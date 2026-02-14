"""
Proactive messages: every 60s check agenda for connected users, enqueue reminders (e.g. event in 15 min).
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from neuroion.core.memory.db import db_session
from neuroion.core.memory.repository import AgendaEventRepository, UserRepository
from neuroion.core.websocket.manager import connection_manager

logger = logging.getLogger(__name__)

PROACTIVE_INTERVAL = 60.0  # seconds
REMINDER_WINDOW_MIN = 12   # remind when event starts in 12–18 min
REMINDER_WINDOW_MAX = 18


async def run_proactive_tick() -> None:
    """
    For each connected user: load agenda (next 24h), if an event starts in REMINDER_WINDOW_MIN–REMINDER_WINDOW_MAX
    minutes, enqueue a proactive message and flush to client.
    """
    try:
        user_ids = await connection_manager.get_connected_user_ids()
        if not user_ids:
            return
        now = datetime.now(timezone.utc)
        window_start = now + timedelta(minutes=REMINDER_WINDOW_MIN)
        window_end = now + timedelta(minutes=REMINDER_WINDOW_MAX)
        end_24h = now + timedelta(hours=24)

        def _load_agenda_and_enqueue() -> None:
            with db_session() as db:
                for user_id in user_ids:
                    user = UserRepository.get_by_id(db, user_id)
                    if not user:
                        continue
                    household_id = user.household_id
                    events = AgendaEventRepository.list_for_user(db, household_id, user_id, now, end_24h)
                    for e in events:
                        if e.start_at >= window_start and e.start_at <= window_end:
                            msg = f"Over {REMINDER_WINDOW_MIN} min: {e.title}"
                            ts = now.isoformat()
                            connection_manager.enqueue_proactive(user_id, msg, ts)

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _load_agenda_and_enqueue)

        for user_id in user_ids:
            await connection_manager.flush_pending_proactive(user_id)
    except Exception as e:
        logger.exception("Proactive tick failed: %s", e)


async def run_proactive_loop() -> None:
    """Run proactive tick every PROACTIVE_INTERVAL seconds."""
    while True:
        try:
            await run_proactive_tick()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.exception("Proactive loop: %s", e)
        await asyncio.sleep(PROACTIVE_INTERVAL)


_proactive_task: Optional[asyncio.Task] = None


async def start_proactive_service() -> None:
    """Start the proactive message service (60s loop)."""
    global _proactive_task
    if _proactive_task is not None:
        return
    _proactive_task = asyncio.create_task(run_proactive_loop())
    logger.info("Proactive service started (tick every %ss)", PROACTIVE_INTERVAL)


async def stop_proactive_service() -> None:
    """Stop the proactive service."""
    global _proactive_task
    if _proactive_task is None:
        return
    _proactive_task.cancel()
    try:
        await _proactive_task
    except asyncio.CancelledError:
        pass
    _proactive_task = None
    logger.info("Proactive service stopped")
