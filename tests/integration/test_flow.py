import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.llm.gemini_client import gemini_client
import json

client = TestClient(app)

@pytest.mark.asyncio
async def test_chat_flow_mock_gemini(mocker):
    # Mock Gemini stream_chat to return a fixed response
    async def mock_stream_chat(history, message, tools=None):
        yield {"type": "text", "content": "Hello"}
    
    mocker.patch.object(gemini_client, "stream_chat", side_effect=mock_stream_chat)
    
    response = client.post("/api/v1/chat", json={"message": "Hi"})
    assert response.status_code == 200
    
    # Parse SSE
    content = ""
    for line in response.iter_lines():
        if line.startswith("data: "):
            data = line[6:]
            if data == "[DONE]":
                break
            event = json.loads(data)
            if event["event"] == "token":
                content += event["data"]
    
    assert content == "Hello"

@pytest.mark.asyncio
async def test_tool_execution_flow(mocker):
    # Mock Gemini to return a function call then text
    async def mock_stream_chat(history, message, tools=None):
        # If it's the first call (user message)
        if isinstance(message, str):
            yield {
                "type": "function_call", 
                "function_name": "getWeather", 
                "args": {"location": "London", "units": "metric"}
            }
        else:
            # Second call (function response)
            yield {"type": "text", "content": "The weather is cloudy."}

    mocker.patch.object(gemini_client, "stream_chat", side_effect=mock_stream_chat)
    
    # Mock tool execution to avoid real API call
    mocker.patch("app.tools.weather.get_weather", return_value={
        "location": "London", "temperature": 15, "condition": "cloudy"
    })
    
    response = client.post("/api/v1/chat", json={"message": "Weather in London?"})
    assert response.status_code == 200
    
    events = []
    for line in response.iter_lines():
        if line.startswith("data: "):
            data = line[6:]
            if data == "[DONE]":
                break
            events.append(json.loads(data))
            
    # Check events
    # 1. tool_call
    # 2. tool_result
    # 3. token
    
    event_types = [e["event"] for e in events]
    assert "tool_call" in event_types
    assert "tool_result" in event_types
    assert "token" in event_types
    
    # Check content
    final_text = "".join([e["data"] for e in events if e["event"] == "token"])
    assert "The weather is cloudy" in final_text
