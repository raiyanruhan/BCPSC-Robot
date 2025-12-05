import httpx
from app.config import settings
from app.schemas import GetWeatherForecastArgs
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

async def get_weather_forecast(args: GetWeatherForecastArgs) -> dict:
    """
    Fetches weather forecast data from OpenWeatherMap One Call API or 5-day forecast.
    """
    if not settings.WEATHER_API_KEY:
        return {"error": "Weather API key not configured"}

    # First, get coordinates for the location
    geocode_params = {
        "q": args.location,
        "appid": settings.WEATHER_API_KEY,
        "limit": 1
    }
    
    async with httpx.AsyncClient() as client:
        try:
            # Get coordinates
            geocode_response = await client.get(
                "http://api.openweathermap.org/geo/1.0/direct",
                params=geocode_params,
                timeout=5.0
            )
            geocode_response.raise_for_status()
            geocode_data = geocode_response.json()
            
            if not geocode_data:
                return {"error": f"Location '{args.location}' not found"}
            
            lat = geocode_data[0]["lat"]
            lon = geocode_data[0]["lon"]
            location_name = geocode_data[0].get("name", args.location)
            
            # Get forecast using 5-day/3-hour forecast API (free tier)
            forecast_params = {
                "lat": lat,
                "lon": lon,
                "appid": settings.WEATHER_API_KEY,
                "units": "metric"
            }
            
            forecast_response = await client.get(
                "https://api.openweathermap.org/data/2.5/forecast",
                params=forecast_params,
                timeout=5.0
            )
            forecast_response.raise_for_status()
            forecast_data = forecast_response.json()
            
            # Calculate target date
            target_date = datetime.now() + timedelta(days=args.days_ahead)
            target_date_str = target_date.strftime("%Y-%m-%d")
            
            # Find forecast entries for the target day
            matching_forecasts = []
            for item in forecast_data.get("list", []):
                forecast_date = datetime.fromtimestamp(item["dt"]).strftime("%Y-%m-%d")
                if forecast_date == target_date_str:
                    matching_forecasts.append(item)
            
            if not matching_forecasts:
                # If no exact match, get the closest forecast
                closest_forecast = None
                min_diff = float('inf')
                for item in forecast_data.get("list", []):
                    forecast_dt = datetime.fromtimestamp(item["dt"])
                    diff = abs((forecast_dt - target_date).total_seconds())
                    if diff < min_diff:
                        min_diff = diff
                        closest_forecast = item
                
                if closest_forecast:
                    matching_forecasts = [closest_forecast]
            
            if not matching_forecasts:
                return {"error": f"No forecast available for {args.days_ahead} days ahead"}
            
            # Use the first matching forecast (or average if multiple)
            forecast = matching_forecasts[0]
            main = forecast.get("main", {})
            weather = forecast.get("weather", [{}])[0]
            wind = forecast.get("wind", {})
            
            # Calculate average if multiple forecasts for the day
            if len(matching_forecasts) > 1:
                avg_temp = sum(f.get("main", {}).get("temp", 0) for f in matching_forecasts) / len(matching_forecasts)
                avg_humidity = sum(f.get("main", {}).get("humidity", 0) for f in matching_forecasts) / len(matching_forecasts)
                main["temp"] = avg_temp
                main["humidity"] = avg_humidity
            
            forecast_time = datetime.fromtimestamp(forecast["dt"]).strftime("%Y-%m-%d %H:%M")
            
            return {
                "location": location_name,
                "forecast_date": target_date_str,
                "forecast_time": forecast_time,
                "days_ahead": args.days_ahead,
                "temperature": round(main.get("temp", 0), 1),
                "condition": weather.get("description", ""),
                "humidity": main.get("humidity", 0),
                "wind_speed": wind.get("speed", 0),
                "units": "metric"
            }
        except httpx.HTTPStatusError as e:
            logger.error(f"Weather Forecast API error: {e.response.text}")
            return {"error": f"Weather Forecast API error: {e.response.status_code}"}
        except Exception as e:
            logger.error(f"Weather forecast tool error: {e}")
            return {"error": str(e)}

definition = {
    "name": "getWeatherForecast",
    "description": "Return forecast weather for a given location and date (1-7 days ahead). Use this when users ask about weather 'tomorrow', 'next week', or specific future dates.",
    "parameters": {
        "type": "object",
        "properties": {
            "location": {"type": "string", "description": "City name or 'City, Country' or 'lat,lon'"},
            "days_ahead": {"type": "integer", "description": "Number of days ahead for forecast (1-7)", "minimum": 1, "maximum": 7}
        },
        "required": ["location", "days_ahead"]
    }
}


