"""Retry decorator behaviour tests."""

import asyncio
import pytest

from app.utils.retry import async_retry, retry_with_fallback


@pytest.mark.asyncio
async def test_no_retry_on_success():
    call_count = 0

    @async_retry(max_attempts=3)
    async def always_succeeds() -> str:
        nonlocal call_count
        call_count += 1
        return "ok"

    result = await always_succeeds()
    assert result == "ok"
    assert call_count == 1


@pytest.mark.asyncio
async def test_retries_on_failure_then_succeeds():
    call_count = 0

    @async_retry(max_attempts=3, base_delay=0.0)
    async def fails_twice() -> str:
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ValueError("transient")
        return "ok"

    result = await fails_twice()
    assert result == "ok"
    assert call_count == 3


@pytest.mark.asyncio
async def test_raises_after_max_attempts():
    call_count = 0

    @async_retry(max_attempts=2, base_delay=0.0)
    async def always_fails() -> str:
        nonlocal call_count
        call_count += 1
        raise RuntimeError("permanent")

    with pytest.raises(RuntimeError, match="permanent"):
        await always_fails()
    assert call_count == 2


@pytest.mark.asyncio
async def test_fallback_called_on_exhaustion():
    @async_retry(max_attempts=2, base_delay=0.0)
    async def always_fails() -> str:
        raise RuntimeError("always")

    result = await retry_with_fallback(
        fn=always_fails,
        fallback=lambda: "fallback_value",
        max_attempts=2,
        base_delay=0.0,
    )
    assert result == "fallback_value"
