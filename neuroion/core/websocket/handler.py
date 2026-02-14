"""
WebSocket message handling: heartbeat (separate task), chat_message -> agent stream, etc.
"""
import asyncio
import json
import logging
import queue
import threading
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

from neuroion.core.websocket.manager import connection_manager


async def _push_agenda_update(user_id: int) -> None:
    """Fetch user's agenda (next 30 days) and send agenda_update to client if connected."""
    def _fetch() -> list:
        from neuroion.core.memory.db import db_session
        from neuroion.core.memory.repository import AgendaEventRepository
        from datetime import timedelta, timezone
        now = datetime.now(timezone.utc)
        end = now + timedelta(days=30)
        with db_session() as db:
            # Get household_id from user - we need it for list_for_user
            from neuroion.core.memory.repository import UserRepository
            user = UserRepository.get_by_id(db, user_id)
            if not user:
                return []
            household_id = user.household_id
            events = AgendaEventRepository.list_for_user(db, household_id, user_id, now, end)
            return [
                {
                    "id": e.id,
                    "title": e.title,
                    "start_at": e.start_at.isoformat() if hasattr(e.start_at, "isoformat") else str(e.start_at),
                    "end_at": e.end_at.isoformat() if hasattr(e.end_at, "isoformat") else str(e.end_at),
                    "all_day": e.all_day,
                    "notes": e.notes,
                }
                for e in events
            ]
    loop = asyncio.get_event_loop()
    events = await loop.run_in_executor(None, _fetch)
    if events:
        await connection_manager.send_to_user(user_id, {"type": "agenda_update", "events": events})

logger = logging.getLogger(__name__)

HEARTBEAT_INTERVAL = 60.0  # seconds
HEARTBEAT_TIMEOUT = 90.0   # seconds without ack -> close


async def run_heartbeat_task(
    websocket: Any,
    user_id: int,
    last_seen: list,
    closed: list,
) -> None:
    """
    Separate function: every HEARTBEAT_INTERVAL send heartbeat; if no activity for
    HEARTBEAT_TIMEOUT, close the connection. Only keepalive/liveness, no business logic.
    closed is a single-element list: closed[0] True means stop.
    """
    last = last_seen[0]
    while not closed[0]:
        await asyncio.sleep(HEARTBEAT_INTERVAL)
        if closed[0]:
            return
        now = datetime.now(timezone.utc).isoformat()
        try:
            await websocket.send_json({"type": "heartbeat", "ts": now})
        except Exception as e:
            logger.debug("Heartbeat send failed for user %s: %s", user_id, e)
            closed[0] = True
            return
        # Wait for ack or any message (last_seen updates on any receive)
        deadline = asyncio.get_event_loop().time() + HEARTBEAT_TIMEOUT
        while asyncio.get_event_loop().time() < deadline and not closed[0]:
            await asyncio.sleep(2.0)
            if last_seen[0] != last:
                last = last_seen[0]
                break
        else:
            if closed[0]:
                return
            # Timeout: no ack
            logger.info("WebSocket heartbeat timeout for user_id=%s", user_id)
            closed[0] = True
            try:
                await websocket.close(code=4001, reason="heartbeat_timeout")
            except Exception:
                pass
            return


def _enrich_ev(ev: Dict[str, Any]) -> Dict[str, Any]:
    """Add ts to event."""
    e = dict(ev)
    e.setdefault("ts", datetime.now(timezone.utc).isoformat())
    return e


