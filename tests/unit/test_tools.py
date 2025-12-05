import pytest
from app.tools.weather import get_weather
from app.schemas import GetWeatherArgs
from app.config import settings

@pytest.mark.asyncio
async def test_get_weather_no_key():
    # Save original key
    original_key = settings.WEATHER_API_KEY
    settings.WEATHER_API_KEY = None
    
    args = GetWeatherArgs(location="London")
    result = await get_weather(args)
    assert "error" in result
    
    # Restore key
    settings.WEATHER_API_KEY = original_key

@pytest.mark.asyncio
async def test_get_weather_mock(mocker):
    # Mock httpx
    mock_response = mocker.Mock()
    mock_response.json.return_value = {
        "name": "London",
        "main": {"temp": 15, "humidity": 80},
        "weather": [{"description": "cloudy"}],
        "wind": {"speed": 5}
    }
    mock_response.status_code = 200
    
    patcher = mocker.patch("httpx.AsyncClient.get", return_value=mock_response)
    
    args = GetWeatherArgs(location="London")
    result = await get_weather(args)
    
    assert result["location"] == "London"
    assert result["temperature"] == 15
    assert result["condition"] == "cloudy"
