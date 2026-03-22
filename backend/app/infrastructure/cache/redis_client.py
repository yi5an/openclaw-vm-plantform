"""
Redis client for caching and session management.
"""
import redis.asyncio as redis
from typing import Optional, Any, Dict
import json
from app.core.config import settings


class RedisClient:
    """Async Redis client wrapper."""
    
    def __init__(self):
        self.client: Optional[redis.Redis] = None
    
    async def connect(self):
        """Connect to Redis."""
        self.client = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            max_connections=settings.REDIS_MAX_CONNECTIONS
        )
    
    async def disconnect(self):
        """Disconnect from Redis."""
        if self.client:
            await self.client.close()
    
    async def get(self, key: str) -> Optional[str]:
        """Get value by key."""
        return await self.client.get(key)
    
    async def set(self, key: str, value: str, ex: Optional[int] = None):
        """Set key-value pair with optional expiration."""
        await self.client.set(key, value, ex=ex)
    
    async def delete(self, key: str):
        """Delete key."""
        await self.client.delete(key)
    
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        return await self.client.exists(key) > 0
    
    async def expire(self, key: str, seconds: int):
        """Set expiration time for key."""
        await self.client.expire(key, seconds)
    
    async def incr(self, key: str) -> int:
        """Increment value."""
        return await self.client.incr(key)
    
    async def incrbyfloat(self, key: str, amount: float) -> float:
        """Increment value by float."""
        return await self.client.incrbyfloat(key, amount)
    
    # Hash operations
    async def hget(self, name: str, key: str) -> Optional[str]:
        """Get hash field value."""
        return await self.client.hget(name, key)
    
    async def hgetall(self, name: str) -> Dict[str, str]:
        """Get all hash fields."""
        return await self.client.hgetall(name)
    
    async def hset(self, name: str, key: str, value: str):
        """Set hash field value."""
        await self.client.hset(name, key, value)
    
    async def hmset(self, name: str, mapping: Dict[str, str]):
        """Set multiple hash fields."""
        await self.client.hset(name, mapping=mapping)
    
    async def hdel(self, name: str, key: str):
        """Delete hash field."""
        await self.client.hdel(name, key)
    
    async def hincrby(self, name: str, key: str, amount: int = 1) -> int:
        """Increment hash field by integer."""
        return await self.client.hincrby(name, key, amount)
    
    async def hincrbyfloat(self, name: str, key: str, amount: float) -> float:
        """Increment hash field by float."""
        return await self.client.hincrbyfloat(name, key, amount)
    
    # JSON helpers
    async def get_json(self, key: str) -> Optional[Any]:
        """Get JSON value."""
        value = await self.get(key)
        if value:
            return json.loads(value)
        return None
    
    async def set_json(self, key: str, value: Any, ex: Optional[int] = None):
        """Set JSON value."""
        await self.set(key, json.dumps(value), ex=ex)
    
    # Utility methods
    async def set_if_not_exists(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """Set key-value only if key doesn't exist (NX)."""
        result = await self.client.set(key, value, ex=ex, nx=True)
        return result is not None
    
    async def acquire_lock(self, lock_name: str, timeout: int = 30) -> bool:
        """
        Acquire a distributed lock.
        
        Args:
            lock_name: Name of the lock
            timeout: Lock timeout in seconds
            
        Returns:
            True if lock acquired, False otherwise
        """
        lock_key = f"lock:{lock_name}"
        return await self.set_if_not_exists(lock_key, "1", ex=timeout)
    
    async def release_lock(self, lock_name: str):
        """Release a distributed lock."""
        lock_key = f"lock:{lock_name}"
        await self.delete(lock_key)


# Global Redis client instance
redis_client = RedisClient()


async def get_redis() -> RedisClient:
    """Dependency to get Redis client."""
    return redis_client
