"""TTL-based response cache for expensive API calls.

Used for Ahrefs (paid credits) and Google Analytics Admin API (rarely-changing
metadata). Each integration creates its own ``TTLCache`` instance with a sensible
TTL — short for live metrics, long for metadata.
"""

from __future__ import annotations

import hashlib
import json
import threading
from collections.abc import Callable
from typing import Any, TypeVar

from cachetools import TTLCache

from marketing_mcp.utils.logging import get_logger

logger = get_logger("cache")

T = TypeVar("T")


def make_key(*parts: Any) -> str:
    """Build a stable cache key from positional parts.

    Dicts and lists are JSON-serialized with sorted keys so equivalent
    payloads hash to the same key.
    """
    blob = json.dumps(parts, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


class ScopedCache:
    """Thread-safe wrapper around ``cachetools.TTLCache`` with a friendly API."""

    def __init__(self, name: str, ttl_seconds: int, maxsize: int = 256) -> None:
        self.name = name
        self.ttl = ttl_seconds
        self._cache: TTLCache[str, Any] = TTLCache(maxsize=maxsize, ttl=ttl_seconds)
        self._lock = threading.RLock()

    def get(self, key: str) -> Any | None:
        with self._lock:
            value = self._cache.get(key)
        if value is not None:
            logger.debug("cache hit [%s] key=%s", self.name, key[:10])
        return value

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._cache[key] = value

    def get_or_compute(self, key: str, factory: Callable[[], T]) -> T:
        with self._lock:
            cached = self._cache.get(key)
        if cached is not None:
            logger.debug("cache hit [%s] key=%s", self.name, key[:10])
            return cached  # type: ignore[no-any-return]
        value = factory()
        with self._lock:
            self._cache[key] = value
        return value

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
        logger.info("Cleared cache [%s]", self.name)

    def __len__(self) -> int:
        with self._lock:
            return len(self._cache)


# Pre-configured caches per integration.
# Tune TTLs based on how often the data changes.
ANALYTICS_METADATA_CACHE = ScopedCache("analytics_metadata", ttl_seconds=600)   # 10 min
GTM_METADATA_CACHE = ScopedCache("gtm_metadata", ttl_seconds=600)               # 10 min
ADS_QUERY_CACHE = ScopedCache("ads_query", ttl_seconds=300)                     # 5 min
AHREFS_CACHE = ScopedCache("ahrefs", ttl_seconds=3600)                          # 1 hr (paid credits)


__all__ = [
    "ADS_QUERY_CACHE",
    "AHREFS_CACHE",
    "ANALYTICS_METADATA_CACHE",
    "GTM_METADATA_CACHE",
    "ScopedCache",
    "make_key",
]
