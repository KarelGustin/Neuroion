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


# Endpoints

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
    Create a new member in the household.
    
    Note: In production, members should be added via join tokens (owner-only).
    This endpoint is for direct creation (admin/owner only in production).
    """
    try:
        # Verify household exists
        household = HouseholdRepository.get_by_id(db, user["household_id"])
        if not household:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Household not found",
            )
        
        # Create member
        member = UserRepository.create(
            db=db,
            household_id=user["household_id"],
            name=request.name,
            role="member",
            device_type="web",
        )
        
        # Update member profile fields
        if request.language:
            member.language = request.language
        if request.timezone:
            member.timezone = request.timezone
        if request.style_prefs:
            member.style_prefs_json = request.style_prefs
        if request.preferences:
            member.preferences_json = request.preferences
        if request.consent:
            member.consent_json = request.consent
        
        db.commit()
        db.refresh(member)
        
        return MemberCreateResponse(
            success=True,
            member_id=member.id,
            message="Member created successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating member: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create member: {str(e)}",
        )
