"""
Redis caching implementation for Kasa Monitor
Provides decorators and utilities for caching with Redis
"""

import asyncio
import hashlib
import json
import logging
import os
import pickle
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Union

import redis.asyncio as redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


class RedisCache:
    """Redis cache manager with multiple serialization strategies"""

    def __init__(
        self,
        redis_url: Optional[str] = None,
        default_ttl: int = 3600,
        key_prefix: str = "kasa:",
        max_connections: int = 50,
    ):
        """
        Initialize Redis cache

        Args:
            redis_url: Redis connection URL
            default_ttl: Default TTL in seconds
            key_prefix: Prefix for all cache keys
            max_connections: Maximum number of connections in pool
        """
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.default_ttl = default_ttl
        self.key_prefix = key_prefix
        self.client = None
        self.connected = False
        self.max_connections = max_connections

        # Statistics
        self.stats = {"hits": 0, "misses": 0, "sets": 0, "deletes": 0, "errors": 0}

    async def connect(self):
        """Connect to Redis"""
        try:
            self.client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=False,
                max_connections=self.max_connections,
            )
            await self.client.ping()
            self.connected = True
            logger.info(f"Connected to Redis at {self.redis_url}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.connected = False
            raise

    async def disconnect(self):
        """Disconnect from Redis"""
        if self.client:
            await self.client.close()
            self.connected = False
            logger.info("Disconnected from Redis")

    def _make_key(self, key: str) -> str:
        """Create a namespaced key"""
        return f"{self.key_prefix}{key}"

    def _serialize(self, value: Any) -> bytes:
        """Serialize value for storage"""
        if isinstance(value, (str, int, float)):
            return json.dumps(value).encode("utf-8")
        elif isinstance(value, (dict, list)):
            return json.dumps(value).encode("utf-8")
        else:
            # Use pickle for complex objects
            return pickle.dumps(value)

    def _deserialize(self, data: bytes) -> Any:
        """Deserialize value from storage"""
        if data is None:
            return None

        try:
            # Try JSON first
            return json.loads(data.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            try:
                # Fall back to pickle
                return pickle.loads(data)
            except Exception as e:
                logger.error(f"Failed to deserialize data: {e}")
                return None

    async def get(self, key: str, default: Any = None) -> Any:
        """Get value from cache"""
        if not self.connected:
            return default

        try:
            full_key = self._make_key(key)
            data = await self.client.get(full_key)

            if data is None:
                self.stats["misses"] += 1
                return default

            self.stats["hits"] += 1
            return self._deserialize(data)
        except RedisError as e:
            logger.error(f"Redis get error: {e}")
            self.stats["errors"] += 1
            return default

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache"""
        if not self.connected:
            return False

        try:
            full_key = self._make_key(key)
            serialized = self._serialize(value)
            ttl = ttl or self.default_ttl

            await self.client.setex(full_key, ttl, serialized)
            self.stats["sets"] += 1
            return True
        except RedisError as e:
            logger.error(f"Redis set error: {e}")
            self.stats["errors"] += 1
            return False

    async def delete(self, key: str) -> bool:
        """Delete value from cache"""
        if not self.connected:
            return False

        try:
            full_key = self._make_key(key)
            result = await self.client.delete(full_key)
            self.stats["deletes"] += 1
            return result > 0
        except RedisError as e:
            logger.error(f"Redis delete error: {e}")
            self.stats["errors"] += 1
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        if not self.connected:
            return False

        try:
            full_key = self._make_key(key)
            return await self.client.exists(full_key) > 0
        except RedisError as e:
            logger.error(f"Redis exists error: {e}")
            return False

    async def expire(self, key: str, ttl: int) -> bool:
        """Set expiration on existing key"""
        if not self.connected:
            return False

        try:
            full_key = self._make_key(key)
            return await self.client.expire(full_key, ttl)
        except RedisError as e:
            logger.error(f"Redis expire error: {e}")
            return False

    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values at once"""
        if not self.connected:
            return {}

        try:
            full_keys = [self._make_key(k) for k in keys]
            values = await self.client.mget(full_keys)

            result = {}
            for key, value in zip(keys, values):
                if value is not None:
                    result[key] = self._deserialize(value)
                    self.stats["hits"] += 1
                else:
                    self.stats["misses"] += 1

            return result
        except RedisError as e:
            logger.error(f"Redis mget error: {e}")
            self.stats["errors"] += 1
            return {}

    async def set_many(
        self, mapping: Dict[str, Any], ttl: Optional[int] = None
    ) -> bool:
        """Set multiple values at once"""
        if not self.connected:
            return False

        try:
            ttl = ttl or self.default_ttl
            pipe = self.client.pipeline()

            for key, value in mapping.items():
                full_key = self._make_key(key)
                serialized = self._serialize(value)
                pipe.setex(full_key, ttl, serialized)

            await pipe.execute()
            self.stats["sets"] += len(mapping)
            return True
        except RedisError as e:
            logger.error(f"Redis mset error: {e}")
            self.stats["errors"] += 1
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern"""
        if not self.connected:
            return 0

        try:
            full_pattern = self._make_key(pattern)
            keys = []
            async for key in self.client.scan_iter(full_pattern):
                keys.append(key)

            if keys:
                deleted = await self.client.delete(*keys)
                self.stats["deletes"] += deleted
                return deleted
            return 0
        except RedisError as e:
            logger.error(f"Redis delete pattern error: {e}")
            self.stats["errors"] += 1
            return 0

    async def clear(self) -> bool:
        """Clear all cache entries with our prefix"""
        if not self.connected:
            return False

        try:
            deleted = await self.delete_pattern("*")
            logger.info(f"Cleared {deleted} cache entries")
            return True
        except RedisError as e:
            logger.error(f"Redis clear error: {e}")
            return False

    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        stats = self.stats.copy()

        # Calculate hit ratio
        total_requests = stats["hits"] + stats["misses"]
        if total_requests > 0:
            stats["hit_ratio"] = stats["hits"] / total_requests
        else:
            stats["hit_ratio"] = 0

        # Get Redis info if connected
        if self.connected:
            try:
                info = await self.client.info()
                stats["redis_info"] = {
                    "version": info.get("redis_version"),
                    "connected_clients": info.get("connected_clients"),
                    "used_memory_mb": info.get("used_memory", 0) / (1024 * 1024),
                    "total_keys": await self.client.dbsize(),
                }
            except:
                pass

        return stats

    async def ttl(self, key: str) -> int:
        """Get remaining TTL for a key"""
        if not self.connected:
            return -1

        try:
            full_key = self._make_key(key)
            return await self.client.ttl(full_key)
        except RedisError as e:
            logger.error(f"Redis ttl error: {e}")
            return -1


# Cache decorators
def cache_key_builder(
    func: Callable, prefix: Optional[str] = None, include_kwargs: bool = True
) -> str:
    """Build cache key from function and arguments"""
    parts = [prefix or func.__name__]

    def builder(*args, **kwargs):
        key_parts = parts.copy()

        # Add positional arguments
        for arg in args[1:]:  # Skip 'self' if present
            if hasattr(arg, "__dict__"):
                # For objects, use their id or a hash
                key_parts.append(str(id(arg)))
            else:
                key_parts.append(str(arg))

        # Add keyword arguments if requested
        if include_kwargs and kwargs:
            sorted_kwargs = sorted(kwargs.items())
            for k, v in sorted_kwargs:
                key_parts.append(f"{k}={v}")

        # Create hash for long keys
        key = ":".join(key_parts)
        if len(key) > 200:
            key_hash = hashlib.md5(key.encode()).hexdigest()
            key = f"{parts[0]}:{key_hash}"

        return key

    return builder


def cached(
    ttl: Optional[int] = None,
    key_prefix: Optional[str] = None,
    cache_none: bool = False,
    key_builder: Optional[Callable] = None,
):
    """
    Decorator for caching function results

    Args:
        ttl: Time to live in seconds
        key_prefix: Prefix for cache key
        cache_none: Whether to cache None values
        key_builder: Custom key builder function
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Get cache instance
            cache = get_redis_cache()
            if not cache or not cache.connected:
                # If cache not available, just run the function
                return await func(*args, **kwargs)

            # Build cache key
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                builder = cache_key_builder(func, key_prefix)
                cache_key = builder(*args, **kwargs)

            # Try to get from cache
            cached_value = await cache.get(cache_key)
            if cached_value is not None or (
                cache_none and await cache.exists(cache_key)
            ):
                logger.debug(f"Cache hit for {cache_key}")
                return cached_value

            # Execute function
            result = await func(*args, **kwargs)

            # Cache result if not None or if cache_none is True
            if result is not None or cache_none:
                await cache.set(cache_key, result, ttl)
                logger.debug(f"Cached result for {cache_key}")

            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # For sync functions, we need to run in async context
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(async_wrapper(*args, **kwargs))

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def invalidate_cache(pattern: str):
    """
    Decorator to invalidate cache entries matching pattern after function execution

    Args:
        pattern: Pattern of cache keys to invalidate
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)

            # Invalidate cache
            cache = get_redis_cache()
            if cache and cache.connected:
                await cache.delete_pattern(pattern)
                logger.debug(f"Invalidated cache pattern: {pattern}")

            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            result = func(*args, **kwargs)

            # Invalidate cache in async context
            loop = asyncio.get_event_loop()
            cache = get_redis_cache()
            if cache and cache.connected:
                loop.run_until_complete(cache.delete_pattern(pattern))
                logger.debug(f"Invalidated cache pattern: {pattern}")

            return result

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# Global cache instance
_redis_cache: Optional[RedisCache] = None


async def init_redis_cache(**kwargs) -> RedisCache:
    """Initialize global Redis cache"""
    global _redis_cache
    _redis_cache = RedisCache(**kwargs)
    await _redis_cache.connect()
    return _redis_cache


def get_redis_cache() -> Optional[RedisCache]:
    """Get global Redis cache instance"""
    return _redis_cache


async def close_redis_cache():
    """Close global Redis cache"""
    global _redis_cache
    if _redis_cache:
        await _redis_cache.disconnect()
        _redis_cache = None