async def handle_chat_message(
    user_id: int,
    household_id: int,
    message: str,
    send_cb: Callable[[Dict[str, Any]], Any],
) -> None:
    """Run agent in thread; stream chat_token/chat_done/chat_error via send_cb."""
    from neuroion.core.api.chat import get_agent
    from neuroion.core.memory.db import db_session
    from neuroion.core.memory.repository import ChatMessageRepository
    from neuroion.core.agent.agent import compact_and_save_session
    from datetime import timedelta

    SESSION_INACTIVITY_MINUTES = 15
    agent = get_agent()
    sync_queue: queue.Queue = queue.Queue()

    def run_agent() -> None:
        with db_session() as thread_db:
            try:
                recent = ChatMessageRepository.get_recent(thread_db, household_id, limit=1, user_id=user_id)
                last_msg = recent[0] if recent else None
                new_user_message = ChatMessageRepository.create(
                    db=thread_db,
                    household_id=household_id,
                    user_id=user_id,
                    role="user",
                    content=message,
                )
                if last_msg and new_user_message.created_at and last_msg.created_at:
                    gap = new_user_message.created_at - last_msg.created_at
                    if gap >= timedelta(minutes=SESSION_INACTIVITY_MINUTES):
                        previous_session = ChatMessageRepository.get_previous_session_messages(
                            thread_db, household_id, user_id, new_user_message.created_at, SESSION_INACTIVITY_MINUTES
                        )
                        if previous_session:
                            try:
                                compact_and_save_session(thread_db, household_id, user_id, previous_session)
                            except Exception:
                                pass
                conversation_history = ChatMessageRepository.get_messages_for_current_session(
                    thread_db, household_id, user_id, before_or_at=None, inactivity_minutes=SESSION_INACTIVITY_MINUTES
                )
                result = agent.process_message(
                    db=thread_db,
                    household_id=household_id,
                    user_id=user_id,
                    message=message,
                    conversation_history=conversation_history,
                    force_task_mode=False,
                    progress_callback=lambda ev: sync_queue.put(ev),
                )
                sync_queue.put(_enrich_ev({
                    "type": "done",
                    "message": result.get("message", ""),
                    "actions": result.get("actions", []),
                }))
            except Exception as e:
                logger.exception("Agent process_message failed: %s", e)
                sync_queue.put(_enrich_ev({"type": "done", "message": "", "actions": [], "error": str(e)}))

    loop = asyncio.get_event_loop()
    thread = threading.Thread(target=run_agent)
    thread.start()

    # First status
    await send_cb(_enrich_ev({"type": "status", "text": "Neuroion denkt na…"}))
    full_message: list = []

    while True:
        try:
            ev = await loop.run_in_executor(None, lambda: sync_queue.get(timeout=0.5))
        except queue.Empty:
            await asyncio.sleep(0.05)
            continue
        kind = ev.get("type")
        if kind == "done":
            if not ev.get("error"):
                with db_session() as save_db:
                    ChatMessageRepository.create(
                        db=save_db,
                        household_id=household_id,
                        user_id=user_id,
                        role="assistant",
                        content=ev.get("message", ""),
                        metadata={"actions": ev.get("actions", [])} if ev.get("actions") else None,
                    )
            await send_cb(_enrich_ev({"type": "chat_done", "message": ev.get("message", ""), "actions": ev.get("actions", []), "error": ev.get("error")}))
            # Push updated agenda to client so app can merge (agent may have modified agenda via tools)
            await _push_agenda_update(user_id)
            return
        if kind == "token":
            text = ev.get("text") or ""
            full_message.append(text)
            await send_cb({"type": "chat_token", "text": text})
        elif kind == "status":
            await send_cb({"type": "status", "text": ev.get("text", "")})
        elif kind in ("step_output", "tool_start", "tool_done"):
            await send_cb({"type": kind, **{k: v for k, v in ev.items() if k != "type"}})
        # ignore other events or forward if needed


async def handle_message(
    websocket: Any,
    user_id: int,
    household_id: int,
    data: Dict[str, Any],
    last_seen: list,
) -> Optional[str]:
    """
    Dispatch incoming message. Update last_seen on any received frame.
    Returns error string to send back if any (e.g. invalid type).
    """
    last_seen[0] = asyncio.get_event_loop().time()
    msg_type = data.get("type") or ""
    if msg_type == "heartbeat_ack":
        return None
    if msg_type == "chat_message":
        message = (data.get("message") or "").strip()
        if not message:
            return None
        async def send_cb(obj: Dict[str, Any]) -> None:
            try:
                await websocket.send_json(obj)
            except Exception as e:
                logger.warning("Send chat frame failed: %s", e)
        await handle_chat_message(user_id, household_id, message, send_cb)
        return None
    if msg_type == "agenda_sync":
        from neuroion.core.websocket.agenda_sync import handle_agenda_sync
        await handle_agenda_sync(user_id, household_id, data.get("events") or [])
        return None
    if msg_type == "cancel_generation":
        # MVP: no-op; could set a flag for running agent
        return None
    return None
