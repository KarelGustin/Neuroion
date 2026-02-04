"""
Pairing endpoints for device authentication.

Handles pairing code generation and confirmation for new devices.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from neuroion.core.memory.db import get_db
from neuroion.core.memory.repository import HouseholdRepository, UserRepository, ChatMessageRepository
from neuroion.core.security.tokens import TokenManager, PairingCodeStore
from neuroion.core.agent.onboarding import (
    is_onboarding_completed,
    get_current_onboarding_question,
)
from neuroion.core.agent.agent import Agent

router = APIRouter(prefix="/pair", tags=["pairing"])


class PairStartRequest(BaseModel):
    """Request to start pairing process."""
    household_id: int
    device_id: str
    device_type: str  # ios, telegram, web
    name: str  # User/device name


class PairStartResponse(BaseModel):
    """Response with pairing code."""
    pairing_code: str
    expires_in_minutes: int


class PairConfirmRequest(BaseModel):
    """Request to confirm pairing with code."""
    pairing_code: str
    device_id: str


class PairConfirmResponse(BaseModel):
    """Response with auth token."""
    token: str
    household_id: int
    household_name: str
    user_id: int
    expires_in_hours: int
    onboarding_message: Optional[str] = None  # First onboarding question if needed


@router.post("/start")
def start_pairing(
    request: PairStartRequest,
    db: Session = Depends(get_db),
) -> PairStartResponse:
    """
    Start pairing process.
    
    Generates a short-lived pairing code that can be confirmed via /pair/confirm.
    The code is displayed as QR code on the setup UI.
    """
    # Verify household exists
    household = HouseholdRepository.get_by_id(db, request.household_id)
    if not household:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Household not found",
        )
    
    # Check if device already paired
    existing_user = UserRepository.get_by_device_id(db, request.device_id)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Device already paired",
        )
    
    # Generate pairing code
    code = TokenManager.generate_pairing_code()
    
    # Store pairing code
    PairingCodeStore.store(
        code=code,
        household_id=request.household_id,
    )
    
    return PairStartResponse(
        pairing_code=code,
        expires_in_minutes=10,  # From config
    )


@router.post("/confirm")
def confirm_pairing(
    request: PairConfirmRequest,
    db: Session = Depends(get_db),
) -> PairConfirmResponse:
    """
    Confirm pairing with code.
    
    Validates the pairing code and returns a long-lived auth token.
    Creates a new user if device_id doesn't exist.
    """
    # Verify pairing code
    household_id = PairingCodeStore.verify(request.pairing_code)
    if not household_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired pairing code",
        )
    
    # Check if user already exists for this device
    user = UserRepository.get_by_device_id(db, request.device_id)
    is_new_user = False
    
    if not user:
        is_new_user = True
        # Determine device type from device_id
        device_type = "telegram" if request.device_id.startswith("telegram_") else "unknown"
        
        # Set name based on device type
        if device_type == "telegram":
            user_name = "ion"
        else:
            user_name = f"Device {request.device_id[:8]}"  # Default name for other devices
        
        # Create new user
        user = UserRepository.create(
            db=db,
            household_id=household_id,
            name=user_name,
            role="member",
            device_id=request.device_id,
            device_type=device_type,
        )
    else:
        # Update device type if it's a Telegram user
        if request.device_id.startswith("telegram_") and user.device_type != "telegram":
            user.device_type = "telegram"
            db.commit()
    
    # Get household name
    household = HouseholdRepository.get_by_id(db, household_id)
    household_name = household.name if household else f"Household {household_id}"
    
    # Generate auth token
    token = TokenManager.create_access_token({
        "user_id": user.id,
        "household_id": household_id,
        "device_id": request.device_id,
    })
    
    # Start onboarding conversation if new user or not completed
    onboarding_message = None
    if is_new_user or not is_onboarding_completed(db, household_id, user.id):
        first_question = get_current_onboarding_question(db, household_id, user.id)
        if first_question:
            onboarding_message = first_question["question"]
            # Save the initial onboarding message as assistant message
            ChatMessageRepository.create(
                db=db,
                household_id=household_id,
                user_id=user.id,
                role="assistant",
                content=onboarding_message,
            )
    
    return PairConfirmResponse(
        token=token,
        household_id=household_id,
        household_name=household_name,
        user_id=user.id,
        expires_in_hours=8760,  # 1 year from config
        onboarding_message=onboarding_message,
    )
