"""
Preferences API endpoints for managing user and household preferences.

Provides endpoints for getting, setting, and deleting preferences.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any

from neuroion.core.memory.db import get_db
from neuroion.core.memory.repository import PreferenceRepository
from neuroion.core.security.permissions import get_current_user

router = APIRouter(prefix="/preferences", tags=["preferences"])


class PreferenceResponse(BaseModel):
    """Preference response model."""
    key: str
    value: Any
    category: Optional[str] = None
    is_user_specific: bool


class PreferencesListResponse(BaseModel):
    """List of preferences response."""
    preferences: List[PreferenceResponse]


class SetPreferenceRequest(BaseModel):
    """Request to set a preference."""
    key: str
    value: Any
    category: Optional[str] = None


@router.get("/user/{user_id}", response_model=PreferencesListResponse)
def get_user_preferences(
    user_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> PreferencesListResponse:
    """
    Get all preferences for a user.
    
    Requires authentication. User can only access their own preferences.
    """
    # Verify authenticated user matches requested user_id
    if user["user_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own preferences",
        )
    
    # Get user-specific preferences
    prefs = PreferenceRepository.get_all(
        db,
        household_id=user["household_id"],
        user_id=user_id,
    )
    
    return PreferencesListResponse(
        preferences=[
            PreferenceResponse(
                key=pref.key,
                value=pref.value,
                category=pref.category,
                is_user_specific=True,
            )
            for pref in prefs
        ]
    )


@router.post("/user/{user_id}", response_model=PreferenceResponse)
def set_user_preference(
    user_id: int,
    request: SetPreferenceRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> PreferenceResponse:
    """
    Set a user-specific preference.
    
    Requires authentication. User can only set their own preferences.
    """
    # Verify authenticated user matches requested user_id
    if user["user_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only set your own preferences",
        )
    
    # Set preference
    pref = PreferenceRepository.set(
        db=db,
        household_id=user["household_id"],
        key=request.key,
        value=request.value,
        user_id=user_id,
        category=request.category,
    )
    
    return PreferenceResponse(
        key=pref.key,
        value=pref.value,
        category=pref.category,
        is_user_specific=True,
    )


@router.delete("/user/{user_id}/{key}")
def delete_user_preference(
    user_id: int,
    key: str,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Delete a user-specific preference.
    
    Requires authentication. User can only delete their own preferences.
    """
    # Verify authenticated user matches requested user_id
    if user["user_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own preferences",
        )
    
    # Delete preference
    deleted = PreferenceRepository.delete(
        db=db,
        household_id=user["household_id"],
        key=key,
        user_id=user_id,
    )
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Preference '{key}' not found",
        )
    
    return {
        "success": True,
        "message": f"Preference '{key}' deleted",
    }


@router.get("/household", response_model=PreferencesListResponse)
def get_household_preferences(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> PreferencesListResponse:
    """
    Get all household-level preferences (read-only).
    
    Requires authentication.
    """
    # Get household-level preferences (where user_id IS NULL)
    prefs = PreferenceRepository.get_all(
        db,
        household_id=user["household_id"],
        user_id=None,
    )
    
    return PreferencesListResponse(
        preferences=[
            PreferenceResponse(
                key=pref.key,
                value=pref.value,
                category=pref.category,
                is_user_specific=False,
            )
            for pref in prefs
        ]
    )
