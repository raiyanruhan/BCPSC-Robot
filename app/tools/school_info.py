import httpx
import json
import os
from app.config import settings
from app.schemas import GetSchoolInfoArgs
import logging

logger = logging.getLogger(__name__)

# Load school database and exclusive names on module import
SCHOOL_DB = None
EXCLUSIVE_NAMES = []
EXCLUSIVE_ROLES = {}  # Map role -> name

def _load_school_data():
    """Load school data from JSON file and exclusive names from text file."""
    global SCHOOL_DB, EXCLUSIVE_NAMES, EXCLUSIVE_ROLES
    
    if SCHOOL_DB is not None:
        return  # Already loaded
    
    SCHOOL_DB = []
    EXCLUSIVE_NAMES = []
    EXCLUSIVE_ROLES = {}
    
    # Load All Details.json
    school_data_path = os.path.join(os.path.dirname(__file__), "..", "..", "Data", "School", "All Details.json")
    if os.path.exists(school_data_path):
        try:
            with open(school_data_path, "r", encoding="utf-8") as f:
                SCHOOL_DB = json.load(f)
            logger.info(f"Loaded {len(SCHOOL_DB)} school records from database")
        except Exception as e:
            logger.error(f"Error loading school database: {e}")
            SCHOOL_DB = []
    
    # Load exclusive.txt - store both role and name
    exclusive_path = os.path.join(os.path.dirname(__file__), "..", "..", "Data", "School", "exclusive.txt")
    if os.path.exists(exclusive_path):
        try:
            with open(exclusive_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and ":" in line:
                        # Extract role and name
                        parts = line.split(":", 1)
                        role = parts[0].strip()
                        name = parts[1].strip()
                        EXCLUSIVE_NAMES.append(name)
                        # Store role mapping (normalized for matching)
                        role_normalized = role.lower().strip()
                        EXCLUSIVE_ROLES[role_normalized] = name
                        # Also store common variations
                        if "principal" in role_normalized:
                            EXCLUSIVE_ROLES["principal"] = name
                            EXCLUSIVE_ROLES["principle"] = name  # Common typo
                        elif "chairman" in role_normalized:
                            EXCLUSIVE_ROLES["chairman"] = name
                        elif "chief patron" in role_normalized or "patron" in role_normalized:
                            EXCLUSIVE_ROLES["chief patron"] = name
                            EXCLUSIVE_ROLES["patron"] = name
            logger.info(f"Loaded {len(EXCLUSIVE_NAMES)} exclusive names and {len(EXCLUSIVE_ROLES)} role mappings")
        except Exception as e:
            logger.error(f"Error loading exclusive names: {e}")

def _normalize_name(name: str, remove_titles: bool = False) -> str:
    """Normalize name for better matching - remove extra spaces, punctuation, titles, etc."""
    if not name:
        return ""
    import re
    # Convert to lowercase, remove extra spaces, remove common punctuation
    normalized = name.lower().strip()
    
    # Remove common prefixes/suffixes that might vary
    normalized = normalized.replace("mst.", "").replace("md.", "").replace("dr.", "")
    normalized = normalized.replace("mst", "").replace("md", "").replace("dr", "")
    
    # Remove titles if requested (for query normalization)
    if remove_titles:
        titles = ["sir", "madam", "maam", "mam", "sir.", "madam.", "teacher", "professor", "prof"]
        for title in titles:
            # Remove title as whole word
            normalized = re.sub(r'\b' + re.escape(title) + r'\b', '', normalized)
    
    # Remove all punctuation and extra spaces
    normalized = re.sub(r'[^\w\s]', ' ', normalized)
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    return normalized

def _calculate_match_score(query_tokens: list, name_tokens: list) -> float:
    """Calculate match score between query and name tokens with fuzzy matching."""
    if not query_tokens or not name_tokens:
        return 0.0
    
    # Count exact token matches
    exact_matches = sum(1 for token in query_tokens if token in name_tokens)
    
    # Count partial/substring matches (for cases like "shajed" matching "shajedul")
    partial_matches = 0
    matched_tokens = set()
    for query_token in query_tokens:
        if len(query_token) >= 3:  # Only for meaningful tokens
            for name_token in name_tokens:
                # Check if query token is a substring of name token or vice versa
                # This handles "shajed" -> "shajedul", "shajedur"
                if query_token in name_token or name_token in query_token:
                    if name_token not in matched_tokens:
                        partial_matches += 1
                        matched_tokens.add(name_token)
                        break
    
    # Use the better of exact or partial matches
    matches = max(exact_matches, partial_matches)
    
    # Calculate score based on percentage of tokens matched
    if len(query_tokens) > 0:
        score = matches / len(query_tokens)
    else:
        score = 0.0
    
    # Bonus for exact order match
    if query_tokens == name_tokens[:len(query_tokens)]:
        score += 0.3
    
    # Bonus for first token match (first name is usually most important)
    # This is critical for "shajed" -> "shajedul" matching
    if query_tokens and name_tokens:
        first_query = query_tokens[0]
        first_name = name_tokens[0]
        # Check if first query token is a substring of first name token
        if first_query in first_name or first_name in first_query:
            score += 0.3  # Increased bonus for first name match
        # Also check if first query token matches any name token (for middle/last name cases)
        elif any(first_query in token or token in first_query for token in name_tokens):
            score += 0.2
    
    return min(score, 1.0)  # Cap at 1.0

def _search_local_database(query: str) -> dict:
    """Search in local school database with improved fuzzy matching."""
    _load_school_data()
    
    query_lower = query.lower().strip()
    # Normalize query with title removal for better matching
    query_normalized = _normalize_name(query, remove_titles=True)
    query_tokens = [token for token in query_normalized.split() if token]  # Remove empty tokens
    
    # If query is too short after normalization, try without title removal
    if len(query_tokens) == 0:
        query_normalized = _normalize_name(query, remove_titles=False)
        query_tokens = [token for token in query_normalized.split() if token]
    
    results = []
    scored_results = []
    
    # Search in database with scoring
    for record in SCHOOL_DB:
        score = 0.0
        matched_field = None
        
        # Check all possible name fields and also Position field for role matching
        name_fields = ["name", "Name", "Employee Name", "newText", "Position"]
        
        for field in name_fields:
            if field in record and record[field]:
                field_value = str(record[field])
                field_lower = field_value.lower()
                field_normalized = _normalize_name(field_value)
                field_tokens = field_normalized.split()
                
                # Exact match (highest score)
                if query_lower == field_lower:
                    score = 1.0
                    matched_field = field
                    break
                
                # Normalized exact match
                if query_normalized == field_normalized:
                    score = 0.95
                    matched_field = field
                    break
                
                # Contains match
                if query_lower in field_lower or field_lower in query_lower:
                    score = max(score, 0.7)
                    matched_field = field
                
                # Token-based matching (this handles partial matches like "shajed" -> "shajedul")
                token_score = _calculate_match_score(query_tokens, field_tokens)
                if token_score > score:
                    score = token_score
                    matched_field = field
                
                # Additional fuzzy matching for first name variations
                # If query has at least one token, check if it matches the start of any name token
                if query_tokens:
                    first_query_token = query_tokens[0]
                    if len(first_query_token) >= 3:
                        for field_token in field_tokens:
                            # Check if query token matches the beginning of field token (e.g., "shajed" -> "shajedul")
                            if field_token.startswith(first_query_token) or first_query_token.startswith(field_token):
                                score = max(score, 0.6)
                                matched_field = field
                                break
                
                # Special handling for Position field - role matching (e.g., "principal" matches "PRINCIPAL")
                if field == "Position" and record.get("Position"):
                    position_lower = record["Position"].lower()
                    # Check if query matches position/role
                    if query_lower in position_lower or position_lower in query_lower:
                        score = max(score, 0.8)  # High score for role matches
                        matched_field = field
                    # Also check individual tokens
                    for query_token in query_tokens:
                        if len(query_token) >= 4 and query_token in position_lower:
                            score = max(score, 0.7)
                            matched_field = field
        
        if score > 0.25:  # Lower threshold to catch more matches
            scored_results.append((score, record, matched_field))
    
    # Check exclusive roles first (Principal, Chairman, Chief Patron)
    query_normalized_lower = query_normalized.lower()
    for role_key, exclusive_name in EXCLUSIVE_ROLES.items():
        # Check if query matches the role (e.g., "principal" matches "Principal:")
        if role_key in query_normalized_lower or query_normalized_lower in role_key:
            # Find the matching record for this exclusive name
            exclusive_normalized = _normalize_name(exclusive_name)
            for record in SCHOOL_DB:
                if "Name" in record:
                    record_name_normalized = _normalize_name(record["Name"])
                    # Check if this record matches the exclusive name
                    if exclusive_normalized in record_name_normalized or record_name_normalized in exclusive_normalized:
                        scored_results.append((0.95, record, "Name"))  # Very high priority for exclusive roles
                        break
                # Also check Employee Name field
                if "Employee Name" in record:
                    record_name_normalized = _normalize_name(record["Employee Name"])
                    if exclusive_normalized in record_name_normalized or record_name_normalized in exclusive_normalized:
                        scored_results.append((0.95, record, "Employee Name"))
                        break
    
    # Check exclusive names directly (by name matching)
    for exclusive_name in EXCLUSIVE_NAMES:
        exclusive_normalized = _normalize_name(exclusive_name)
        exclusive_tokens = exclusive_normalized.split()
        
        # Check if query matches exclusive name
        exclusive_score = _calculate_match_score(query_tokens, exclusive_tokens)
        if exclusive_score > 0.4:
            # Find matching record in database
            for record in SCHOOL_DB:
                if "Name" in record:
                    record_name_normalized = _normalize_name(record["Name"])
                    if exclusive_normalized in record_name_normalized or record_name_normalized in exclusive_normalized:
                        scored_results.append((0.9, record, "Name"))  # High priority for exclusive names
                        break
                # Also check Employee Name
                if "Employee Name" in record:
                    record_name_normalized = _normalize_name(record["Employee Name"])
                    if exclusive_normalized in record_name_normalized or record_name_normalized in exclusive_normalized:
                        scored_results.append((0.9, record, "Employee Name"))
                        break
    
    # Sort by score (highest first) and remove duplicates
    scored_results.sort(key=lambda x: x[0], reverse=True)
    seen_records = set()
    for score, record, field in scored_results:
        # Use a simple hash to identify duplicate records
        record_id = str(record.get("Name", "")) + str(record.get("Employee Name", "")) + str(record.get("name", ""))
        if record_id not in seen_records:
            seen_records.add(record_id)
            results.append(record)
            if len(results) >= 5:  # Limit to top 5 results
                break
    
    if results:
        # Return results with metadata
        return {
            "found": True,
            "source": "local_database",
            "data": results[0] if len(results) == 1 else results[:3],  # Return first or up to 3 results
            "total_matches": len(results)
        }
    
    return {"found": False}

async def _search_google_cse(query: str, cse_id: str, source_name: str) -> dict:
    """Search using Google Custom Search Engine."""
    if not settings.GOOGLE_API_KEY or not cse_id:
        return {"found": False, "error": "Google Search API key or CSE ID not configured"}
    
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": settings.GOOGLE_API_KEY,
        "cx": cse_id,
        "q": query,
        "num": 5
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params, timeout=5.0)
            response.raise_for_status()
            data = response.json()
            
            items = data.get("items", [])
            if items:
                return {
                    "found": True,
                    "source": source_name,
                    "data": {
                        "title": items[0].get("title"),
                        "description": items[0].get("snippet"),
                        "website": items[0].get("link"),
                        "additional_results": [
                            {
                                "title": item.get("title"),
                                "snippet": item.get("snippet"),
                                "link": item.get("link")
                            }
                            for item in items[1:3]
                        ]
                    }
                }
            return {"found": False}
        except Exception as e:
            logger.error(f"Google Search API error ({source_name}): {e}")
            return {"found": False, "error": str(e)}

