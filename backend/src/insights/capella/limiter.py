"""Async token-bucket rate limiter and retry/backoff policy for the Capella client."""

from __future__ import annotations

import asyncio
import random
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

Clock = Callable[[], float]
Sleeper = Callable[[float], Awaitable[None]]


class TokenBucket:
    """Token bucket: ``rate_per_minute`` sustained, ``burst`` tokens available at once.

    Waiters sleep for the exact time until a token is available; there is no busy-wait.
    The default burst is a fifth of the per-minute rate so that even a cold start never
    exceeds Capella's 100 requests/minute (80/min sustained + 16 burst < 100 in any window).
    """

    def __init__(
        self,
        rate_per_minute: float,
        burst: int | None = None,
        *,
        clock: Clock = time.monotonic,
        sleep: Sleeper = asyncio.sleep,
    ) -> None:
        if rate_per_minute <= 0:
            raise ValueError("rate_per_minute must be positive")
        self._rate_per_sec = rate_per_minute / 60.0
        self._capacity = float(burst if burst is not None else max(1, int(rate_per_minute // 5)))
        self._tokens = self._capacity
        self._clock = clock
        self._sleep = sleep
        self._last = clock()
        self._lock = asyncio.Lock()

    @property
    def available(self) -> float:
        """Tokens currently in the bucket (after refill)."""
        self._refill()
        return self._tokens

    def _refill(self) -> None:
        now = self._clock()
        elapsed = max(0.0, now - self._last)
        self._last = now
        self._tokens = min(self._capacity, self._tokens + elapsed * self._rate_per_sec)

    async def acquire(self) -> None:
        """Take one token, sleeping until one is available."""
        while True:
            async with self._lock:
                self._refill()
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return
                wait = (1.0 - self._tokens) / self._rate_per_sec
            await self._sleep(wait)


def parse_retry_after(value: str | None, *, now: datetime | None = None) -> float | None:
    """Turn a ``Retry-After`` header (seconds or HTTP-date) into seconds to wait."""
    if value is None:
        return None
    text = value.strip()
    if text.isdigit():
        return float(text)
    try:
        when = parsedate_to_datetime(text)
    except (TypeError, ValueError):
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=UTC)
    current = now or datetime.now(UTC)
    return max(0.0, (when - current).total_seconds())


@dataclass
class RetryPolicy:
    """Exponential backoff with jitter; ``Retry-After`` wins when the server sends one."""

    max_attempts: int = 5
    #: 5xx answers from Capella are usually deterministic (e.g. bucket listing on a turned-off
    #: cluster), so they get fewer attempts than 429s, which are worth waiting out.
    max_attempts_5xx: int = 3
    base_delay: float = 0.5
    max_delay: float = 30.0
    jitter: float = 0.25
    rng: Callable[[], float] = field(default=random.random)

    def delay_for(self, attempt: int, retry_after: str | None = None) -> float:
        """Seconds to sleep before ``attempt`` (1-based index of the retry)."""
        hinted = parse_retry_after(retry_after)
        if hinted is not None:
            return min(hinted, self.max_delay) + self.rng() * self.jitter
        backoff = self.base_delay * (2 ** (attempt - 1))
        return min(backoff, self.max_delay) + self.rng() * self.jitter

    def should_retry(self, status: int) -> bool:
        return status == 429 or 500 <= status <= 599

    def attempts_for(self, status: int) -> int:
        """How many attempts in total a response with ``status`` deserves."""
        return self.max_attempts if status == 429 else min(self.max_attempts, self.max_attempts_5xx)
