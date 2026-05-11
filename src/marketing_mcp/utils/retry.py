"""Retry policy with exponential backoff for transient API errors."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

import requests
from tenacity import (
    RetryError,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from marketing_mcp.utils.logging import get_logger

logger = get_logger("retry")

T = TypeVar("T")


class TransientAPIError(Exception):
    """An error that should be retried (network blip, 5xx, rate limit)."""


# Retryable HTTP statuses: request timeout, rate limit, 5xx.
RETRYABLE_STATUS_CODES = frozenset({408, 429, 500, 502, 503, 504})


def is_transient_error(exc: BaseException) -> bool:
    """Return True if ``exc`` is worth retrying."""
    if isinstance(exc, TransientAPIError):
        return True
    if isinstance(exc, (requests.ConnectionError, requests.Timeout)):
        return True
    if isinstance(exc, requests.HTTPError):
        resp = exc.response
        if resp is None:
            return True  # no response at all = treat as transient
        return resp.status_code in RETRYABLE_STATUS_CODES
    return False


def with_retry(
    attempts: int = 3,
    wait_initial: float = 1.0,
    wait_max: float = 8.0,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator: retry the wrapped callable on transient errors only.

    4xx errors (other than 408/429) propagate immediately — they indicate the
    request itself is wrong and retrying won't help.
    """
    def decorator(fn: Callable[..., T]) -> Callable[..., T]:
        wrapped = retry(
            stop=stop_after_attempt(attempts),
            wait=wait_exponential(multiplier=wait_initial, max=wait_max),
            retry=retry_if_exception(is_transient_error),
            reraise=True,
            before_sleep=lambda rs: logger.warning(
                "Retry %d/%d for %s after %s: %s",
                rs.attempt_number,
                attempts,
                fn.__name__,
                rs.next_action.sleep if rs.next_action else "?",
                rs.outcome.exception() if rs.outcome else "?",
            ),
        )(fn)
        return wrapped

    return decorator


__all__ = ["RETRYABLE_STATUS_CODES", "RetryError", "TransientAPIError", "is_transient_error", "with_retry"]
