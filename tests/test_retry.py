"""Unit tests for the retry decorator."""

from __future__ import annotations

import pytest
import requests

from marketing_mcp.utils.retry import TransientAPIError, with_retry


def test_retry_succeeds_after_transient_failure():
    calls = []

    @with_retry(attempts=3, wait_initial=0.01, wait_max=0.02)
    def flaky():
        calls.append(1)
        if len(calls) < 3:
            raise TransientAPIError("flaky")
        return "ok"

    assert flaky() == "ok"
    assert len(calls) == 3


def test_retry_gives_up_after_attempts():
    @with_retry(attempts=2, wait_initial=0.01, wait_max=0.02)
    def always_fails():
        raise TransientAPIError("nope")

    with pytest.raises(TransientAPIError):
        always_fails()


def test_retry_passes_non_transient_immediately():
    calls = []

    @with_retry(attempts=3, wait_initial=0.01, wait_max=0.02)
    def value_error():
        calls.append(1)
        raise ValueError("don't retry me")

    with pytest.raises(ValueError):
        value_error()
    assert len(calls) == 1  # not retried


def test_retry_on_connection_error():
    calls = []

    @with_retry(attempts=2, wait_initial=0.01, wait_max=0.02)
    def conn_fail():
        calls.append(1)
        if len(calls) == 1:
            raise requests.ConnectionError("network down")
        return "recovered"

    assert conn_fail() == "recovered"
    assert len(calls) == 2
