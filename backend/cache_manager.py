"""
Cache Manager Module for Kasa Monitor
Implements multi-level caching with Redis and in-memory cache
"""

import asyncio
import hashlib
import json
import logging
import os
import pickle
import sys
import time
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable, Dict, List, Optional

# Import the sanitize_for_log function from server module
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from server import sanitize_for_log

import redis.asyncio as redis
from aiocache import Cache
from aiocache.serializers import JsonSerializer, PickleSerializer

logger = logging.getLogger(__name__)


class CacheManager:
    """Manages multi-level caching with L1 (memory) and L2 (Redis) caches"""

    def __init__(
        self,
        redis_url: Optional[str] = None,
        l1_ttl: int = 60,
        l2_ttl: int = 300,
        l1_max_size: int = 100,
    ):
        """
        Initialize cache manager

        Args:
            redis_url: Redis connection URL
            l1_ttl: L1 cache TTL in seconds
            l2_ttl: L2 cache TTL in seconds
            l1_max_size: Maximum number of items in L1 cache
        """
        self.l1_ttl = l1_ttl
        self.l2_ttl = l2_ttl
        self.l1_max_size = l1_max_size

        # L1 Cache (in-memory)
        self.l1_cache = Cache(Cache.MEMORY, ttl=l1_ttl, serializer=JsonSerializer())

        # L2 Cache (Redis)
        self.redis_client = None
        if redis_url:
            try:
                self.redis_client = redis.from_url(
                    redis_url, encoding="utf-8", decode_responses=False
                )
                logger.info("Redis cache initialized")
            except Exception as e:
                logger.warning(
                    f"Failed to connect to Redis: {e}. Using memory cache only."
                )

        # Cache statistics
        self.stats = {
            "hits": 0,
            "misses": 0,
            "l1_hits": 0,
            "l2_hits": 0,
            "sets": 0,
            "deletes": 0,
            "errors": 0,
        }

    async def get(self, key: str, default: Any = None) -> Any:
        """
        Get value from cache (checks L1 then L2)

        Args:
            key: Cache key
            default: Default value if not found

        Returns:
            Cached value or default
        """
        try:
            # Check L1 cache
            value = await self.l1_cache.get(key)
            if value is not None:
                self.stats["hits"] += 1
                self.stats["l1_hits"] += 1
                return value

            # Check L2 cache (Redis)
            if self.redis_client:
                value = await self.redis_client.get(key)
                if value is not None:
                    # Deserialize from Redis
                    try:
                        value = json.loads(value)
                    except json.JSONDecodeError:
                        value = pickle.loads(value)

                    # Promote to L1 cache
                    await self.l1_cache.set(key, value, ttl=self.l1_ttl)

                    self.stats["hits"] += 1
                    self.stats["l2_hits"] += 1
                    return value

            self.stats["misses"] += 1
            return default

        except Exception as e:
            logger.error("Cache get error for key %s: %s", sanitize_for_log(key), sanitize_for_log(str(e)))
            self.stats["errors"] += 1
            return default

    async def set(
        self, key: str, value: Any, ttl: Optional[int] = None, l1_only: bool = False
    ) -> bool:
        """
        Set value in cache

        Args:
            key: Cache key
            value: Value to cache
            ttl: Optional TTL override
            l1_only: Only cache in L1 (memory)

        Returns:
            True if successful
        """
        try:
            # Set in L1 cache
            await self.l1_cache.set(key, value, ttl=ttl or self.l1_ttl)

            # Set in L2 cache (Redis) if not L1 only
            if not l1_only and self.redis_client:
                # Serialize for Redis
                try:
                    serialized = json.dumps(value)
                except (TypeError, ValueError):
                    serialized = pickle.dumps(value)

                await self.redis_client.set(key, serialized, ex=ttl or self.l2_ttl)

            self.stats["sets"] += 1
            return True

        except Exception as e:
            logger.error("Cache set error for key %s: %s", sanitize_for_log(key), sanitize_for_log(str(e)))
            self.stats["errors"] += 1
            return False

    async def delete(self, key: str) -> bool:
        """
        Delete value from cache

        Args:
            key: Cache key

        Returns:
            True if successful
        """
        try:
            # Delete from L1
            await self.l1_cache.delete(key)

            # Delete from L2
            if self.redis_client:
                await self.redis_client.delete(key)

            self.stats["deletes"] += 1
            return True

        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            self.stats["errors"] += 1
            return False

    async def clear(self, pattern: Optional[str] = None) -> int:
        """
        Clear cache entries

        Args:
            pattern: Optional pattern to match keys (Redis only)

        Returns:
            Number of keys deleted
        """
        count = 0

        try:
            # Clear L1 cache
            await self.l1_cache.clear()

            # Clear L2 cache
            if self.redis_client:
                if pattern:
                    # Delete keys matching pattern
                    cursor = 0
                    while True:
                        cursor, keys = await self.redis_client.scan(
                            cursor, match=pattern, count=100
                        )
                        if keys:
                            count += len(keys)
                            await self.redis_client.delete(*keys)
                        if cursor == 0:
                            break
                else:
                    # Clear all keys (use with caution)
                    await self.redis_client.flushdb()

            return count

        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            self.stats["errors"] += 1
            return 0

    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """
        Get multiple values from cache

        Args:
            keys: List of cache keys

        Returns:
            Dictionary of key-value pairs
        """
        results = {}

        # Get from L1 cache
        for key in keys:
            value = await self.l1_cache.get(key)
            if value is not None:
                results[key] = value

        # Get remaining from L2 cache
        missing_keys = [k for k in keys if k not in results]
        if missing_keys and self.redis_client:
            values = await self.redis_client.mget(missing_keys)
            for key, value in zip(missing_keys, values):
                if value is not None:
                    try:
                        results[key] = json.loads(value)
                    except json.JSONDecodeError:
                        results[key] = pickle.loads(value)

                    # Promote to L1 cache
                    await self.l1_cache.set(key, results[key], ttl=self.l1_ttl)

        return results

    async def set_many(
        self, mapping: Dict[str, Any], ttl: Optional[int] = None
    ) -> bool:
        """
        Set multiple values in cache

        Args:
            mapping: Dictionary of key-value pairs
            ttl: Optional TTL override

        Returns:
            True if successful
        """
        try:
            # Set in L1 cache
            for key, value in mapping.items():
                await self.l1_cache.set(key, value, ttl=ttl or self.l1_ttl)

            # Set in L2 cache
            if self.redis_client:
                # Serialize values
                serialized = {}
                for key, value in mapping.items():
                    try:
                        serialized[key] = json.dumps(value)
                    except (TypeError, ValueError):
                        serialized[key] = pickle.dumps(value)

                # Use pipeline for efficiency
                async with self.redis_client.pipeline() as pipe:
                    for key, value in serialized.items():
                        pipe.set(key, value, ex=ttl or self.l2_ttl)
                    await pipe.execute()

            return True

        except Exception as e:
            logger.error(f"Cache set_many error: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = (
            (self.stats["hits"] / total_requests * 100) if total_requests > 0 else 0
        )

        return {
            **self.stats,
            "total_requests": total_requests,
            "hit_rate": f"{hit_rate:.2f}%",
            "l1_hit_rate": f"{(self.stats['l1_hits'] / total_requests * 100) if total_requests > 0 else 0:.2f}%",
            "l2_hit_rate": f"{(self.stats['l2_hits'] / total_requests * 100) if total_requests > 0 else 0:.2f}%",
        }

    async def close(self):
        """Close cache connections"""
        if self.redis_client:
            await self.redis_client.close()


