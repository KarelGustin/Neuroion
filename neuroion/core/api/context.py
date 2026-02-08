"""
Context API: list, add, and delete current user's context snapshots.

Used by dashboard-ui Context tab for personal context management.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, List, Any, Dict
from datetime import datetime

from neuroion.core.memory.db import get_db
from neuroion.core.memory.repository import ContextSnapshotRepository
from neuroion.core.security.permissions import get_current_user

router = APIRouter(prefix="/context", tags=["context"])


class ContextSnapshotItem(BaseModel):
    """Single context snapshot for list response."""
    id: int
    event_type: str
    event_subtype: Optional[str] = None
    summary: str
    context_metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime

    class Config:
        from_attributes = True


class ContextListResponse(BaseModel):
    """List of context snapshots."""
    snapshots: List[ContextSnapshotItem]


class AddContextRequest(BaseModel):
    """Add a note/context (optional)."""
    summary: str


class AddContextResponse(BaseModel):
    """Response after adding context."""
    success: bool
    snapshot_id: int
    message: str


@router.get("", response_model=ContextListResponse)
def list_my_context(
    limit: int = 50,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> ContextListResponse:
    """
    List current user's context snapshots (most recent first).
    """
    snapshots = ContextSnapshotRepository.get_recent(
        db,
        household_id=user["household_id"],
        user_id=user["user_id"],
        limit=limit,
    )
    items = []
    for s in snapshots:
        meta = s.context_metadata
        if isinstance(meta, str):
            import json
            try:
                meta = json.loads(meta) if meta else None
            except Exception:
                meta = None
        items.append(
            ContextSnapshotItem(
                id=s.id,
                event_type=s.event_type,
                event_subtype=s.event_subtype,
                summary=s.summary,
                context_metadata=meta,
                timestamp=s.timestamp,
            )
        )
    return ContextListResponse(snapshots=items)


@router.delete("/{snapshot_id}")
def delete_my_context(
    snapshot_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    Delete a context snapshot. Only snapshots belonging to the current user can be deleted.
    """
    deleted = ContextSnapshotRepository.delete(db, snapshot_id, user["user_id"])
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Context snapshot not found or access denied",
        )
    return {"success": True, "message": "Deleted"}


@router.post("", response_model=AddContextResponse)
def add_context_note(
    request: AddContextRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> AddContextResponse:
    """
    Add a note as context for the current user (e.g. "Working from home today").
    """
    snapshot = ContextSnapshotRepository.create(
        db=db,
        household_id=user["household_id"],
        user_id=user["user_id"],
        event_type="note",
        summary=request.summary.strip() or "Note",
        context_metadata=None,
    )
    return AddContextResponse(
        success=True,
        snapshot_id=snapshot.id,
        message="Context added",
    )
