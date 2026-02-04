"""
Admin endpoints for system management.

Provides endpoints for system administration and monitoring.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional

from neuroion.core.memory.db import get_db
from neuroion.core.memory.repository import (
    HouseholdRepository,
    UserRepository,
    AuditLogRepository,
    ContextSnapshotRepository,
)
from neuroion.core.security.permissions import get_current_user, require_role

router = APIRouter(prefix="/admin", tags=["admin"])


class SystemStatusResponse(BaseModel):
    """System status response."""
    households: int
    users: int
    recent_audit_logs: int
    recent_context_snapshots: int


class AuditLogResponse(BaseModel):
    """Audit log entry response."""
    id: int
    action_type: str
    action_name: str
    reasoning: Optional[str]
    status: str
    created_at: str
    confirmed_at: Optional[str]
    executed_at: Optional[str]


@router.get("/status", response_model=SystemStatusResponse)
def get_system_status(
    db: Session = Depends(get_db),
    user: dict = Depends(require_role(["owner", "admin"])),
) -> SystemStatusResponse:
    """
    Get system status and statistics.
    
    Requires owner or admin role.
    """
    households = HouseholdRepository.get_all(db)
    users = UserRepository.get_by_household(db, user["household_id"])
    audit_logs = AuditLogRepository.get_recent(db, user["household_id"], limit=100)
    snapshots = ContextSnapshotRepository.get_recent(db, user["household_id"], limit=100)
    
    return SystemStatusResponse(
        households=len(households),
        users=len(users),
        recent_audit_logs=len(audit_logs),
        recent_context_snapshots=len(snapshots),
    )


@router.get("/audit", response_model=List[AuditLogResponse])
def get_audit_logs(
    limit: int = 100,
    action_type: Optional[str] = None,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role(["owner", "admin"])),
) -> List[AuditLogResponse]:
    """
    Get audit logs.
    
    Requires owner or admin role.
    """
    logs = AuditLogRepository.get_recent(
        db,
        user["household_id"],
        limit=limit,
        action_type=action_type,
    )
    
    return [
        AuditLogResponse(
            id=log.id,
            action_type=log.action_type,
            action_name=log.action_name,
            reasoning=log.reasoning,
            status=log.status,
            created_at=log.created_at.isoformat(),
            confirmed_at=log.confirmed_at.isoformat() if log.confirmed_at else None,
            executed_at=log.executed_at.isoformat() if log.executed_at else None,
        )
        for log in logs
    ]
