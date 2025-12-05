import httpx
from app.config import settings
from app.schemas import GetWeatherArgs
import logging

logger = logging.getLogger(__name__)

async def get_weather(args: GetWeatherArgs) -> dict:
    """
    Fetches weather data from OpenWeatherMap.
    """
    if not settings.WEATHER_API_KEY:
        return {"error": "Weather API key not configured"}

    params = {
        "q": args.location,
        "units": args.units,
        "appid": settings.WEATHER_API_KEY
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(settings.WEATHER_API_URL, params=params, timeout=5.0)
            response.raise_for_status()
            data = response.json()
            
            # Simplify response for LLM
            main = data.get("main", {})
            weather = data.get("weather", [{}])[0]
            wind = data.get("wind", {})
            
            return {
                "location": data.get("name"),
                "temperature": main.get("temp"),
                "condition": weather.get("description"),
                "humidity": main.get("humidity"),
                "wind_speed": wind.get("speed"),
                "units": args.units
            }
        except httpx.HTTPStatusError as e:
            logger.error(f"Weather API error: {e.response.text}")
            return {"error": f"Weather API error: {e.response.status_code}"}
        except Exception as e:
            logger.error(f"Weather tool error: {e}")
            return {"error": str(e)}

definition = {
    "name": "getWeather",
    "description": "Return current weather for a given location (city, lat/lon, or free-form).",
    "parameters": {
        "type": "object",
        "properties": {
            "location": {"type": "string", "description": "City name or 'City, Country' or 'lat,lon'"},
            "units": {"type": "string", "enum": ["metric", "imperial"]}
        },
        "required": ["location"]
    }
}