def _format_school_result(record: dict) -> dict:
    """Format a school database record into a readable response."""
    result = {}
    
    # Extract name from various fields
    name = record.get("Name") or record.get("Employee Name") or record.get("name") or "Unknown"
    result["name"] = name
    
    # Extract position/designation
    if "Position" in record:
        result["position"] = record["Position"]
    if "Designation" in record:
        result["designation"] = record["Designation"]
    
    # Extract institution
    if "Institution" in record:
        result["institution"] = record["Institution"]
    
    # Extract other relevant fields
    if "newText" in record:
        result["details"] = record["newText"]
    if "Joining Date" in record:
        result["joining_date"] = record["Joining Date"]
    if "Blood Group" in record:
        result["blood_group"] = record["Blood Group"]
    
    # Include full record for reference
    result["full_record"] = record
    
    return result

async def get_school_info(args: GetSchoolInfoArgs) -> dict:
    """
    Searches for school information with fallback chain:
    1. Local database (Data/School/All Details.json + exclusive.txt) - with fuzzy matching
    2. School-specific Google CSE
    3. International Google CSE
    4. Sorry response if no solid answer found
    """
    query = args.school_name.strip()
    
    # Step 1: Search local database with improved fuzzy matching
    local_result = _search_local_database(query)
    if local_result.get("found"):
        data = local_result["data"]
        
        # Format single result or multiple results
        if isinstance(data, dict):
            formatted_data = _format_school_result(data)
        else:
            # Multiple results - format all
            formatted_data = {
                "matches": [_format_school_result(record) for record in data],
                "total_found": len(data)
            }
            # If multiple, also include the best match separately
            if data:
                formatted_data["best_match"] = _format_school_result(data[0])
        
        return {
            "school_name": query,
            "source": "local_database",
            "info": formatted_data,
            "search_query": query
        }
    
    # Step 2: Search school-specific CSE
    school_cse_id = settings.GOOGLE_CSE_ID_SCHOOL or settings.GOOGLE_CSE_ID
    school_result = await _search_google_cse(query, school_cse_id, "school_search_engine")
    if school_result.get("found"):
        return {
            "school_name": query,
            "source": "school_search_engine",
            "info": school_result["data"],
            "search_query": query
        }
    
    # Step 3: Search international CSE
    international_cse_id = settings.GOOGLE_CSE_ID_INTERNATIONAL
    if international_cse_id:
        intl_result = await _search_google_cse(query, international_cse_id, "international_search")
        if intl_result.get("found"):
            return {
                "school_name": query,
                "source": "international_search",
                "info": intl_result["data"],
                "search_query": query
            }
    
    # Step 4: Fallback to general webSearch tool
    try:
        from app.tools.web_search import web_search
        from app.schemas import WebSearchArgs
        
        web_search_args = WebSearchArgs(query=f"{query} Bogura Cantonment Public School and College", limit=3)
        web_result = await web_search(web_search_args)
        
        if web_result.get("results"):
            return {
                "school_name": query,
                "source": "web_search_fallback",
                "info": {
                    "title": "Web Search Results",
                    "results": web_result["results"],
                    "note": "Information found through general web search. Local database and school-specific search did not return results."
                },
                "search_query": query
            }
    except Exception as e:
        logger.error(f"Error in webSearch fallback: {e}")
    
    # Step 5: No solid answer found
    return {
        "school_name": query,
        "source": "none",
        "error": "I'm sorry, I couldn't find reliable information about this person or entity in our database (258 school members) or through search engines. Please check the spelling or provide more details.",
        "search_query": query,
        "suggestion": "Try searching with the full name or check if the person is associated with Bogura Cantonment Public School and College."
    }

definition = {
    "name": "getSchoolInfo",
    "description": "Search for school information with fallback chain: 1) Local database (258 school members), 2) School-specific search engine, 3) International search engine, 4) Sorry response if not found. Always checks exclusive important names first.",
    "parameters": {
        "type": "object",
        "properties": {
            "school_name": {"type": "string", "description": "Name of the school, person, or entity to search for"}
        },
        "required": ["school_name"]
    }
}
