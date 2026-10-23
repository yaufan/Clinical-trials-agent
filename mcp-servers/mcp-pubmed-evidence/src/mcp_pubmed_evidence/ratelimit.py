"""Minimal async token bucket honouring NCBI's 3 req/s (no key) / 10 req/s (key) policy."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable


class TokenBucket:
    """Async token bucket.

    ``rate`` tokens are added per second up to ``capacity``. :meth:`acquire` waits until a
    token is available. ``clock`` and ``sleep`` are injectable so tests can run without
    real waiting (the fake ``sleep`` must advance the fake ``clock``).
    """

    def __init__(
        self,
        rate: float,
        capacity: int | None = None,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        if rate <= 0:
            raise ValueError("rate must be positive")
        self.rate = float(rate)
        self.capacity = float(capacity if capacity is not None else max(1, int(rate)))
        self._tokens = self.capacity
        self._clock = clock
        self._sleep = sleep
        self._last = clock()
        self._lock = asyncio.Lock()

    def _refill(self) -> None:
        now = self._clock()
        elapsed = max(0.0, now - self._last)
        self._last = now
        self._tokens = min(self.capacity, self._tokens + elapsed * self.rate)

    async def acquire(self) -> float:
        """Take one token, sleeping if necessary. Returns the seconds spent waiting."""
        async with self._lock:
            waited = 0.0
            self._refill()
            while self._tokens < 1.0:
                need = (1.0 - self._tokens) / self.rate
                await self._sleep(need)
                waited += need
                self._refill()
            self._tokens -= 1.0
            return waited

    @property
    def tokens(self) -> float:
        return self._tokens
