import httpx
from app.config import settings
from app.schemas import WebSearchArgs
import logging

logger = logging.getLogger(__name__)

async def web_search(args: WebSearchArgs) -> dict:
    """
    Performs a Google Custom Search using the international CSE ID.
    """
    # Use international CSE ID for web searches, fallback to default if not set
    cse_id = settings.GOOGLE_CSE_ID_INTERNATIONAL or settings.GOOGLE_CSE_ID
    
    if not settings.GOOGLE_API_KEY or not cse_id:
        return {"error": "Google Search API key or CSE ID not configured"}

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
            logger.error(f"Google Search API error: {e.response.text}")
            return {"error": f"Google Search API error: {e.response.status_code}"}
        except Exception as e:
            logger.error(f"Web search tool error: {e}")
            return {"error": str(e)}

definition = {
    "name": "webSearch",
    "description": "Search the web using Google Search / CSE and return top results (title, snippet, url). Use this for general web searches, celebrity information, or when you need current/real-time information. For person names, consider using searchPerson tool first (it will route celebrities appropriately).",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "limit": {"type": "integer", "minimum": 1, "maximum": 10, "default": 5}
        },
        "required": ["query"]
    }
}
