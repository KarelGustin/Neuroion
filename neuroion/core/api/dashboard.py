"""
Dashboard endpoints for homebase and user dashboards.

CORE DASHBOARD (Household-level):
- These endpoints provide data for the entire household
- No authentication required (for homebase display)
- Endpoints: /dashboard/stats, /dashboard/members, /dashboard/login-code/generate

USER DASHBOARD (User-specific):
- These endpoints provide data for individual users
- Authentication required via JWT token
- User can only access their own data
- Endpoints: /integrations/user/{user_id}, etc.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from neuroion.core.memory.db import get_db
from neuroion.core.memory.repository import (
    HouseholdRepository,
    UserRepository,
    DashboardLinkRepository,
    LoginCodeRepository,
)
from neuroion.core.services.request_counter import RequestCounter
from neuroion.core.services.wifi_status import WiFiStatusService, WiFiStatus
from neuroion.core.services.network import get_dashboard_base_url
from neuroion.core.config import settings
from neuroion.core.security.tokens import TokenManager, PairingCodeStore
from neuroion.core.security.passcode import hash_passcode, verify_passcode, is_valid_passcode_format
from neuroion.core.security.join_tokens import JoinTokenManager
from neuroion.core.security.permissions import get_current_user
from datetime import timedelta
import time

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

# Startup time for "days since boot" (shared with setup status)
try:
    from neuroion.core.api.setup import _startup_time as _dashboard_startup_time
except Exception:
    _dashboard_startup_time = time.time()


class DashboardStatsResponse(BaseModel):
    """Homebase dashboard stats response."""
    member_count: int
    daily_requests: int
    wifi_status: str  # "online", "no_signal", "error"
    wifi_status_color: str  # "green", "blue", "red"
    wifi_message: str
    days_since_boot: int  # Dagen sinds geboot


class DashboardLinkResponse(BaseModel):
    """Dashboard link response."""
    url: str
    token: str


class LoginCodeGenerateRequest(BaseModel):
    """Request to generate login code."""
    user_id: int


class LoginCodeGenerateResponse(BaseModel):
    """Response from generating login code."""
    code: str
    expires_at: str  # ISO format datetime


class LoginCodeVerifyRequest(BaseModel):
    """Request to verify login code."""
    code: str


class LoginCodeVerifyResponse(BaseModel):
    """Response from verifying login code."""
    token: str
    user_id: int


class MemberResponse(BaseModel):
    """Household member response."""
    id: int
    name: str
    role: str


class MembersListResponse(BaseModel):
    """List of household members."""
    members: list[MemberResponse]


class ByPageResponse(BaseModel):
    """Public response for GET by-page (exists and optional display_name)."""
    exists: bool
    display_name: Optional[str] = None


class UnlockRequest(BaseModel):
    """Request to unlock personal dashboard with passcode."""
    page_name: str
    passcode: str


class UnlockResponse(BaseModel):
    """Response after successful unlock (JWT for personal dashboard)."""
    token: str
    user_id: int


class SetPasscodeRequest(BaseModel):
    """Request to set passcode (after join, using setup_token)."""
    setup_token: str
    passcode: str


class SetPasscodeResponse(BaseModel):
    """Response after setting passcode."""
    success: bool
    message: str


class DashboardMemberDeleteRequest(BaseModel):
    """Request to delete a member from kiosk (no auth)."""
    member_id: int
    confirmation_code: Optional[str] = None


class DashboardMemberDeleteResponse(BaseModel):
    """Response after deleting member from kiosk."""
    success: bool
    message: str


class AddMemberRequest(BaseModel):
    """Request to add a member and get Telegram pairing QR."""
    name: str


class AddMemberResponse(BaseModel):
    """Response after adding member: member_id, pairing code and QR value for Telegram."""
    member_id: int
    pairing_code: str
    qr_value: str


class DashboardJoinTokenRequest(BaseModel):
    """Request to create join token from kiosk (no auth)."""
    expires_in_minutes: Optional[int] = 10


class DashboardJoinTokenResponse(BaseModel):
    """Response with join token and URLs for add-member QR."""
    token: str
    expires_at: str
    join_url: str
    qr_url: str


@router.post("/add-member", response_model=AddMemberResponse)
def add_member(
    request: AddMemberRequest,
    db: Session = Depends(get_db),
) -> AddMemberResponse:
    """
    Single-user mode: adding members is disabled. Returns 410 Gone.
    """
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="Single-user mode: adding members is disabled",
    )


@router.post("/join-token", response_model=DashboardJoinTokenResponse)
def create_dashboard_join_token(
    request: DashboardJoinTokenRequest,
    db: Session = Depends(get_db),
) -> DashboardJoinTokenResponse:
    """
    Single-user mode: join tokens for adding members are disabled. Returns 410 Gone.
    """
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="Single-user mode: join token is disabled",
    )


@router.post("/member-delete", response_model=DashboardMemberDeleteResponse)
def dashboard_member_delete(
    request: DashboardMemberDeleteRequest,
    db: Session = Depends(get_db),
) -> DashboardMemberDeleteResponse:
    """
    Single-user mode: deleting members is disabled. Returns 410 Gone.
    """
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="Single-user mode: deleting members is disabled",
    )


@router.get("/stats", response_model=DashboardStatsResponse)
def get_dashboard_stats(
    db: Session = Depends(get_db),
) -> DashboardStatsResponse:
    """
    Get homebase dashboard stats.
    
    Returns member count, daily requests, and WiFi status.
    No authentication required for homebase display.
    """
    # Get first household (for now, assuming single household setup)
    households = HouseholdRepository.get_all(db)
    if not households:
        # Return default values if no household exists
        wifi_status, wifi_message = WiFiStatusService.get_status()
        uptime_seconds = max(0, int(time.time() - _dashboard_startup_time))
        return DashboardStatsResponse(
            member_count=0,
            daily_requests=0,
            wifi_status=wifi_status.value,
            wifi_status_color=WiFiStatusService.get_status_color(wifi_status),
            wifi_message=wifi_message,
            days_since_boot=uptime_seconds // 86400,
        )
    
    household_id = households[0].id

    # Single-user mode: member_count is always 1 when configured
    member_count = 1

    # Get daily request count
    daily_requests = RequestCounter.get_today_count(db, household_id)

    # Get WiFi status
    wifi_status, wifi_message = WiFiStatusService.get_status()

    # Days since boot (Neuroion process start)
    uptime_seconds = max(0, int(time.time() - _dashboard_startup_time))
    days_since_boot = uptime_seconds // 86400

    return DashboardStatsResponse(
        member_count=member_count,
        daily_requests=daily_requests,
        wifi_status=wifi_status.value,
        wifi_status_color=WiFiStatusService.get_status_color(wifi_status),
        wifi_message=wifi_message,
        days_since_boot=days_since_boot,
    )


@router.get("/user/{user_id}/link", response_model=DashboardLinkResponse)
def get_user_dashboard_link(
    user_id: int,
    db: Session = Depends(get_db),
) -> DashboardLinkResponse:
    """
    Get or create personal dashboard link for a user.
    
    Returns localhost URL with token for accessing personal dashboard.
    """
    # Verify user exists
    user = UserRepository.get_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Get or create dashboard link
    link = DashboardLinkRepository.get_or_create(db, user_id)
    
    # Construct URL using detected local IP (works for mobile access)
    base_url = get_dashboard_base_url(settings.dashboard_ui_port, prefer_localhost=False)
    url = f"{base_url}/user/{user_id}?token={link.token}"
    
    return DashboardLinkResponse(
        url=url,
        token=link.token,
    )


@router.post("/login-code/generate", response_model=LoginCodeGenerateResponse)
def generate_login_code(
    request: LoginCodeGenerateRequest,
    db: Session = Depends(get_db),
) -> LoginCodeGenerateResponse:
    """
    Generate a login code for a user.
    
    Code expires after 60 seconds.
    No authentication required (for homebase dashboard access).
    """
    # Verify user exists
    user = UserRepository.get_by_id(db, request.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Generate login code
    login_code = LoginCodeRepository.create_for_user(db, request.user_id, expires_in_seconds=60)
    
    return LoginCodeGenerateResponse(
        code=login_code.code,
        expires_at=login_code.expires_at.isoformat(),
    )


@router.post("/login-code/verify", response_model=LoginCodeVerifyResponse)
def verify_login_code(
    request: LoginCodeVerifyRequest,
    db: Session = Depends(get_db),
) -> LoginCodeVerifyResponse:
    """
    Verify a login code and return dashboard token.
    
    Code is deleted after use (one-time use).
    """
    # Verify code
    user_id = LoginCodeRepository.verify(db, request.code)
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired login code",
        )
    
    # Get user to get household_id
    user = UserRepository.get_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Generate JWT token for dashboard access
    token = TokenManager.create_access_token(
        data={
            "user_id": user_id,
            "household_id": user.household_id,
        },
        expires_delta=timedelta(hours=24),  # Token valid for 24 hours
    )
    
    return LoginCodeVerifyResponse(
        token=token,
        user_id=user_id,
    )


@router.get("/members", response_model=MembersListResponse)
def get_household_members(
    db: Session = Depends(get_db),
) -> MembersListResponse:
    """
    Get list of household members.
    
    No authentication required (for homebase display).
    Returns empty list if no household exists.
    """
    # Get first household (for now, assuming single household setup)
    households = HouseholdRepository.get_all(db)
    if not households:
        return MembersListResponse(members=[])
    
    household_id = households[0].id
    
    # Get members
    members = UserRepository.get_by_household(db, household_id)
    
    return MembersListResponse(
        members=[
            MemberResponse(
                id=member.id,
                name=member.name,
                role=member.role,
            )
            for member in members
        ]
    )


@router.get("/by-page/{page_name}", response_model=ByPageResponse)
def get_by_page(
    page_name: str,
    db: Session = Depends(get_db),
) -> ByPageResponse:
    """
    Public lookup: does this page_name exist? Optionally return display name.
    No sensitive data. For "save this page" UX.
    """
    user = UserRepository.get_by_page_name(db, page_name.strip().lower())
    if not user:
        return ByPageResponse(exists=False)
    return ByPageResponse(exists=True, display_name=user.name)


@router.post("/unlock", response_model=UnlockResponse)
def unlock_with_passcode(
    request: UnlockRequest,
    db: Session = Depends(get_db),
) -> UnlockResponse:
    """
    Login to personal dashboard with page_name + passcode.
    Returns JWT (same format as login-code verify).
    """
    if not is_valid_passcode_format(request.passcode):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passcode must be 4-6 digits",
        )
    user = UserRepository.get_by_page_name(db, request.page_name.strip().lower())
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid page or passcode",
        )
    if not user.passcode_hash or not verify_passcode(request.passcode, user.passcode_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid page or passcode",
        )
    token = TokenManager.create_access_token(
        data={
            "user_id": user.id,
            "household_id": user.household_id,
        },
        expires_delta=timedelta(hours=24),
    )
    return UnlockResponse(token=token, user_id=user.id)


class UserStatsResponse(BaseModel):
    """User stats for personal dashboard."""
    daily_requests: int
    message_count: int


@router.get("/user/stats", response_model=UserStatsResponse)
def get_user_stats(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> UserStatsResponse:
    """Get stats for the current user (for personal dashboard)."""
    household_id = user["household_id"]
    user_id = user["user_id"]
    daily_requests = RequestCounter.get_today_count(db, household_id)
    from sqlalchemy import func
    from neuroion.core.memory.models import ChatMessage
    msg_count = db.query(func.count(ChatMessage.id)).filter(
        ChatMessage.user_id == user_id,
    ).scalar() or 0
    return UserStatsResponse(
        daily_requests=daily_requests,
        message_count=msg_count,
    )


@router.post("/set-passcode", response_model=SetPasscodeResponse)
def set_passcode(
    request: SetPasscodeRequest,
    db: Session = Depends(get_db),
) -> SetPasscodeResponse:
    """
    Set passcode for a user after join (one-time setup_token from consume response).
    """
    if not is_valid_passcode_format(request.passcode):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passcode must be 4-6 digits",
        )
    user = UserRepository.get_by_setup_token(db, request.setup_token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired setup token",
        )
    hashed = hash_passcode(request.passcode)
    UserRepository.set_passcode(db, user.id, hashed)
    return SetPasscodeResponse(success=True, message="Passcode set successfully")
