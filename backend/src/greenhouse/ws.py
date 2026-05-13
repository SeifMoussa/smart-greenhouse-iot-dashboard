"""WebSocket hub — tracks active connections and enforces the max limit."""

from __future__ import annotations

import asyncio


class WebSocketHub:
    """Counts active WebSocket connections and enforces ``max_connections``.

    The hub does not own the WebSocket objects themselves; the route owns
    those. The hub exists so the max-connections rule has one place to live.
    """

    def __init__(self, max_connections: int = 100) -> None:
        if max_connections <= 0:
            raise ValueError("max_connections must be positive")
        self.max_connections = max_connections
        self._count = 0
        self._lock = asyncio.Lock()

    async def try_reserve(self) -> bool:
        """Reserve a connection slot. Returns False if the limit is reached."""
        async with self._lock:
            if self._count >= self.max_connections:
                return False
            self._count += 1
            return True

    async def release(self) -> None:
        """Release a previously reserved connection slot."""
        async with self._lock:
            if self._count > 0:
                self._count -= 1

    def count(self) -> int:
        """Return the current count of reserved slots (unlocked snapshot)."""
        return self._count
