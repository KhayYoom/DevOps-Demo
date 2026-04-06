"""
cache.py - Redis caching layer for the Inventory System.

This module provides a thin wrapper around redis-py for caching
product data. It uses JSON serialization so that complex Python
objects (dicts, lists) can be stored and retrieved transparently.

Why cache?
    Database queries are relatively slow. By caching frequently
    accessed products in Redis, the API can respond much faster
    for repeated reads.

TTL (Time To Live):
    Every cached entry expires after a configurable TTL (default
    300 seconds / 5 minutes). This ensures stale data is eventually
    refreshed from the database.
"""

import json
import redis


class CacheManager:
    """
    Manages Redis connections and cached key-value operations.

    Usage:
        cache = CacheManager()
        cache.connect("redis://localhost:6379")
        cache.set("product:1", {"name": "Widget", "price": 9.99})
        data = cache.get("product:1")
        cache.disconnect()
    """

    def __init__(self):
        """Initialize the CacheManager with no active connection."""
        self._client = None

    def connect(self, redis_url):
        """
        Connect to a Redis server.

        Args:
            redis_url: Redis connection URI, e.g. "redis://localhost:6379".
        """
        self._client = redis.from_url(redis_url, decode_responses=True)
        # Verify the connection is alive
        self._client.ping()

    def disconnect(self):
        """Close the Redis connection."""
        if self._client:
            self._client.close()
            self._client = None

    def is_connected(self):
        """Check whether the Redis connection is active."""
        if self._client is None:
            return False
        try:
            self._client.ping()
            return True
        except Exception:
            return False

    def set(self, key, value, ttl=300):
        """
        Store a value in the cache with an optional TTL.

        Args:
            key: Cache key (string).
            value: Any JSON-serializable Python object.
            ttl: Time to live in seconds (default 300). Set to None for no expiry.
        """
        serialized = json.dumps(value)
        if ttl is not None:
            self._client.setex(key, ttl, serialized)
        else:
            self._client.set(key, serialized)

    def get(self, key):
        """
        Retrieve a value from the cache.

        Args:
            key: Cache key.

        Returns:
            The deserialized Python object, or None if the key does not exist.
        """
        raw = self._client.get(key)
        if raw is None:
            return None
        return json.loads(raw)

    def delete(self, key):
        """
        Remove a key from the cache.

        Args:
            key: Cache key.

        Returns:
            bool: True if the key existed and was deleted.
        """
        return self._client.delete(key) > 0

    def clear(self):
        """Flush all keys from the current Redis database."""
        self._client.flushdb()

    def get_stats(self):
        """
        Return basic cache statistics.

        Returns:
            dict: Contains 'keys' (total key count) and 'memory' (used memory).
        """
        info = self._client.info(section="memory")
        db_size = self._client.dbsize()
        return {
            "keys": db_size,
            "memory": info.get("used_memory_human", "unknown"),
        }
