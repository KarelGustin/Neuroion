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
from neuroion.core.security.tokens import TokenManager
from datetime import timedelta

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


class DashboardStatsResponse(BaseModel):
    """Homebase dashboard stats response."""
    member_count: int
    daily_requests: int
    wifi_status: str  # "online", "no_signal", "error"
    wifi_status_color: str  # "green", "blue", "red"
    wifi_message: str


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
        return DashboardStatsResponse(
            member_count=0,
            daily_requests=0,
            wifi_status=wifi_status.value,
            wifi_status_color=WiFiStatusService.get_status_color(wifi_status),
            wifi_message=wifi_message,
        )
    
    household_id = households[0].id
    
    # Get member count
    members = UserRepository.get_by_household(db, household_id)
    member_count = len(members)
    
    # Get daily request count
    daily_requests = RequestCounter.get_today_count(db, household_id)
    
    # Get WiFi status
    wifi_status, wifi_message = WiFiStatusService.get_status()
    
    return DashboardStatsResponse(
        member_count=member_count,
        daily_requests=daily_requests,
        wifi_status=wifi_status.value,
        wifi_status_color=WiFiStatusService.get_status_color(wifi_status),
        wifi_message=wifi_message,
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
    login_code = LoginCodeRepository.create(db, request.user_id, expires_in_seconds=60)
    
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
