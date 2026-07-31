import httpx
from app.config import settings
from app.schemas import GetNewsArgs
import logging

logger = logging.getLogger(__name__)

async def get_news(args: GetNewsArgs) -> dict:
    """
    Fetches top news headlines using newsdata.io API.
    Supports country, category, language filters, and keyword search.
    """
    if not settings.NEWS_API_KEY:
        return {"error": "News API key not configured"}

    # Build parameters for newsdata.io API with defaults
    params = {
        "apikey": settings.NEWS_API_KEY,
        "country": args.country or "bd",  # Default to Bangladesh
        "category": args.category or "politics,sports,top,domestic,business",  # Default categories
        "language": args.language or "en",  # Default to English
        "size": args.limit
    }
    
    # Add keyword search if topic is provided
    if args.topic and args.topic.strip() and args.topic.lower() != "general":
        params["q"] = args.topic.strip()
    
    # Log the request parameters for debugging
    logger.info(f"Fetching news with params: country={params.get('country')}, category={params.get('category')}, language={params.get('language')}, topic={params.get('q', 'none')}, limit={params.get('size')}")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(settings.NEWS_API_URL, params=params, timeout=10.0)
            response.raise_for_status()
            data = response.json()
            
            # Log response status
            logger.info(f"News API response status: {data.get('status')}, totalResults: {data.get('totalResults', 0)}")
            
            # Check API response status
            status = data.get("status")
            if status != "success":
                error_msg = data.get("message", "Unknown error from news API")
                logger.error(f"News API returned error: {error_msg}")
                logger.error(f"Full API response: {data}")
                return {"error": f"News API error: {error_msg}", "api_response": data}
            
            # Extract articles from newsdata.io response format
            articles_data = data.get("results", [])
            if not articles_data:
                # Check if there's a message in the response
                message = data.get("message", "No news articles found")
                logger.warning(f"News API returned no articles. Message: {message}")
                return {
                    "articles": [],
                    "message": f"No news articles found. API message: {message}",
                    "query_params": params
                }
            
            articles = []
            for article in articles_data:
                # Extract all available fields from newsdata.io response
                article_info = {
                    "title": article.get("title", "No title"),
                    "source": article.get("source_id") or article.get("source_name") or "Unknown source",
                    "description": article.get("description") or article.get("content", ""),
                    "url": article.get("link") or article.get("url", ""),
                    "published_date": article.get("pubDate") or article.get("published_date", ""),
                }
                
                # Add category and country if available
                category = article.get("category")
                if category:
                    article_info["category"] = category if isinstance(category, list) else [category]
                else:
                    article_info["category"] = []
                
                country = article.get("country")
                if country:
                    article_info["country"] = country if isinstance(country, list) else [country]
                else:
                    article_info["country"] = []
                
                # Add image if available
                if article.get("image_url"):
                    article_info["image_url"] = article.get("image_url")
                
                articles.append(article_info)
            
            return {
                "articles": articles,
                "total_results": data.get("totalResults", len(articles)),
                "next_page": data.get("nextPage"),
                "query_params": {
                    "country": params.get("country"),
                    "category": params.get("category"),
                    "language": params.get("language"),
                    "topic": params.get("q", "top headlines")
                }
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
    "description": "Fetch latest news headlines from newsdata.io API. By default, returns news from Bangladesh (country='bd') in categories: politics, sports, top, domestic, business. Supports keyword search, country filter, category filter, and language selection. Use this tool when the user asks about news, current events, headlines, or specific topics like 'politics', 'sports', 'Bangladesh news', etc.",
    "parameters": {
        "type": "object",
        "properties": {
            "topic": {"type": "string", "description": "Optional keyword to search for specific topics (e.g., 'technology', 'politics', 'Bangladesh', 'sports', 'election'). If not provided, returns top headlines from default categories. Use this for specific topic searches."},
            "country": {"type": "string", "description": "Country code filter (e.g., 'bd' for Bangladesh, 'us' for USA, 'in' for India). Defaults to 'bd' (Bangladesh). Use this when user asks for news from a specific country."},
            "category": {"type": "string", "description": "Category filter - comma-separated list of categories (e.g., 'politics,sports,top,domestic,business', 'technology', 'health'). Defaults to 'politics,sports,top,domestic,business'. Use this to filter by specific news categories."},
            "language": {"type": "string", "description": "Language filter: 'en' for English or 'bn' for Bengali. Defaults to 'en'. Use 'bn' when user requests Bengali news."},
            "limit": {"type": "integer", "description": "Number of articles to return (1-10). Defaults to 3.", "minimum": 1, "maximum": 10, "default": 3}
        },
        "required": []
    }
}
