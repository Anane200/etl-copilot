"""Retry decorator with exponential backoff.

Wraps a callable so transient failures (e.g. a database blip) are retried a
bounded number of times with growing delays, instead of failing the whole
pipeline on the first error. ``sleep`` is injectable so tests run instantly.
"""
from __future__ import annotations

import functools
import logging
import time
from collections.abc import Callable

logger = logging.getLogger(__name__)


def with_retry(
    *,
    max_attempts: int = 3,
    base_delay: float = 0.5,
    backoff: float = 2.0,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
    sleep: Callable[[float], None] = time.sleep,
):
    """Decorator: retry the wrapped function up to ``max_attempts`` times.

    Delay before attempt N (1-indexed) is ``base_delay * backoff**(N-1)``.
    Re-raises the last exception once attempts are exhausted.
    """
    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")

    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts:
                        logger.error(
                            "%s failed after %d attempt(s): %s",
                            func.__name__, attempt, e,
                        )
                        raise
                    delay = base_delay * (backoff ** (attempt - 1))
                    logger.warning(
                        "%s attempt %d/%d failed: %s; retrying in %.2fs",
                        func.__name__, attempt, max_attempts, e, delay,
                    )
                    sleep(delay)

        return wrapper

    return decorator
