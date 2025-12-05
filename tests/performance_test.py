import asyncio
import httpx
import time
import statistics
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

URL = "http://localhost:8000/api/v1/chat"
CONCURRENT_USERS = 50
TOTAL_REQUESTS = 50

async def simulate_user(user_id):
    start_time = time.time()
    first_token_time = None
    
    async with httpx.AsyncClient() as client:
        try:
            async with client.stream("POST", URL, json={"message": "What is the weather in London?"}, timeout=30.0) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        if first_token_time is None:
                            first_token_time = time.time()
                        
                        data = line[6:]
                        if data == "[DONE]":
                            break
        except Exception as e:
            logger.error(f"User {user_id} error: {e}")
            return None, None

    end_time = time.time()
    
    if first_token_time:
        ttft = (first_token_time - start_time) * 1000 # ms
        total_time = (end_time - start_time) * 1000 # ms
        return ttft, total_time
    return None, None

async def main():
    logger.info(f"Starting performance test with {CONCURRENT_USERS} concurrent users...")
    
    tasks = []
    for i in range(CONCURRENT_USERS):
        tasks.append(simulate_user(i))
    
    results = await asyncio.gather(*tasks)
    
    ttfts = [r[0] for r in results if r[0] is not None]
    totals = [r[1] for r in results if r[1] is not None]
    
    if not ttfts:
        logger.error("No successful requests.")
        return

    logger.info(f"Successful requests: {len(ttfts)}/{CONCURRENT_USERS}")
    
    logger.info("--- Metrics ---")
    logger.info(f"P50 TTFT: {statistics.median(ttfts):.2f} ms")
    logger.info(f"P95 TTFT: {statistics.quantiles(ttfts, n=20)[18]:.2f} ms") # 19th quantile is 95%
    logger.info(f"P50 Total Time: {statistics.median(totals):.2f} ms")
    logger.info(f"P95 Total Time: {statistics.quantiles(totals, n=20)[18]:.2f} ms")

if __name__ == "__main__":
    asyncio.run(main())
