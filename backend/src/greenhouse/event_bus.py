"""In-process async pub/sub event bus.

Each subscriber owns an ``asyncio.Queue``. The bus fans out every published
message to every subscriber queue. If a subscriber's queue is full the oldest
message is dropped to make room for the new one — this keeps slow consumers
from blocking publishers.
"""

from __future__ import annotations

import asyncio
import contextlib
from typing import Any

QUEUE_MAXSIZE = 1000


class EventBus:
    """Lightweight, single-process publish/subscribe bus."""

    def __init__(self) -> None:
        self._subscribers: list[asyncio.Queue[dict[str, Any]]] = []
        self._lock = asyncio.Lock()

    async def subscribe(self) -> asyncio.Queue[dict[str, Any]]:
        """Register a new subscriber and return its queue."""
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=QUEUE_MAXSIZE)
        async with self._lock:
            self._subscribers.append(queue)
        return queue

    async def unsubscribe(self, queue: asyncio.Queue[dict[str, Any]]) -> None:
        """Remove a previously registered subscriber."""
        async with self._lock:
            with contextlib.suppress(ValueError):
                self._subscribers.remove(queue)

    async def publish(self, message: dict[str, Any]) -> None:
        """Broadcast a message to every subscriber. Drops oldest if full."""
        async with self._lock:
            subscribers = list(self._subscribers)
        for queue in subscribers:
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                with contextlib.suppress(asyncio.QueueEmpty, asyncio.QueueFull):
                    queue.get_nowait()
                    queue.put_nowait(message)

    def subscriber_count(self) -> int:
        """Return the current number of active subscribers."""
        return len(self._subscribers)
