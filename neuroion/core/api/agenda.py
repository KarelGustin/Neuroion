"""
Agenda API: list, create, update, and delete current user's calendar events.

Used by the iOS app and agent for the in-app agenda.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime

from neuroion.core.memory.db import get_db
from neuroion.core.memory.repository import AgendaEventRepository
from neuroion.core.security.permissions import get_current_user

router = APIRouter(prefix="/agenda", tags=["agenda"])


def _parse_iso_datetime(value: str) -> datetime:
    """Parse ISO date or datetime string to naive datetime (stored as UTC)."""
    value = (value or "").strip()
    if not value:
        raise ValueError("Empty value")
    # Date only (YYYY-MM-DD) -> start of day
    if len(value) <= 10:
        try:
            return datetime.strptime(value[:10], "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"Invalid date: {value}")
    # Datetime: try fromisoformat (handles 2024-01-15T14:00:00, 2024-01-15T14:00:00Z, +00:00, etc.)
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is not None:
            dt = dt.astimezone(__import__("datetime").timezone.utc).replace(tzinfo=None)
        return dt
    except ValueError:
        pass
    # Fallback: without timezone
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M"):
        try:
            return datetime.strptime(value[:19], fmt)
        except ValueError:
            continue
    raise ValueError(f"Invalid date/datetime: {value}")


class AgendaEventItem(BaseModel):
    """Single agenda event for API response."""
    id: int
    title: str
    start_at: datetime
    end_at: datetime
    all_day: bool
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AgendaListResponse(BaseModel):
    """List of agenda events."""
    events: List[AgendaEventItem]


class CreateAgendaEventRequest(BaseModel):
    """Request body for creating an event."""
    title: str
    start_at: str  # ISO date or datetime
    end_at: str
    all_day: bool = False
    notes: Optional[str] = None

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        if not (v or "").strip():
            raise ValueError("title is required")
        return v.strip()


class UpdateAgendaEventRequest(BaseModel):
    """Request body for updating an event (partial)."""
    title: Optional[str] = None
    start_at: Optional[str] = None
    end_at: Optional[str] = None
    all_day: Optional[bool] = None
    notes: Optional[str] = None


class AgendaSyncEventItem(BaseModel):
    """Single event for bulk sync (id optional, client-side)."""
    id: Optional[int] = None
    title: str
    start_at: str
    end_at: str
    all_day: bool = False
    notes: Optional[str] = None


class AgendaSyncRequest(BaseModel):
    """Request body for full agenda sync from app."""
    events: List[AgendaSyncEventItem]


class AgendaSyncResponse(BaseModel):
    """Response after agenda sync."""
    success: bool
    created: int


@router.post("/sync", response_model=AgendaSyncResponse)
def agenda_sync(
    request: AgendaSyncRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> AgendaSyncResponse:
    """
    Full replace: replace current user's agenda with the given events.
    Used by the app when syncing local agenda to the backend (e.g. when WebSocket is not connected).
    """
    from neuroion.core.websocket.agenda_sync import sync_agenda_for_user
    events_dict = [e.model_dump() for e in request.events]
    created = sync_agenda_for_user(
        user_id=user["user_id"],
        household_id=user["household_id"],
        events=events_dict,
    )
    return AgendaSyncResponse(success=True, created=created)


@router.get("", response_model=AgendaListResponse)
def list_agenda_events(
    start: str,
    end: str,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> AgendaListResponse:
    """
    List current user's agenda events in the given date range.
    Query params: start, end (ISO date or datetime).
    """
    try:
        start_dt = _parse_iso_datetime(start)
        end_dt = _parse_iso_datetime(end)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    if start_dt >= end_dt:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="start must be before end")
    events = AgendaEventRepository.list_for_user(
        db,
        household_id=user["household_id"],
        user_id=user["user_id"],
        start_dt=start_dt,
        end_dt=end_dt,
    )
    return AgendaListResponse(
        events=[
            AgendaEventItem(
                id=e.id,
                title=e.title,
                start_at=e.start_at,
                end_at=e.end_at,
                all_day=e.all_day,
                notes=e.notes,
                created_at=e.created_at,
                updated_at=e.updated_at,
            )
            for e in events
        ]
    )


@router.get("/{event_id}", response_model=AgendaEventItem)
def get_agenda_event(
    event_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> AgendaEventItem:
    """Get a single agenda event by id (404 if not found or not owner)."""
    event = AgendaEventRepository.get_by_id(db, event_id, user["user_id"])
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return AgendaEventItem(
        id=event.id,
        title=event.title,
        start_at=event.start_at,
        end_at=event.end_at,
        all_day=event.all_day,
        notes=event.notes,
        created_at=event.created_at,
        updated_at=event.updated_at,
    )


@router.post("", response_model=AgendaEventItem, status_code=status.HTTP_201_CREATED)
def create_agenda_event(
    request: CreateAgendaEventRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> AgendaEventItem:
    """Create a new agenda event. Validates start_at < end_at."""
    try:
        start_dt = _parse_iso_datetime(request.start_at)
        end_dt = _parse_iso_datetime(request.end_at)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    if start_dt >= end_dt:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="start_at must be before end_at")
    event = AgendaEventRepository.create(
        db=db,
        household_id=user["household_id"],
        user_id=user["user_id"],
        title=request.title,
        start_at=start_dt,
        end_at=end_dt,
        all_day=request.all_day,
        notes=request.notes,
    )
    return AgendaEventItem(
        id=event.id,
        title=event.title,
        start_at=event.start_at,
        end_at=event.end_at,
        all_day=event.all_day,
        notes=event.notes,
        created_at=event.created_at,
        updated_at=event.updated_at,
    )


@router.patch("/{event_id}", response_model=AgendaEventItem)
def update_agenda_event(
    event_id: int,
    request: UpdateAgendaEventRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> AgendaEventItem:
    """Update an agenda event (partial). Validates start_at < end_at if either is provided."""
    kwargs = request.model_dump(exclude_unset=True)
    if "start_at" in kwargs or "end_at" in kwargs:
        event = AgendaEventRepository.get_by_id(db, event_id, user["user_id"])
        if not event:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
        try:
            start_dt = _parse_iso_datetime(kwargs.get("start_at") or event.start_at.isoformat())
            end_dt = _parse_iso_datetime(kwargs.get("end_at") or event.end_at.isoformat())
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        if start_dt >= end_dt:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="start_at must be before end_at")
        if "start_at" in kwargs:
            kwargs["start_at"] = start_dt
        if "end_at" in kwargs:
            kwargs["end_at"] = end_dt
    if "title" in kwargs and kwargs["title"] is not None and not (kwargs["title"] or "").strip():
        kwargs["title"] = "Untitled"
    updated = AgendaEventRepository.update(db, event_id, user["user_id"], **kwargs)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return AgendaEventItem(
        id=updated.id,
        title=updated.title,
        start_at=updated.start_at,
        end_at=updated.end_at,
        all_day=updated.all_day,
        notes=updated.notes,
        created_at=updated.created_at,
        updated_at=updated.updated_at,
    )


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_agenda_event(
    event_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> None:
    """Delete an agenda event (204 if deleted, 404 if not found or not owner)."""
    deleted = AgendaEventRepository.delete(db, event_id, user["user_id"])
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
