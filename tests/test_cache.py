"""Unit tests for the cache utility."""

from __future__ import annotations

from marketing_mcp.utils.cache import ScopedCache, make_key


def test_make_key_stable_across_dict_order():
    a = make_key("endpoint", {"x": 1, "y": 2})
    b = make_key("endpoint", {"y": 2, "x": 1})
    assert a == b


def test_make_key_changes_with_input():
    a = make_key("endpoint", {"x": 1})
    b = make_key("endpoint", {"x": 2})
    assert a != b


def test_set_and_get():
    cache = ScopedCache("test", ttl_seconds=60)
    cache.set("k", "value")
    assert cache.get("k") == "value"


def test_get_or_compute_caches():
    cache = ScopedCache("test", ttl_seconds=60)
    calls = []

    def factory():
        calls.append(1)
        return "computed"

    assert cache.get_or_compute("k", factory) == "computed"
    assert cache.get_or_compute("k", factory) == "computed"
    assert len(calls) == 1  # only computed once


def test_clear():
    cache = ScopedCache("test", ttl_seconds=60)
    cache.set("k", "v")
    assert len(cache) == 1
    cache.clear()
    assert len(cache) == 0
