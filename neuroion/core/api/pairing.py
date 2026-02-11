"""
Pairing endpoints for device authentication.

Handles pairing code generation and confirmation for new devices.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from neuroion.core.memory.db import get_db
from neuroion.core.memory.repository import HouseholdRepository, UserRepository
from neuroion.core.security.tokens import TokenManager, PairingCodeStore

router = APIRouter(prefix="/pair", tags=["pairing"])


class PairStartRequest(BaseModel):
    """Request to start pairing process."""
    household_id: int
    device_id: str
    device_type: str  # ios, telegram, web
    name: str  # User/device name
    member_id: Optional[int] = None  # If set, link device to this existing member (e.g. after join)


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

    # When linking to an existing member (e.g. after join), skip device check; otherwise ensure device not already paired
    if request.member_id is not None:
        member = UserRepository.get_by_id(db, request.member_id)
        if not member or member.household_id != request.household_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Member not found or not in this household",
            )
    else:
        existing_user = UserRepository.get_by_device_id(db, request.device_id)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Device already paired",
            )

    # Generate pairing code
    code = TokenManager.generate_pairing_code()

    # Store pairing code (optionally bound to member for join → Telegram link)
    PairingCodeStore.store(
        code=code,
        household_id=request.household_id,
        member_id=request.member_id,
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
    If the code was bound to a member (join → Telegram), updates that member's device_id.
    Otherwise creates a new user if device_id doesn't exist.
    """
    # Verify pairing code
    data = PairingCodeStore.verify(request.pairing_code)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired pairing code",
        )
    household_id = data["household_id"]
    member_id = data.get("member_id")

    if member_id is not None:
        # Link Telegram (or other device) to existing member (e.g. after join)
        user = UserRepository.get_by_id(db, member_id)
        if not user or user.household_id != household_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Member not found or invalid",
            )
        # Another user might already have this device_id; reject if so (unless it's this same user)
        existing_by_device = UserRepository.get_by_device_id(db, request.device_id)
        if existing_by_device and existing_by_device.id != user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This device is already linked to another account",
            )
        device_type = "telegram" if request.device_id.startswith("telegram_") else "unknown"
        UserRepository.update(
            db, user.id, device_id=request.device_id, device_type=device_type
        )
        db.commit()
        db.refresh(user)
    else:
        # Original behaviour: find or create user by device_id
        user = UserRepository.get_by_device_id(db, request.device_id)

        if not user:
            device_type = "telegram" if request.device_id.startswith("telegram_") else "unknown"
            user_name = "ion" if device_type == "telegram" else f"Device {request.device_id[:8]}"
            user = UserRepository.create(
                db=db,
                household_id=household_id,
                name=user_name,
                role="member",
                device_id=request.device_id,
                device_type=device_type,
            )
        else:
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
    
    return PairConfirmResponse(
        token=token,
        household_id=household_id,
        household_name=household_name,
        user_id=user.id,
        expires_in_hours=8760,  # 1 year from config
        onboarding_message=None,
    )
