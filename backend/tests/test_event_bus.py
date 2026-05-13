"""Unit tests for the in-process EventBus."""

from __future__ import annotations

import asyncio

import pytest

from greenhouse.event_bus import EventBus


@pytest.mark.asyncio
async def test_publish_delivers_to_subscriber() -> None:
    bus = EventBus()
    queue = await bus.subscribe()
    await bus.publish({"type": "reading", "data": {"value": 1}})
    message = await asyncio.wait_for(queue.get(), timeout=1.0)
    assert message == {"type": "reading", "data": {"value": 1}}


@pytest.mark.asyncio
async def test_publish_fans_out_to_all_subscribers() -> None:
    bus = EventBus()
    q1 = await bus.subscribe()
    q2 = await bus.subscribe()
    await bus.publish({"type": "alert"})

    m1 = await asyncio.wait_for(q1.get(), timeout=1.0)
    m2 = await asyncio.wait_for(q2.get(), timeout=1.0)
    assert m1 == {"type": "alert"}
    assert m2 == {"type": "alert"}


@pytest.mark.asyncio
async def test_unsubscribe_stops_delivery() -> None:
    bus = EventBus()
    queue = await bus.subscribe()
    await bus.unsubscribe(queue)
    assert bus.subscriber_count() == 0
    await bus.publish({"type": "ignored"})
    # No delivery: queue stays empty.
    assert queue.empty()


@pytest.mark.asyncio
async def test_subscriber_count_tracks_lifecycle() -> None:
    bus = EventBus()
    assert bus.subscriber_count() == 0
    q1 = await bus.subscribe()
    q2 = await bus.subscribe()
    assert bus.subscriber_count() == 2
    await bus.unsubscribe(q1)
    assert bus.subscriber_count() == 1
    await bus.unsubscribe(q2)
    assert bus.subscriber_count() == 0
