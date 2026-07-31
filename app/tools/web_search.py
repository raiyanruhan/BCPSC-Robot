import httpx
from app.config import settings
from app.schemas import WebSearchArgs
import logging

logger = logging.getLogger(__name__)

async def web_search(args: WebSearchArgs) -> dict:
    """
    Performs a Google Custom Search using the international CSE ID.
    Falls back to providing a helpful message if API is not available.
    """
    # Use international CSE ID for web searches, fallback to default if not set
    cse_id = settings.GOOGLE_CSE_ID_INTERNATIONAL or settings.GOOGLE_CSE_ID
    
    if not settings.GOOGLE_API_KEY or not cse_id:
        logger.warning("Google Search API key or CSE ID not configured")
        return {
            "error": "Web search not available",
            "message": "The Google Custom Search API is not configured. Please enable the Custom Search API in your Google Cloud Console at https://console.developers.google.com/apis/api/customsearch.googleapis.com/",
            "query": args.query,
            "suggestion": f"I cannot search the web for '{args.query}' right now because the search API is not configured. However, I can help you with information from my knowledge base or school database."
        }

    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": settings.GOOGLE_API_KEY,
        "cx": cse_id,
        "q": args.query,
        "num": args.limit
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params, timeout=5.0)
            response.raise_for_status()
            data = response.json()
            
            results = []
            for item in data.get("items", []):
                results.append({
                    "title": item.get("title"),
                    "snippet": item.get("snippet"),
                    "link": item.get("link")
                })
            
            return {"results": results}
        except httpx.HTTPStatusError as e:
            error_text = e.response.text
            logger.error(f"Google Search API error: {error_text}")
            
            # Check if it's a 403 permission error
            if e.response.status_code == 403:
                return {
                    "error": "Web search not available",
                    "message": "The Google Custom Search API is not enabled. Please enable it by visiting: https://console.developers.google.com/apis/api/customsearch.googleapis.com/",
                    "query": args.query,
                    "suggestion": f"I cannot search the web for '{args.query}' right now because the Custom Search API needs to be enabled in the Google Cloud Console. However, I can still help you with general information from my knowledge base, school information, or local database. What would you like to know?"
                }
            
            return {
                "error": f"Google Search API error: {e.response.status_code}",
                "query": args.query,
                "suggestion": f"I encountered an error while trying to search for '{args.query}'. However, I can still help you with information from my knowledge base or school database."
            }
        except Exception as e:
            logger.error(f"Web search tool error: {e}")
            return {
                "error": str(e),
                "query": args.query,
                "suggestion": f"I encountered an error while trying to search for '{args.query}'. However, I can still answer questions using my knowledge base."
            }

definition = {
    "name": "webSearch",
    "description": "Search the web using Google Search / CSE and return top results (title, snippet, url). CRITICAL: DO NOT use this tool for person queries like 'who is [name]' - use searchPerson tool instead, which searches school database first. Use webSearch ONLY for: general web searches (non-person queries), current events, news, general information, or when you need to find information that's clearly not about a person. When the user asks you to 'search for' something that is NOT a person name, immediately call this tool with the search query. NOTE: If the API is not available, you will receive a suggestion to use your knowledge base instead.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The search query to look up on the web. Use clear, specific search terms. DO NOT use for person names - use searchPerson instead."},
            "limit": {"type": "integer", "minimum": 1, "maximum": 10, "default": 5}
        },
        "required": ["query"]
    }
}
