"""
test_cache.py - Integration tests for the CacheManager.

These tests connect to a REAL Redis instance.
They are SKIPPED automatically when the REDIS_URL environment
variable is not set, so unit-only test runs are not affected.

In GitHub Actions, the Redis service container provides
the Redis server. Locally, you can use docker-compose.
"""

import os
import time
import pytest
from app.cache import CacheManager


# Skip the entire module if REDIS_URL is not configured
REDIS_URL = os.environ.get("REDIS_URL")
pytestmark = pytest.mark.skipif(
    REDIS_URL is None,
    reason="REDIS_URL environment variable not set -- skipping cache tests",
)


@pytest.fixture()
def cache():
    """Create a CacheManager, connect, flush, and clean up after each test."""
    manager = CacheManager()
    manager.connect(REDIS_URL)
    manager.clear()
    yield manager
    manager.clear()
    manager.disconnect()


class TestCacheConnection:
    """Tests for connecting to Redis."""

    def test_connection_is_alive(self, cache):
        """The connection should be alive after connect()."""
        assert cache.is_connected() is True


class TestCacheOperations:
    """Tests for basic set/get/delete cache operations."""

    def test_set_and_get_string(self, cache):
        """Setting a string value and getting it back should work."""
        cache.set("greeting", "hello")
        assert cache.get("greeting") == "hello"

    def test_set_and_get_dict(self, cache):
        """Setting a dict value should serialize/deserialize via JSON."""
        data = {"name": "Widget", "price": 9.99}
        cache.set("product:1", data)
        result = cache.get("product:1")
        assert result == data

    def test_set_and_get_list(self, cache):
        """Setting a list value should serialize/deserialize via JSON."""
        data = [1, 2, 3, "four"]
        cache.set("numbers", data)
        assert cache.get("numbers") == data

    def test_get_nonexistent_returns_none(self, cache):
        """Getting a key that doesn't exist should return None."""
        assert cache.get("nonexistent") is None

    def test_delete_key(self, cache):
        """Deleting a key should remove it from the cache."""
        cache.set("key", "value")
        assert cache.delete("key") is True
        assert cache.get("key") is None

    def test_delete_nonexistent_returns_false(self, cache):
        """Deleting a key that doesn't exist should return False."""
        assert cache.delete("nonexistent") is False

    def test_clear_removes_all_keys(self, cache):
        """Clearing the cache should remove all keys."""
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        cache.clear()
        assert cache.get("a") is None
        assert cache.get("b") is None
        assert cache.get("c") is None


class TestCacheTTL:
    """Tests for TTL (time-to-live) expiration."""

    def test_key_expires_after_ttl(self, cache):
        """A key should disappear after its TTL expires."""
        cache.set("temp", "data", ttl=1)  # 1-second TTL
        assert cache.get("temp") == "data"
        time.sleep(2)  # Wait for expiration
        assert cache.get("temp") is None


class TestCacheStats:
    """Tests for cache statistics."""

    def test_get_stats_returns_dict(self, cache):
        """get_stats() should return a dict with keys and memory info."""
        cache.set("x", 1)
        stats = cache.get_stats()
        assert "keys" in stats
        assert "memory" in stats
        assert stats["keys"] >= 1
