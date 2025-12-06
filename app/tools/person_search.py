import httpx
import json
import os
import asyncio
from app.config import settings
from app.schemas import SearchPersonArgs
from app.tools.school_info import _load_school_data, SCHOOL_DB, EXCLUSIVE_NAMES, EXCLUSIVE_ROLES, _normalize_name
from app.tools.developer_info import _load_developer_names, DEVELOPER_NAMES
from rapidfuzz import fuzz, process
import logging

logger = logging.getLogger(__name__)

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

def _search_school_database(query: str) -> list:
    """Search school database using rapidfuzz and return scored results."""
    _load_school_data()
    
    if not SCHOOL_DB:
        return []
    
    query_normalized = _normalize_name(query, remove_titles=True)
    results = []
    
    # Extract all names from school database
    name_candidates = []
    for record in SCHOOL_DB:
        # Get name from various fields
        name = record.get("Name") or record.get("Employee Name") or record.get("name") or ""
        if name:
            name_candidates.append((name, record))
    
    # Use rapidfuzz to find best matches
    if name_candidates:
        # Extract names for matching
        names_only = [name for name, _ in name_candidates]
        
        # Use rapidfuzz.process.extract to get top matches with scores
        matches = process.extract(
            query_normalized,
            names_only,
            scorer=fuzz.WRatio,  # Weighted ratio for better matching
            limit=10
        )
        
        # Filter matches with score >= 60 (adjust threshold as needed)
        for matched_name, score, _ in matches:
            if score >= 60:
                # Find the corresponding record
                for name, record in name_candidates:
                    if name == matched_name:
                        results.append({
                            "name": name,
                            "record": record,
                            "score": score,
                            "source": "school_database"
                        })
                        break
    
    # Also check exclusive roles
    query_lower = query.lower()
    for role_key, exclusive_name in EXCLUSIVE_ROLES.items():
        if role_key in query_lower or query_lower in role_key:
            # Find matching record
            for record in SCHOOL_DB:
                name = record.get("Name") or record.get("Employee Name") or ""
                if exclusive_name.lower() in name.lower() or name.lower() in exclusive_name.lower():
                    results.append({
                        "name": name,
                        "record": record,
                        "score": 95.0,  # High score for role matches
                        "source": "school_database_exclusive"
                    })
                    break
    
    return results

def _search_developer_database(query: str) -> list:
    """Search developer database using rapidfuzz and return scored results."""
    _load_developer_names()
    
    if not DEVELOPER_NAMES:
        return []
    
    query_normalized = query.lower().strip()
    query_words = query_normalized.split()
    results = []
    
    # Use rapidfuzz to find best matches - try multiple strategies
    # Strategy 1: Full name matching
    matches = process.extract(
        query_normalized,
        DEVELOPER_NAMES,
        scorer=fuzz.WRatio,
        limit=10
    )
    
    # Strategy 2: First name matching (for queries like "Raiyan" matching "Raiyan Bin Rashid")
    first_name_matches = []
    if query_words:
        first_name = query_words[0]
        for dev_name in DEVELOPER_NAMES:
            dev_words = dev_name.lower().split()
            if dev_words and first_name in dev_words[0] or dev_words[0] in first_name:
                # Calculate score for first name match
                score = fuzz.ratio(first_name, dev_words[0])
                if score >= 70:  # Lower threshold for first name matches
                    first_name_matches.append((dev_name, score + 20))  # Bonus for first name match
    
    # Strategy 3: Partial name matching (for nicknames like "faijuice" -> "FaiJuice Lubna Karim")
    partial_matches = []
    query_normalized_no_spaces = query_normalized.replace(" ", "")
    for dev_name in DEVELOPER_NAMES:
        dev_normalized = dev_name.lower().replace(" ", "")
        # Check if query is contained in dev name or vice versa
        if query_normalized_no_spaces in dev_normalized or dev_normalized in query_normalized_no_spaces:
            score = fuzz.ratio(query_normalized, dev_name.lower())
            if score >= 50:  # Lower threshold for partial matches
                partial_matches.append((dev_name, score + 15))  # Bonus for partial match
        # Check first 4-6 characters for nickname matching
        if len(query_normalized_no_spaces) >= 4 and len(dev_normalized) >= 4:
            if query_normalized_no_spaces[:4] == dev_normalized[:4] or query_normalized_no_spaces[:4] in dev_normalized:
                score = fuzz.ratio(query_normalized, dev_name.lower())
                if score >= 40:
                    partial_matches.append((dev_name, score + 25))  # Higher bonus for prefix match
    
    # Combine all matches and deduplicate
    all_matches = {}
    
    # Add full name matches
    for dev_name, score, _ in matches:
        if score >= 50:  # Lower threshold
            if dev_name not in all_matches or score > all_matches[dev_name]:
                all_matches[dev_name] = score
    
    # Add first name matches (they get priority)
    for dev_name, score in first_name_matches:
        if dev_name not in all_matches or score > all_matches[dev_name]:
            all_matches[dev_name] = score
    
    # Add partial matches
    for dev_name, score in partial_matches:
        if dev_name not in all_matches or score > all_matches[dev_name]:
            all_matches[dev_name] = score
    
    # Convert to results list, sorted by score
    for dev_name, score in sorted(all_matches.items(), key=lambda x: x[1], reverse=True):
        results.append({
            "name": dev_name,
            "score": min(100, score),  # Cap at 100
            "source": "developer_database"
        })
        if len(results) >= 5:  # Limit to top 5
            break
    
    return results

