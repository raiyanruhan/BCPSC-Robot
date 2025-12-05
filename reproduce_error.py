import httpx
import asyncio
import json

async def reproduce():
    url = "http://localhost:8000/api/v1/chat"
    print(f"Sending request to {url}...")
    try:
        async with httpx.AsyncClient() as client:
            async with client.stream("POST", url, json={"message": "Hello"}, timeout=30.0) as response:
                async for line in response.aiter_lines():
                    print(f"Received: {line}")
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    asyncio.run(reproduce())
