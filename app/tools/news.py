import httpx
from app.config import settings
from app.schemas import GetNewsArgs
import logging

logger = logging.getLogger(__name__)

async def get_news(args: GetNewsArgs) -> dict:
    """
    Fetches top news headlines using newsdata.io API.
    Supports keyword search, breaking news, and general headlines.
    """
    if not settings.NEWS_API_KEY:
        return {"error": "News API key not configured"}

    # Build parameters for newsdata.io API
    params = {
        "apikey": settings.NEWS_API_KEY,
        "language": "en",
        "size": args.limit
    }
    
    # Add keyword search if topic is provided and not "general"
    topic = args.topic or "general"
    if topic.lower() != "general":
        params["q"] = topic
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(settings.NEWS_API_URL, params=params, timeout=10.0)
            response.raise_for_status()
            data = response.json()
            
            # Check API response status
            status = data.get("status")
            if status != "success":
                error_msg = data.get("message", "Unknown error from news API")
                logger.error(f"News API returned error: {error_msg}")
                return {"error": f"News API error: {error_msg}"}
            
            # Extract articles from newsdata.io response format
            articles_data = data.get("results", [])
            if not articles_data:
                return {"articles": [], "message": "No news articles found for this topic"}
            
            articles = []
            for article in articles_data:
                articles.append({
                    "title": article.get("title"),
                    "source": article.get("source_id") or article.get("source_name"),
                    "description": article.get("description"),
                    "url": article.get("link"),
                    "published_date": article.get("pubDate"),
                    "category": article.get("category", []),
                    "country": article.get("country", [])
                })
            
            return {
                "articles": articles,
                "total_results": data.get("totalResults", len(articles)),
                "next_page": data.get("nextPage")
            }
        except httpx.HTTPStatusError as e:
            error_text = ""
            try:
                error_text = e.response.text
                error_data = e.response.json()
                error_msg = error_data.get("message", error_text)
            except:
                error_msg = error_text or str(e)
            
            logger.error(f"News API HTTP error ({e.response.status_code}): {error_msg}")
            return {"error": f"News API error: {error_msg}"}
        except httpx.TimeoutException:
            logger.error("News API request timed out")
            return {"error": "News API request timed out. Please try again later."}
        except Exception as e:
            logger.error(f"News tool error: {e}")
            return {"error": f"Error fetching news: {str(e)}"}

definition = {
    "name": "getNews",
    "description": "Fetch latest news headlines and breaking news. Supports keyword search for specific topics (e.g., 'technology', 'politics', 'Bangladesh') or 'general' for top headlines. Returns articles with title, source, description, and URL. If no topic is specified, returns general top headlines.",
    "parameters": {
        "type": "object",
        "properties": {
            "topic": {"type": "string", "description": "News topic keyword to search for (e.g., 'technology', 'politics', 'Bangladesh', 'sports') or 'general' for top breaking news headlines. Defaults to 'general' if not provided."},
            "limit": {"type": "integer", "description": "Number of articles to return (1-10)", "minimum": 1, "maximum": 10, "default": 3}
        },
        "required": []
    }
}