async def _search_all_sources(query: str) -> dict:
    """Search all sources in parallel and combine results."""
    # Load data first
    _load_school_data()
    _load_developer_names()
    
    # Search local databases (synchronous, fast)
    school_results = _search_school_database(query)
    developer_results = _search_developer_database(query)
    
    # Search external sources (asynchronous)
    tasks = []
    
    # School-specific CSE
    school_cse_id = settings.GOOGLE_CSE_ID_SCHOOL or settings.GOOGLE_CSE_ID
    if school_cse_id:
        tasks.append(_search_google_cse(query, school_cse_id, "school_search_engine"))
    else:
        async def empty_result():
            return {"found": False}
        tasks.append(empty_result())
    
    # International CSE
    international_cse_id = settings.GOOGLE_CSE_ID_INTERNATIONAL
    if international_cse_id:
        words = query.split()
        should_try_international = len(words) >= 2 or any(len(word) > 6 for word in words)
        if should_try_international:
            tasks.append(_search_google_cse(query, international_cse_id, "international_search"))
        else:
            async def empty_result2():
                return {"found": False}
            tasks.append(empty_result2())
    else:
        async def empty_result3():
            return {"found": False}
        tasks.append(empty_result3())
    
    # Web search fallback
    web_search_task = None
    try:
        from app.tools.web_search import web_search
        from app.schemas import WebSearchArgs
        web_search_args = WebSearchArgs(query=query, limit=5)
        web_search_task = web_search(web_search_args)
    except Exception as e:
        logger.error(f"Error preparing web search: {e}")
        web_search_task = None
    
    # Execute all async searches
    search_results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Process web search if available
    web_results = []
    if web_search_task:
        try:
            web_result = await web_search_task
            if web_result.get("results"):
                # Score web search results using rapidfuzz
                for result in web_result["results"]:
                    title = result.get("title", "")
                    snippet = result.get("snippet", "")
                    combined_text = f"{title} {snippet}"
                    
                    # Calculate similarity score
                    score = fuzz.WRatio(query.lower(), combined_text.lower())
                    if score >= 50:  # Lower threshold for web results
                        web_results.append({
                            "title": title,
                            "snippet": snippet,
                            "link": result.get("link"),
                            "score": score,
                            "source": "web_search"
                        })
        except Exception as e:
            logger.error(f"Error in web search: {e}")
    
    # Combine all results with priority scoring
    all_results = []
    
    # Add developer results with HIGHEST PRIORITY (developers should rank above school members)
    # Developers get +40 bonus to ensure they rank above school database results
    for result in developer_results:
        priority_score = min(100, result["score"] + 40)
        all_results.append({
            "type": "developer",
            "name": result["name"],
            "data": {"developer_name": result["name"]},
            "score": priority_score,
            "original_score": result["score"],
            "source": result["source"]
        })
    
    # Add school database results with SECOND PRIORITY (add 30 point bonus, but less than developers)
    for result in school_results:
        priority_score = min(100, result["score"] + 30)
        all_results.append({
            "type": "school_member",
            "name": result["name"],
            "data": result.get("record", {}),
            "score": priority_score,
            "original_score": result["score"],
            "source": result["source"]
        })
    
    # Add school CSE results with medium-high priority (add 15 point bonus)
    if len(search_results) > 0 and isinstance(search_results[0], dict) and search_results[0].get("found"):
        school_cse_result = search_results[0]
        # Score the result
        title = school_cse_result["data"].get("title", "")
        snippet = school_cse_result["data"].get("description", "")
        combined_text = f"{title} {snippet}"
        base_score = fuzz.WRatio(query.lower(), combined_text.lower())
        priority_score = min(100, base_score + 15)
        
        all_results.append({
            "type": "school_website",
            "name": title,
            "data": school_cse_result["data"],
            "score": priority_score,
            "original_score": base_score,
            "source": "school_search_engine"
        })
    
    # Add international CSE results with low-medium priority (add 5 point bonus)
    if len(search_results) > 1 and isinstance(search_results[1], dict) and search_results[1].get("found"):
        intl_result = search_results[1]
        title = intl_result["data"].get("title", "")
        snippet = intl_result["data"].get("description", "")
        combined_text = f"{title} {snippet}"
        base_score = fuzz.WRatio(query.lower(), combined_text.lower())
        priority_score = min(100, base_score + 5)
        
        all_results.append({
            "type": "international",
            "name": title,
            "data": intl_result["data"],
            "score": priority_score,
            "original_score": base_score,
            "source": "international_search"
        })
    
    # Add web search results with LOWEST PRIORITY (no bonus, or even subtract points)
    for result in web_results:
        # Web search gets no bonus, ensuring school database results rank higher
        all_results.append({
            "type": "web",
            "name": result["title"],
            "data": {
                "title": result["title"],
                "snippet": result["snippet"],
                "link": result["link"]
            },
            "score": result["score"],
            "original_score": result["score"],
            "source": result["source"]
        })
    
    # Sort by score (highest first) - school database will rank highest due to priority bonus
    all_results.sort(key=lambda x: x["score"], reverse=True)
    
    # Remove duplicates based on name similarity
    unique_results = []
    seen_names = set()
    for result in all_results:
        name_normalized = _normalize_name(result["name"])
        # Check if we've seen a similar name (fuzzy duplicate detection)
        is_duplicate = False
        for seen_name in seen_names:
            if fuzz.ratio(name_normalized, seen_name) >= 90:  # 90% similarity = duplicate
                is_duplicate = True
                break
        
        if not is_duplicate:
            unique_results.append(result)
            seen_names.add(name_normalized)
            if len(unique_results) >= 10:  # Limit to top 10 results
                break
    
    return {
        "all_results": unique_results,
        "total_found": len(unique_results),
        "best_match": unique_results[0] if unique_results else None
    }