def cache_key(*args, **kwargs) -> str:
    """Generate cache key from arguments"""
    key_parts = [str(arg) for arg in args]
    key_parts.extend([f"{k}:{v}" for k, v in sorted(kwargs.items())])
    key_string = ":".join(key_parts)

    # Hash if key is too long
    if len(key_string) > 250:
        key_string = hashlib.md5(key_string.encode()).hexdigest()

    return key_string


def cached(
    ttl: int = 300,
    key_prefix: Optional[str] = None,
    key_builder: Optional[Callable] = None,
    cache_none: bool = False,
):
    """
    Decorator to cache function results

    Args:
        ttl: Cache TTL in seconds
        key_prefix: Optional prefix for cache keys
        key_builder: Optional custom key builder function
        cache_none: Whether to cache None results
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Build cache key
            if key_builder:
                cache_key_str = key_builder(*args, **kwargs)
            else:
                cache_key_str = cache_key(*args, **kwargs)

            if key_prefix:
                cache_key_str = f"{key_prefix}:{cache_key_str}"
            else:
                cache_key_str = f"{func.__module__}.{func.__name__}:{cache_key_str}"

            # Try to get from cache
            cache_manager = kwargs.pop("_cache", None)
            if not cache_manager:
                # No cache manager, just call function
                return await func(*args, **kwargs)

            result = await cache_manager.get(cache_key_str)
            if result is not None or (result is None and cache_none):
                return result

            # Call function and cache result
            result = await func(*args, **kwargs)

            if result is not None or cache_none:
                await cache_manager.set(cache_key_str, result, ttl=ttl)

            return result

        return wrapper

    return decorator


class QueryCache:
    """Specialized cache for database queries"""

    def __init__(self, cache_manager: CacheManager):
        self.cache_manager = cache_manager
        self.query_ttls = {
            "devices": 60,  # Device list changes infrequently
            "readings": 10,  # Recent readings change frequently
            "aggregations": 300,  # Aggregated data is more stable
            "statistics": 600,  # Statistics can be cached longer
        }

    def _get_query_key(self, query: str, params: Optional[tuple] = None) -> str:
        """Generate cache key for query"""
        # Normalize query
        normalized = " ".join(query.split()).lower()

        # Add parameters to key
        if params:
            param_str = ":".join(str(p) for p in params)
            key = (
                f"query:{hashlib.md5(f'{normalized}:{param_str}'.encode()).hexdigest()}"
            )
        else:
            key = f"query:{hashlib.md5(normalized.encode()).hexdigest()}"

        return key

    def _determine_ttl(self, query: str) -> int:
        """Determine TTL based on query type"""
        query_lower = query.lower()

        if "devices" in query_lower:
            return self.query_ttls["devices"]
        elif "readings" in query_lower:
            return self.query_ttls["readings"]
        elif any(word in query_lower for word in ["sum", "avg", "count", "max", "min"]):
            return self.query_ttls["aggregations"]
        elif "statistics" in query_lower or "stats" in query_lower:
            return self.query_ttls["statistics"]
        else:
            return 30  # Default TTL

    async def get_query_result(
        self, query: str, params: Optional[tuple] = None
    ) -> Optional[Any]:
        """Get cached query result"""
        key = self._get_query_key(query, params)
        return await self.cache_manager.get(key)

    async def set_query_result(
        self, query: str, params: Optional[tuple], result: Any
    ) -> bool:
        """Cache query result"""
        key = self._get_query_key(query, params)
        ttl = self._determine_ttl(query)
        return await self.cache_manager.set(key, result, ttl=ttl)

    async def invalidate_pattern(self, pattern: str):
        """Invalidate cached queries matching pattern"""
        await self.cache_manager.clear(f"query:*{pattern}*")


class ResponseCache:
    """Cache for API responses"""

    def __init__(self, cache_manager: CacheManager):
        self.cache_manager = cache_manager

    def get_response_key(
        self, method: str, path: str, params: Optional[Dict] = None
    ) -> str:
        """Generate cache key for API response"""
        key_parts = [method.upper(), path]

        if params:
            # Sort parameters for consistent keys
            param_str = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
            key_parts.append(param_str)

        return f"response:{':'.join(key_parts)}"

    async def get_response(
        self, method: str, path: str, params: Optional[Dict] = None
    ) -> Optional[Any]:
        """Get cached API response"""
        key = self.get_response_key(method, path, params)
        return await self.cache_manager.get(key)

    async def set_response(
        self,
        method: str,
        path: str,
        params: Optional[Dict],
        response: Any,
        ttl: int = 60,
    ) -> bool:
        """Cache API response"""
        key = self.get_response_key(method, path, params)
        return await self.cache_manager.set(key, response, ttl=ttl)

    async def invalidate_endpoint(self, path_pattern: str):
        """Invalidate cached responses for endpoint"""
        await self.cache_manager.clear(f"response:*{path_pattern}*")
