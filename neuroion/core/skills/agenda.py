"""
Agenda skill: list, add, update, and delete events in the user's in-app agenda.

Used by the agent when the user asks about their calendar, wants to schedule something,
or change/remove an event. All actions are scoped to the current user (user_id from context).
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session
from zoneinfo import ZoneInfo

from neuroion.core.agent.tool_registry import register_tool
from neuroion.core.memory.repository import AgendaEventRepository

logger = logging.getLogger(__name__)

DEFAULT_TZ = "Europe/Amsterdam"


def _parse_datetime(value: str, tz_name: str = DEFAULT_TZ) -> datetime:
    """Parse ISO date/datetime to naive UTC datetime."""
    value = (value or "").strip()
    if not value:
        raise ValueError("Empty date/datetime")
    tz = ZoneInfo(tz_name)
    # Date only
    if len(value) <= 10:
        try:
            dt = datetime.strptime(value[:10], "%Y-%m-%d")
            return dt.replace(tzinfo=tz).astimezone(timezone.utc).replace(tzinfo=None)
        except ValueError:
            raise ValueError(f"Invalid date: {value}")
    # With time
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=tz).astimezone(timezone.utc).replace(tzinfo=None)
        else:
            dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt
    except ValueError:
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M"):
        try:
            dt = datetime.strptime(value[:19], fmt).replace(tzinfo=tz).astimezone(timezone.utc).replace(tzinfo=None)
            return dt
        except ValueError:
            continue
    raise ValueError(f"Invalid date/datetime: {value}")


def _event_to_dict(e: Any) -> Dict[str, Any]:
    """Turn an AgendaEvent model into a short dict for the LLM."""
    return {
        "id": e.id,
        "title": e.title,
        "start_at": e.start_at.isoformat() if e.start_at else None,
        "end_at": e.end_at.isoformat() if e.end_at else None,
        "all_day": e.all_day,
        "notes": (e.notes or "").strip() or None,
    }


@register_tool(
    name="agenda.list_events",
    description=(
        "List events in the user's agenda between start and end. "
        "Use when the user asks what they have planned, what's on their calendar, or to check availability."
    ),
    parameters={
        "type": "object",
        "properties": {
            "start": {"type": "string", "description": "Start of range (ISO date or datetime, e.g. 2024-02-01 or 2024-02-01T00:00:00)"},
            "end": {"type": "string", "description": "End of range (ISO date or datetime)"},
            "timezone": {"type": "string", "description": "IANA timezone for display (default Europe/Amsterdam)"},
        },
        "required": ["start", "end"],
    },
)
def agenda_list_events(
    db: Session,
    household_id: int,
    user_id: int,
    start: str,
    end: str,
    timezone: Optional[str] = None,
) -> Dict[str, Any]:
    """List agenda events for the current user in the given range."""
    tz_name = timezone or DEFAULT_TZ
    try:
        start_dt = _parse_datetime(start, tz_name)
        end_dt = _parse_datetime(end, tz_name)
    except ValueError as e:
        return {"success": False, "error": str(e)}
    if start_dt >= end_dt:
        return {"success": False, "error": "start must be before end"}
    events = AgendaEventRepository.list_for_user(db, household_id, user_id, start_dt, end_dt)
    return {
        "success": True,
        "events": [_event_to_dict(e) for e in events],
        "count": len(events),
    }


@register_tool(
    name="agenda.add_event",
    description=(
        "Add an event to the user's agenda. "
        "Use when the user wants to schedule something, block time, or add a reminder in their calendar. "
        "Confirm intent before adding if unclear."
    ),
    parameters={
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Event title"},
            "start_at": {"type": "string", "description": "Start time (ISO date or datetime)"},
            "end_at": {"type": "string", "description": "End time (ISO date or datetime)"},
            "all_day": {"type": "boolean", "description": "True if all-day event", "default": False},
            "notes": {"type": "string", "description": "Optional notes"},
        },
        "required": ["title", "start_at", "end_at"],
    },
)
def agenda_add_event(
    db: Session,
    household_id: int,
    user_id: int,
    title: str,
    start_at: str,
    end_at: str,
    all_day: bool = False,
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    """Add an event to the current user's agenda."""
    if not (title or "").strip():
        return {"success": False, "error": "title is required"}
    try:
        start_dt = _parse_datetime(start_at)
        end_dt = _parse_datetime(end_at)
    except ValueError as e:
        return {"success": False, "error": str(e)}
    if start_dt >= end_dt:
        return {"success": False, "error": "start_at must be before end_at"}
    try:
        event = AgendaEventRepository.create(
            db=db,
            household_id=household_id,
            user_id=user_id,
            title=title.strip(),
            start_at=start_dt,
            end_at=end_dt,
            all_day=all_day,
            notes=notes,
        )
        return {"success": True, "event": _event_to_dict(event)}
    except Exception as e:
        logger.exception("agenda.add_event failed: %s", e)
        return {"success": False, "error": str(e)}