async def search_person(args: SearchPersonArgs) -> dict:
    """
    Search for a person across ALL sources using rapidfuzz:
    1. School database (all members)
    2. Developer database
    3. School-specific CSE
    4. International CSE
    5. Web search
    
    All results are combined, scored using rapidfuzz, and ranked by relevance.
    """
    query = args.person_name.strip()
    
    # Search all sources
    combined_results = await _search_all_sources(query)
    
    if not combined_results["all_results"]:
        return {
            "person_name": query,
            "found": False,
            "source": "none",
            "error": f"I couldn't find information about '{query}' across all available sources (school database, developer database, school website, international search, and web search).",
            "search_query": query,
            "suggestion": "Please check the spelling or provide more context (e.g., full name, position, department)."
        }
    
    # Get best match - prioritize developer matches
    best_match = combined_results["best_match"]
    
    # If we have developer results, prioritize them even if school has higher score
    developer_matches = [r for r in combined_results["all_results"] if r["type"] == "developer"]
    if developer_matches and best_match["type"] != "developer":
        # Check if developer match has reasonable score (>= 50)
        top_developer = developer_matches[0]
        if top_developer.get("original_score", 0) >= 50:
            best_match = top_developer
    
    # Format response based on best match type
    if best_match["type"] == "developer":
        return {
            "person_name": query,
            "found": True,
            "found_in_school_db": False,
            "source": "developer_database",
            "info": {
                "developer_name": best_match["name"],
                "is_team_member": True,
                "team": "Robot Brain Development Team"
            },
            "match_score": best_match.get("original_score", best_match["score"]),
            "search_query": query,
            "all_matches": combined_results["all_results"][:5] if len(combined_results["all_results"]) > 1 else None
        }
    elif best_match["type"] == "school_member":
        record = best_match["data"]
        return {
            "person_name": query,
            "found": True,
            "found_in_school_db": True,
            "source": "school_database",
            "info": record,
            "match_score": best_match.get("original_score", best_match["score"]),
            "search_query": query,
            "all_matches": combined_results["all_results"][:5] if len(combined_results["all_results"]) > 1 else None
        }
    elif best_match["type"] == "school_website":
        return {
            "person_name": query,
            "found": True,
            "found_in_school_db": False,
            "source": "school_search_engine",
            "info": best_match["data"],
            "match_score": best_match["score"],
            "search_query": query,
            "all_matches": combined_results["all_results"][:5] if len(combined_results["all_results"]) > 1 else None
        }
    elif best_match["type"] == "international":
        return {
            "person_name": query,
            "found": True,
            "found_in_school_db": False,
            "source": "international_search",
            "info": best_match["data"],
            "match_score": best_match["score"],
            "search_query": query,
            "all_matches": combined_results["all_results"][:5] if len(combined_results["all_results"]) > 1 else None
        }
    else:  # web
        return {
            "person_name": query,
            "found": True,
            "found_in_school_db": False,
            "source": "web_search",
            "info": {
                "title": "Web Search Results",
                "results": [best_match["data"]] + [
                    r["data"] for r in combined_results["all_results"][1:5] 
                    if r["type"] == "web"
                ]
            },
            "match_score": best_match["score"],
            "search_query": query,
            "all_matches": combined_results["all_results"][:5] if len(combined_results["all_results"]) > 1 else None
        }

definition = {
    "name": "searchPerson",
    "description": "MANDATORY TOOL for ANY person query like 'who is [name]'. This tool searches for a person across ALL available sources with PRIORITY ORDER: 1) School database FIRST (all members - this is checked first and has highest priority), 2) Developer database, 3) School website, 4) International search, 5) Web search (only as last resort). All sources are searched simultaneously and results are combined and ranked by relevance using rapidfuzz, but school database matches are prioritized. The school database is ALWAYS searched first and results from it take precedence. CRITICAL: Before using this tool, FIRST check if the person might be a developer using getDeveloperInfo tool. Only use searchPerson if getDeveloperInfo returns 'is_team_member: false' or if you're certain it's not a developer query. IMPORTANT: For ANY 'who is [name]' query, you MUST use this tool - do NOT use webSearch for person queries. The school database is searched first and has highest priority in results.",
    "parameters": {
        "type": "object",
        "properties": {
            "person_name": {"type": "string", "description": "Name of the person to search for (can include titles like 'sir', 'madam', etc.). This will search school database FIRST, then other sources."}
        },
        "required": ["person_name"]
    }
}
