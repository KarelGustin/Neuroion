"""
Agenda sync from client: replace user's agenda with events from app (WebSocket or REST).
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from neuroion.core.memory.db import db_session
from neuroion.core.memory.repository import AgendaEventRepository

logger = logging.getLogger(__name__)


def _parse_iso_datetime(value: str) -> datetime:
    """Parse ISO date or datetime to naive UTC datetime."""
    value = (value or "").strip()
    if not value:
        raise ValueError("Empty value")
    if len(value) <= 10:
        try:
            return datetime.strptime(value[:10], "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"Invalid date: {value}")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is not None:
            dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt
    except ValueError:
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M"):
        try:
            return datetime.strptime(value[:19], fmt)
        except ValueError:
            continue
    raise ValueError(f"Invalid date/datetime: {value}")


def sync_agenda_for_user(user_id: int, household_id: int, events: List[Dict[str, Any]]) -> int:
    """
    Full replace: delete all agenda events for user, then create from payload.
    events: list of { id?, title, start_at, end_at, all_day?, notes? } (id is optional client id).
    Returns number of events created.
    """
    created = 0
    with db_session() as db:
        AgendaEventRepository.delete_all_for_user(db, household_id, user_id)
        for ev in events:
            title = (ev.get("title") or "").strip() or "Untitled"
            try:
                start_at = _parse_iso_datetime(ev.get("start_at") or "")
                end_at = _parse_iso_datetime(ev.get("end_at") or "")
            except ValueError as e:
                logger.warning("Agenda sync skip invalid event %s: %s", ev.get("title"), e)
                continue
            if start_at >= end_at:
                continue
            all_day = bool(ev.get("all_day", False))
            notes = (ev.get("notes") or "").strip() or None
            AgendaEventRepository.create(
                db=db,
                household_id=household_id,
                user_id=user_id,
                title=title,
                start_at=start_at,
                end_at=end_at,
                all_day=all_day,
                notes=notes,
            )
            created += 1
    logger.info("Agenda sync for user_id=%s: %s events", user_id, created)
    return created


async def handle_agenda_sync(user_id: int, household_id: int, events: List[Dict[str, Any]]) -> None:
    """Async wrapper: run sync_agenda_for_user in executor."""
    import asyncio
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, sync_agenda_for_user, user_id, household_id, events)
