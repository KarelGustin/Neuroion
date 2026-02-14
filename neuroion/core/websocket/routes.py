"""
WebSocket route: /ws?token=... Accept, auth, register, heartbeat task, message loop.
"""
import asyncio
import json
import logging
from urllib.parse import parse_qs

from fastapi import WebSocket, WebSocketDisconnect

from neuroion.core.memory.db import db_session
from neuroion.core.memory.repository import UserRepository, HouseholdRepository
from neuroion.core.security.tokens import TokenManager
from neuroion.core.websocket.manager import connection_manager, MAX_FRAME_SIZE
from neuroion.core.websocket.handler import run_heartbeat_task, handle_message, HEARTBEAT_TIMEOUT

logger = logging.getLogger(__name__)


def _get_user_from_token(token: str):
    """Verify token and return user dict (user_id, household_id) or None."""
    payload = TokenManager.verify_token(token)
    if not payload:
        return None
    user_id = payload.get("user_id")
    household_id = payload.get("household_id")
    if not user_id or not household_id:
        return None
    with db_session() as db:
        user = UserRepository.get_by_id(db, user_id)
        if not user:
            return None
        household = HouseholdRepository.get_by_id(db, household_id)
        if not household:
            return None
        UserRepository.update_last_seen(db, user_id)
    return {"user_id": user_id, "household_id": household_id}


async def websocket_endpoint(websocket: WebSocket) -> None:
    """Accept WebSocket, validate token from query, register, run heartbeat + message loop."""
    query_string = websocket.scope.get("query_string", b"").decode("utf-8")
    params = parse_qs(query_string)
    tokens = params.get("token", [])
    token = tokens[0] if tokens else ""
    if not token:
        await websocket.close(code=4001, reason="missing_token")
        return
    user = _get_user_from_token(token)
    if not user:
        await websocket.close(code=4001, reason="invalid_token")
        return
    user_id = user["user_id"]
    household_id = user["household_id"]
    await websocket.accept()
    await connection_manager.register(user_id, websocket)
    last_seen: list = [asyncio.get_event_loop().time()]
    closed: list = [False]
    heartbeat_task = asyncio.create_task(
        run_heartbeat_task(websocket, user_id, last_seen, closed)
    )
    try:
        await connection_manager.flush_pending_proactive(user_id)
        while not closed[0]:
            try:
                raw = await asyncio.wait_for(websocket.receive_text(), timeout=HEARTBEAT_TIMEOUT + 5)
            except asyncio.TimeoutError:
                if not closed[0]:
                    logger.info("WebSocket receive timeout for user_id=%s", user_id)
                break
            except WebSocketDisconnect:
                break
            if len(raw) > MAX_FRAME_SIZE:
                await websocket.send_json({"type": "chat_error", "error": "Frame too large"})
                continue
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "chat_error", "error": "Invalid JSON"})
                continue
            err = await handle_message(websocket, user_id, household_id, data, last_seen)
            if err:
                await websocket.send_json({"type": "chat_error", "error": err})
    finally:
        closed[0] = True
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass
        await connection_manager.unregister(user_id, websocket)
