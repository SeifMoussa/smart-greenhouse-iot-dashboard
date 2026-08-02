"""WebSocket endpoint that streams ``reading``, ``alert``, and ``actuator`` events."""

from __future__ import annotations

import asyncio
import logging

import jwt
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from greenhouse import auth as auth_module

log = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    """Accept a WebSocket, subscribe to events, and forward each event.

    Browsers can't attach custom headers to a WebSocket handshake, so the
    JWT access token is passed as a query parameter instead of a bearer
    header. It's still verified the same way as everywhere else in the API.
    """
    settings = ws.app.state.settings
    token = ws.query_params.get("token", "")
    try:
        auth_module.decode_access_token(
            token, secret_key=settings.jwt_secret_key, algorithm=settings.jwt_algorithm
        )
    except jwt.PyJWTError:
        await ws.close(code=1008)  # policy violation
        return

    hub = ws.app.state.ws_hub
    bus = ws.app.state.event_bus

    if not await hub.try_reserve():
        # Reject before accepting the handshake.
        await ws.close(code=1013)
        return

    await ws.accept()
    queue = await bus.subscribe()

    async def send_loop() -> None:
        try:
            while True:
                message = await queue.get()
                await ws.send_json(message)
        except WebSocketDisconnect:
            return
        except Exception as exc:  # noqa: BLE001
            log.warning("ws send loop ended: %s", exc)

    async def recv_loop() -> None:
        # We don't expect any payload from the client; consuming reads is
        # the simplest way to detect disconnects promptly.
        try:
            while True:
                await ws.receive_text()
        except WebSocketDisconnect:
            return
        except Exception:  # noqa: BLE001
            return

    sender = asyncio.create_task(send_loop())
    receiver = asyncio.create_task(recv_loop())
    try:
        _done, pending = await asyncio.wait([sender, receiver], return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()
    finally:
        await bus.unsubscribe(queue)
        await hub.release()
