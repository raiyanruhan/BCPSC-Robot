import httpx
import json
import os
from app.config import settings
from app.schemas import SearchPersonArgs
from app.tools.school_info import _load_school_data, _search_local_database
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

async def search_person(args: SearchPersonArgs) -> dict:
    """
    Search for a person in priority order:
    1. School database (258 members) - local fuzzy matching
    2. School-specific CSE - school website search
    3. International CSE - only if >10% chance it's a worldwide person (2+ word names or longer names)
    4. Web search - final fallback
    
    Note: This tool is for uncommon/local names. For celebrities/famous people, 
    you should either answer directly using your knowledge or use webSearch tool.
    """
    query = args.person_name.strip()
    
    # Load school data
    _load_school_data()
    
    # Step 1: Search local school database
    local_result = _search_local_database(query)
    if local_result.get("found"):
        return {
            "person_name": query,
            "found_in_school_db": True,
            "source": "local_database",
            "info": local_result["data"],
            "search_query": query
        }
    
    # Step 2: Search school-specific CSE
    school_cse_id = settings.GOOGLE_CSE_ID_SCHOOL or settings.GOOGLE_CSE_ID
    if school_cse_id:
        school_result = await _search_google_cse(query, school_cse_id, "school_search_engine")
        if school_result.get("found"):
            return {
                "person_name": query,
                "found_in_school_db": False,
                "source": "school_search_engine",
                "info": school_result["data"],
                "search_query": query
            }
    
    # Step 3: Search international CSE (only if >10% chance it's a worldwide person)
    # Heuristic: If name has 2+ words or longer names, might be worldwide (>10% chance)
    international_cse_id = settings.GOOGLE_CSE_ID_INTERNATIONAL
    if international_cse_id:
        words = query.split()
        should_try_international = len(words) >= 2 or any(len(word) > 6 for word in words)
        
        if should_try_international:
            intl_result = await _search_google_cse(query, international_cse_id, "international_search")
            if intl_result.get("found"):
                return {
                    "person_name": query,
                    "found_in_school_db": False,
                    "source": "international_search",
                    "info": intl_result["data"],
                    "search_query": query,
                    "note": "Found through international search (>10% chance this person is known worldwide)."
                }
    
    # Step 4: Final fallback: Use webSearch tool
    try:
        from app.tools.web_search import web_search
        from app.schemas import WebSearchArgs
        
        web_search_args = WebSearchArgs(query=query, limit=5)
        web_result = await web_search(web_search_args)
        
        if web_result.get("results"):
            return {
                "person_name": query,
                "found_in_school_db": False,
                "source": "web_search_fallback",
                "info": {
                    "title": "Web Search Results",
                    "results": web_result["results"],
                    "note": "Information found through general web search. Not found in school database or school-specific search."
                },
                "search_query": query
            }
    except Exception as e:
        logger.error(f"Error in webSearch fallback: {e}")
    
    # Not found anywhere
    return {
        "person_name": query,
        "found_in_school_db": False,
        "source": "none",
        "error": f"I couldn't find information about '{query}' in our school database (258 members), school website, or through web search. This person may not be in our records or may be very uncommon.",
        "search_query": query,
        "suggestion": "Please check the spelling or provide more context (e.g., full name, position, department)."
    }

definition = {
    "name": "searchPerson",
    "description": "Search for a person in priority order: 1) School database (258 members), 2) School website, 3) International search (if >10% chance worldwide), 4) Web search. IMPORTANT: Before using this tool, think: Do I know this person? If they are a well-known celebrity/famous person (e.g., Elon Musk, Taylor Swift, Shahrukh Khan, Barack Obama), you can either: a) Answer directly using your knowledge, OR b) Use webSearch tool for current information. Only use this searchPerson tool for uncommon/local names that you don't recognize. The AI decides whether to answer directly, use webSearch, or use this tool - the app does not decide.",
    "parameters": {
        "type": "object",
        "properties": {
            "person_name": {"type": "string", "description": "Name of the person to search for (can include titles like 'sir', 'madam', etc.)"}
        },
        "required": ["person_name"]
    }
}

