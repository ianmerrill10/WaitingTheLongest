"""
===============================================================================
Waiting The Longest™ - Caching Middleware
===============================================================================
Purpose: In-memory and distributed caching for API responses.
         Reduces database load and improves response times.

Author: Waiting The Longest™ Development Team
===============================================================================
"""

import hashlib
import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Callable, Dict, Optional, TypeVar, Union

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class CacheEntry:
    """Cached data entry."""
    value: Any
    expires_at: float
    created_at: float
    hits: int = 0
    
    @property
    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        return time.time() > self.expires_at
    
    @property
    def ttl_remaining(self) -> float:
        """Get remaining TTL in seconds."""
        return max(0, self.expires_at - time.time())


class CacheBackend(ABC):
    """Abstract cache backend interface."""
    
    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any, ttl: int) -> None:
        """Set value in cache with TTL in seconds."""
        pass
    
    @abstractmethod
    def delete(self, key: str) -> None:
        """Delete value from cache."""
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """Clear all cached values."""
        pass
    
    @abstractmethod
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        pass


class InMemoryCache(CacheBackend):
    """
    Simple in-memory cache implementation.
    
    Suitable for single-instance deployments.
    For multi-instance, use Redis.
    """
    
    def __init__(self, max_size: int = 1000):
        """
        Initialize in-memory cache.
        
        Args:
            max_size: Maximum number of entries before eviction
        """
        self._cache: Dict[str, CacheEntry] = {}
        self._max_size = max_size
        self._hits = 0
        self._misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        entry = self._cache.get(key)
        
        if entry is None:
            self._misses += 1
            return None
        
        if entry.is_expired:
            del self._cache[key]
            self._misses += 1
            return None
        
        entry.hits += 1
        self._hits += 1
        return entry.value
    
    def set(self, key: str, value: Any, ttl: int) -> None:
        """Set value in cache."""
        # Evict if at max size
        if len(self._cache) >= self._max_size:
            self._evict_expired()
            if len(self._cache) >= self._max_size:
                self._evict_lru()
        
        now = time.time()
        self._cache[key] = CacheEntry(
            value=value,
            expires_at=now + ttl,
            created_at=now
        )
    
    def delete(self, key: str) -> None:
        """Delete value from cache."""
        self._cache.pop(key, None)
    
    def clear(self) -> None:
        """Clear all cached values."""
        self._cache.clear()
        self._hits = 0
        self._misses = 0
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0
        
        return {
            "type": "in_memory",
            "size": len(self._cache),
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(hit_rate, 2)
        }
    
    def _evict_expired(self) -> None:
        """Remove expired entries."""
        expired = [
            key for key, entry in self._cache.items()
            if entry.is_expired
        ]
        for key in expired:
            del self._cache[key]
    
    def _evict_lru(self) -> None:
        """Evict least recently used entry."""
        if not self._cache:
            return
        # Find entry with lowest hit count
        lru_key = min(self._cache, key=lambda k: self._cache[k].hits)
        del self._cache[lru_key]


class RedisCache(CacheBackend):
    """
    Redis cache backend for distributed deployments.
    
    Requires redis package.
    """
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        prefix: str = "wtl:"
    ):
        """Initialize Redis cache."""
        try:
            import redis
            self._redis = redis.Redis(
                host=host,
                port=port,
                db=db,
                password=password,
                decode_responses=True
            )
            self._prefix = prefix
            self._available = True
            # Test connection
            self._redis.ping()
        except Exception as e:
            logger.warning(f"Redis not available: {e}. Falling back to in-memory cache.")
            self._available = False
            self._fallback = InMemoryCache()
    
    def _key(self, key: str) -> str:
        """Add prefix to key."""
        return f"{self._prefix}{key}"
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from Redis."""
        if not self._available:
            return self._fallback.get(key)
        
        try:
            data = self._redis.get(self._key(key))
            if data is None:
                return None
            return json.loads(data)
        except Exception as e:
            logger.warning(f"Redis get error: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: int) -> None:
        """Set value in Redis."""
        if not self._available:
            self._fallback.set(key, value, ttl)
            return
        
        try:
            self._redis.setex(
                self._key(key),
                ttl,
                json.dumps(value)
            )
        except Exception as e:
            logger.warning(f"Redis set error: {e}")
    
    def delete(self, key: str) -> None:
        """Delete value from Redis."""
        if not self._available:
            self._fallback.delete(key)
            return
        
        try:
            self._redis.delete(self._key(key))
        except Exception as e:
            logger.warning(f"Redis delete error: {e}")
    
    def clear(self) -> None:
        """Clear all cached values with prefix."""
        if not self._available:
            self._fallback.clear()
            return
        
        try:
            keys = self._redis.keys(f"{self._prefix}*")
            if keys:
                self._redis.delete(*keys)
        except Exception as e:
            logger.warning(f"Redis clear error: {e}")
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        if not self._available:
            return {**self._fallback.stats(), "fallback": True}
        
        try:
            info = self._redis.info("stats")
            return {
                "type": "redis",
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "used_memory": self._redis.info("memory").get("used_memory_human"),
                "connected": True
            }
        except Exception as e:
            return {"type": "redis", "error": str(e), "connected": False}


def generate_cache_key(prefix: str, *args, **kwargs) -> str:
    """Generate a cache key from arguments."""
    key_data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True)
    hash_str = hashlib.md5(key_data.encode()).hexdigest()[:12]
    return f"{prefix}:{hash_str}"


def cached(
    ttl: int = 60,
    key_prefix: Optional[str] = None,
    cache: Optional[CacheBackend] = None
):
    """
    Decorator for caching function results.
    
    Args:
        ttl: Time to live in seconds
        key_prefix: Cache key prefix (defaults to function name)
        cache: Cache backend instance
    
    Usage:
        @cached(ttl=300)
        def get_expensive_data():
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        nonlocal key_prefix
        if key_prefix is None:
            key_prefix = func.__name__
        
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            _cache = cache or get_cache()
            key = generate_cache_key(key_prefix, *args, **kwargs)
            
            # Try to get from cache
            cached_value = _cache.get(key)
            if cached_value is not None:
                return cached_value
            
            # Call function and cache result
            result = func(*args, **kwargs)
            _cache.set(key, result, ttl)
            return result
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            _cache = cache or get_cache()
            key = generate_cache_key(key_prefix, *args, **kwargs)
            
            cached_value = _cache.get(key)
            if cached_value is not None:
                return cached_value
            
            result = await func(*args, **kwargs)
            _cache.set(key, result, ttl)
            return result
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return wrapper
    
    return decorator


# Singleton cache instance
_cache: Optional[CacheBackend] = None


def get_cache() -> CacheBackend:
    """Get or create the cache singleton."""
    global _cache
    if _cache is None:
        # Try Redis first, fall back to in-memory
        import os
        redis_url = os.environ.get("REDIS_URL")
        if redis_url:
            _cache = RedisCache(host=redis_url)
        else:
            _cache = InMemoryCache()
    return _cache


def invalidate_cache(*patterns: str) -> None:
    """Invalidate cache entries matching patterns."""
    cache = get_cache()
    for pattern in patterns:
        cache.delete(pattern)
