"""
Pairing endpoints for device authentication.

Handles pairing code generation and confirmation for new devices.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from neuroion.core.config import settings
from neuroion.core.memory.db import get_db
from neuroion.core.memory.repository import HouseholdRepository, UserRepository, VpnPeerRepository
from neuroion.core.security.permissions import get_current_user
from neuroion.core.security.tokens import TokenManager, PairingCodeStore
from neuroion.core.wireguard_manager import add_peer as wireguard_add_peer, remove_peer as wireguard_remove_peer

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
    include_vpn: Optional[bool] = False  # When True, generate WireGuard config and return in response


class PairConfirmResponse(BaseModel):
    """Response with auth token."""
    token: str
    household_id: int
    household_name: str
    user_id: int
    expires_in_hours: int
    onboarding_message: Optional[str] = None  # First onboarding question if needed
    wireguard_config: Optional[str] = None  # WireGuard client config when include_vpn was True
    vpn_base_url: Optional[str] = None  # e.g. https://10.66.66.1


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

    wireguard_config: Optional[str] = None
    vpn_base_url: Optional[str] = None
    if request.include_vpn and settings.wireguard_endpoint:
        wg = wireguard_add_peer(request.device_id)
        if wg:
            VpnPeerRepository.create(
                db,
                user_id=user.id,
                device_id=request.device_id,
                client_public_key=wg["client_public_key"],
                client_ip=wg["client_ip"],
            )
            wireguard_config = wg["client_config"]
            vpn_base_url = f"https://{settings.vpn_server_ip}"

    return PairConfirmResponse(
        token=token,
        household_id=household_id,
        household_name=household_name,
        user_id=user.id,
        expires_in_hours=8760,  # 1 year from config
        onboarding_message=None,
        wireguard_config=wireguard_config,
        vpn_base_url=vpn_base_url,
    )


@router.post("/vpn-revoke")
def revoke_vpn_peer(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Revoke the WireGuard VPN peer for the current device. Call when unpairing.
    Removes the peer from the unit's WireGuard config and from the database.
    """
    device_id = current_user.get("device_id")
    if not device_id:
        return {"revoked": False, "message": "No device_id in token"}
    peer = VpnPeerRepository.get_by_device_id(db, device_id)
    if not peer:
        return {"revoked": False, "message": "No VPN peer for this device"}
    wireguard_remove_peer(peer.client_public_key)
    VpnPeerRepository.delete_by_device_id(db, device_id)
    return {"revoked": True}
