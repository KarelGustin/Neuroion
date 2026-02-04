"""
Events endpoint for location and health data ingestion.

Receives derived context summaries (never raw health data).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from datetime import datetime

from neuroion.core.memory.db import get_db
from neuroion.core.memory.repository import ContextSnapshotRepository
from neuroion.core.security.permissions import get_current_user

router = APIRouter(prefix="/events", tags=["events"])


class LocationEvent(BaseModel):
    """Location event data."""
    event_type: str  # arriving_home, leaving_home
    timestamp: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


class HealthSummaryEvent(BaseModel):
    """Health summary event data (derived summaries only)."""
    sleep_score: Optional[float] = None
    recovery_level: Optional[str] = None  # high, medium, low
    activity_level: Optional[str] = None  # high, medium, low
    summary: str  # Human-readable summary
    timestamp: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


class EventRequest(BaseModel):
    """Event submission request."""
    event_type: str  # location, health_summary
    location: Optional[LocationEvent] = None
    health_summary: Optional[HealthSummaryEvent] = None


class EventResponse(BaseModel):
    """Event submission response."""
    success: bool
    snapshot_id: int
    message: str


@router.post("", response_model=EventResponse)
def submit_event(
    request: EventRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> EventResponse:
    """
    Submit an event (location or health summary).
    
    Only accepts derived summaries, never raw health data.
    Creates a context snapshot for the agent to use.
    """
    household_id = user["household_id"]
    user_id = user["user_id"]
    
    if request.event_type == "location":
        if not request.location:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="location data required for location events",
            )
        
        # Create location context snapshot
        event_subtype = request.location.event_type
        summary = f"User {event_subtype.replace('_', ' ')}"
        
        snapshot = ContextSnapshotRepository.create(
            db=db,
            household_id=household_id,
            user_id=user_id,
            event_type="location",
            event_subtype=event_subtype,
            summary=summary,
            metadata=request.location.metadata,
            timestamp=request.location.timestamp,
        )
        
        return EventResponse(
            success=True,
            snapshot_id=snapshot.id,
            message=f"Location event recorded: {event_subtype}",
        )
    
    elif request.event_type == "health_summary":
        if not request.health_summary:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="health_summary data required for health_summary events",
            )
        
        # Create health summary context snapshot
        # Only store derived summaries, never raw data
        health = request.health_summary
        
        metadata = {
            "sleep_score": health.sleep_score,
            "recovery_level": health.recovery_level,
            "activity_level": health.activity_level,
        }
        if health.metadata:
            metadata.update(health.metadata)
        
        snapshot = ContextSnapshotRepository.create(
            db=db,
            household_id=household_id,
            user_id=user_id,
            event_type="health_summary",
            event_subtype=None,
            summary=health.summary,
            metadata=metadata,
            timestamp=health.timestamp,
        )
        
        return EventResponse(
            success=True,
            snapshot_id=snapshot.id,
            message="Health summary recorded",
        )
    
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown event_type: {request.event_type}",
        )
