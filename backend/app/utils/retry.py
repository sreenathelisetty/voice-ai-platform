"""
Async retry decorator with full-jitter exponential backoff.

Usage:
    @async_retry(max_attempts=3, base_delay=0.5, exceptions=(MyError,))
    async def flaky_call() -> str: ...

    result = await retry_with_fallback(
        fn=flaky_call,
        fallback=lambda: "default",
        max_attempts=3,
    )
"""

import asyncio
import functools
import random
from collections.abc import Callable, Coroutine
from typing import Any, TypeVar

from app.utils.logging import get_logger

log = get_logger(__name__)

T = TypeVar("T")


def async_retry(
    max_attempts: int = 3,
    base_delay: float = 0.5,
    max_delay: float = 10.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[Callable[..., Coroutine[Any, Any, T]]], Callable[..., Coroutine[Any, Any, T]]]:
    """
    Decorator that retries an async function with full-jitter exponential backoff.

    Args:
        max_attempts: Maximum number of total calls (including first attempt).
        base_delay:   Base delay in seconds for backoff calculation.
        max_delay:    Maximum delay cap in seconds.
        exceptions:   Tuple of exception types that trigger a retry.
    """

    def decorator(
        fn: Callable[..., Coroutine[Any, Any, T]],
    ) -> Callable[..., Coroutine[Any, Any, T]]:
        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exc: Exception | None = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return await fn(*args, **kwargs)
                except exceptions as exc:
                    last_exc = exc
                    if attempt == max_attempts:
                        break
                    # Full-jitter: delay ∈ [0, min(cap, base * 2^attempt)]
                    cap = min(max_delay, base_delay * (2 ** (attempt - 1)))
                    delay = random.uniform(0, cap)
                    log.warning(
                        "retry",
                        fn=fn.__name__,
                        attempt=attempt,
                        max_attempts=max_attempts,
                        delay_s=round(delay, 3),
                        error=str(exc),
                    )
                    await asyncio.sleep(delay)
            raise last_exc  # type: ignore[misc]

        return wrapper

    return decorator


async def retry_with_fallback(
    fn: Callable[..., Coroutine[Any, Any, T]],
    fallback: Callable[[], T] | Callable[[], Coroutine[Any, Any, T]],
    max_attempts: int = 3,
    base_delay: float = 0.5,
    exceptions: tuple[type[Exception], ...] = (Exception,),
    *args: Any,
    **kwargs: Any,
) -> T:
    """
    Try `fn` up to `max_attempts` times, then call `fallback` on exhaustion.
    `fallback` may be sync or async.
    """
    try:
        wrapped = async_retry(
            max_attempts=max_attempts,
            base_delay=base_delay,
            exceptions=exceptions,
        )(fn)
        return await wrapped(*args, **kwargs)
    except exceptions as exc:
        log.error("all_retries_exhausted", fn=fn.__name__, error=str(exc))
        result = fallback()
        if asyncio.iscoroutine(result):
            return await result  # type: ignore[return-value]
        return result  # type: ignore[return-value]
