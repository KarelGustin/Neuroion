"""
Member management endpoints.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)

from neuroion.core.memory.db import get_db
from neuroion.core.memory.repository import (
    HouseholdRepository,
    UserRepository,
)
from neuroion.core.security.permissions import get_current_user
from neuroion.core.security.passcode import verify_passcode, is_valid_passcode_format

router = APIRouter(prefix="/api", tags=["members"])


# Request/Response Models

class MemberResponse(BaseModel):
    """Member information response."""
    id: int
    name: str
    role: str
    language: Optional[str] = None
    timezone: Optional[str] = None
    created_at: str
    last_seen_at: Optional[str] = None


class MembersListResponse(BaseModel):
    """List of members response."""
    members: List[MemberResponse]


class MeResponse(BaseModel):
    """Current user profile (for user dashboard)."""
    id: int
    name: str
    role: str
    language: Optional[str] = None
    timezone: Optional[str] = None
    household_id: int
    created_at: str
    last_seen_at: Optional[str] = None


class MemberCreateRequest(BaseModel):
    """Request to create a member."""
    name: str
    language: Optional[str] = None
    timezone: Optional[str] = None
    style_prefs: Optional[Dict[str, Any]] = None
    preferences: Optional[Dict[str, Any]] = None
    consent: Optional[Dict[str, Any]] = None


class MemberCreateResponse(BaseModel):
    """Response after creating member."""
    success: bool
    member_id: int
    message: str


class MemberDeleteRequest(BaseModel):
    """Request to delete a member (requires confirmation passcode)."""
    confirmation_code: str  # passcode of the member being deleted (self) or owner (when owner deletes)


class MemberDeleteResponse(BaseModel):
    """Response after deleting member."""
    success: bool
    message: str


# Endpoints

@router.get("/me", response_model=MeResponse)
def get_me(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> MeResponse:
    """
    Get current authenticated user profile (for user dashboard).
    """
    member = UserRepository.get_by_id(db, user["user_id"])
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return MeResponse(
        id=member.id,
        name=member.name or "",
        role=member.role or "member",
        language=member.language,
        timezone=member.timezone,
        household_id=member.household_id,
        created_at=member.created_at.isoformat(),
        last_seen_at=member.last_seen_at.isoformat() if member.last_seen_at else None,
    )


@router.get("/members", response_model=MembersListResponse)
def get_members(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> MembersListResponse:
    """
    Get all members in the household.
    
    Returns list of members (all authenticated users can see household members).
    """
    try:
        members = UserRepository.get_by_household(db, user["household_id"])
        
        member_responses = [
            MemberResponse(
                id=member.id,
                name=member.name,
                role=member.role,
                language=member.language,
                timezone=member.timezone,
                created_at=member.created_at.isoformat(),
                last_seen_at=member.last_seen_at.isoformat() if member.last_seen_at else None,
            )
            for member in members
        ]
        
        return MembersListResponse(members=member_responses)
    except Exception as e:
        logger.error(f"Error getting members: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get members: {str(e)}",
        )


@router.post("/members", response_model=MemberCreateResponse)
def create_member(
    request: MemberCreateRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> MemberCreateResponse:
    """
    Single-user mode: creating members is disabled. Returns 410 Gone.
    """
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="Single-user mode: creating members is disabled",
    )


@router.post("/members/{member_id}/delete", response_model=MemberDeleteResponse)
def delete_member(
    member_id: int,
    request: MemberDeleteRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> MemberDeleteResponse:
    """
    Single-user mode: only self-delete is allowed. Deleting other members returns 410 Gone.
    """
    if user["user_id"] != member_id:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Single-user mode: only self-delete is allowed",
        )
    if not is_valid_passcode_format(request.confirmation_code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmation code must be 4-6 digits",
        )
    target = UserRepository.get_by_id(db, member_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
    if not target.passcode_hash or not verify_passcode(request.confirmation_code, target.passcode_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid confirmation code",
        )
    try:
        UserRepository.delete_user_and_all_data(db, member_id)
        return MemberDeleteResponse(success=True, message="Member and all data deleted")
    except Exception as e:
        logger.error(f"Error deleting member: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete member: {str(e)}",
        )
