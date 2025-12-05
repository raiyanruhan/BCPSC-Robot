import redis.asyncio as redis
from app.config import settings
import json
import logging
from typing import Optional, Any
import time

logger = logging.getLogger(__name__)

class CacheInterface:
    async def get(self, key: str) -> Optional[Any]:
        raise NotImplementedError

    async def set(self, key: str, value: Any, ttl: int) -> None:
        raise NotImplementedError

class InMemoryCache(CacheInterface):
    def __init__(self):
        self._cache = {}
        self._expiry = {}

    async def get(self, key: str) -> Optional[Any]:
        if key in self._cache:
            if time.time() < self._expiry.get(key, 0):
                return self._cache[key]
            else:
                del self._cache[key]
                del self._expiry[key]
        return None

    async def set(self, key: str, value: Any, ttl: int) -> None:
        self._cache[key] = value
        self._expiry[key] = time.time() + ttl

class RedisCache(CacheInterface):
    def __init__(self):
        self.redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
        self.fallback = InMemoryCache()
        self.redis_available = False

    async def initialize(self):
        try:
            await self.redis.ping()
            self.redis_available = True
            logger.info("Redis connected successfully.")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Using in-memory fallback.")
            self.redis_available = False

    async def get(self, key: str) -> Optional[Any]:
        if self.redis_available:
            try:
                val = await self.redis.get(key)
                if val:
                    return json.loads(val)
            except Exception as e:
                logger.error(f"Redis get error: {e}")
                # Fallback on error? Maybe not for get, as consistency issues.
                # But for this project, availability > consistency?
                # Let's just return None to force re-fetch.
                return None
        return await self.fallback.get(key)

    async def set(self, key: str, value: Any, ttl: int) -> None:
        if self.redis_available:
            try:
                await self.redis.set(key, json.dumps(value), ex=ttl)
                return
            except Exception as e:
                logger.error(f"Redis set error: {e}")
        
        await self.fallback.set(key, value, ttl)

# Global cache instance
cache = RedisCache()
