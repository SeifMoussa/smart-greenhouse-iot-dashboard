"""Tiny per-key token-bucket rate limiter.

Intentionally simple and self-contained so it is easy to test and reason
about. For a small lab system this is sufficient; production deployments
would normally use a shared backend (Redis) and a battle-tested library.
"""

from __future__ import annotations

import threading
import time


class TokenBucket:
    """Token-bucket per key (typically the client IP).

    ``rate_per_second`` is both the bucket capacity and the refill rate.
    """

    def __init__(self, rate_per_second: int) -> None:
        if rate_per_second <= 0:
            raise ValueError("rate_per_second must be positive")
        self.rate = float(rate_per_second)
        self._buckets: dict[str, tuple[float, float]] = {}
        self._lock = threading.Lock()

    def check(self, key: str) -> bool:
        """Consume one token for ``key``. Returns True if allowed, False if not."""
        now = time.monotonic()
        with self._lock:
            tokens, last = self._buckets.get(key, (self.rate, now))
            # Refill since last check, capped at capacity.
            tokens = min(self.rate, tokens + (now - last) * self.rate)
            if tokens >= 1.0:
                tokens -= 1.0
                self._buckets[key] = (tokens, now)
                return True
            self._buckets[key] = (tokens, now)
            return False