@register_tool(
    name="agenda.update_event",
    description=(
        "Update an existing agenda event. "
        "Use when the user wants to change time, title, or details of an event."
    ),
    parameters={
        "type": "object",
        "properties": {
            "event_id": {"type": "integer", "description": "ID of the event to update"},
            "title": {"type": "string", "description": "New title (optional)"},
            "start_at": {"type": "string", "description": "New start (optional)"},
            "end_at": {"type": "string", "description": "New end (optional)"},
            "all_day": {"type": "boolean", "description": "New all_day (optional)"},
            "notes": {"type": "string", "description": "New notes (optional)"},
        },
        "required": ["event_id"],
    },
)
def agenda_update_event(
    db: Session,
    household_id: int,
    user_id: int,
    event_id: int,
    title: Optional[str] = None,
    start_at: Optional[str] = None,
    end_at: Optional[str] = None,
    all_day: Optional[bool] = None,
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    """Update an agenda event belonging to the current user."""
    event = AgendaEventRepository.get_by_id(db, event_id, user_id)
    if not event:
        return {"success": False, "error": "Event not found"}
    kwargs: Dict[str, Any] = {}
    if title is not None:
        kwargs["title"] = title.strip() or "Untitled"
    if start_at is not None:
        try:
            kwargs["start_at"] = _parse_datetime(start_at)
        except ValueError as e:
            return {"success": False, "error": str(e)}
    if end_at is not None:
        try:
            kwargs["end_at"] = _parse_datetime(end_at)
        except ValueError as e:
            return {"success": False, "error": str(e)}
    if all_day is not None:
        kwargs["all_day"] = all_day
    if notes is not None:
        kwargs["notes"] = notes
    if kwargs:
        # Validate start < end if we're touching times
        start_dt = kwargs.get("start_at", event.start_at)
        end_dt = kwargs.get("end_at", event.end_at)
        if start_dt >= end_dt:
            return {"success": False, "error": "start_at must be before end_at"}
        updated = AgendaEventRepository.update(db, event_id, user_id, **kwargs)
        if updated:
            return {"success": True, "event": _event_to_dict(updated)}
    return {"success": True, "event": _event_to_dict(event)}


@register_tool(
    name="agenda.delete_event",
    description=(
        "Remove an event from the user's agenda. "
        "Use when the user wants to cancel or delete a planned event."
    ),
    parameters={
        "type": "object",
        "properties": {
            "event_id": {"type": "integer", "description": "ID of the event to delete"},
        },
        "required": ["event_id"],
    },
)
def agenda_delete_event(
    db: Session,
    household_id: int,
    user_id: int,
    event_id: int,
) -> Dict[str, Any]:
    """Delete an agenda event belonging to the current user."""
    deleted = AgendaEventRepository.delete(db, event_id, user_id)
    if not deleted:
        return {"success": False, "error": "Event not found"}
    return {"success": True, "message": "Event deleted"}
