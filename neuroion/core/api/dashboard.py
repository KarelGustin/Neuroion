"""
Dashboard endpoints for homebase and user dashboards.

Provides stats, WiFi status, and dashboard link management.
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
)
from neuroion.core.services.request_counter import RequestCounter
from neuroion.core.services.wifi_status import WiFiStatusService, WiFiStatus
from neuroion.core.config import settings

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
    
    # Construct URL (localhost for personal dashboards)
    url = f"http://localhost:{settings.dashboard_ui_port}/user/{user_id}?token={link.token}"
    
    return DashboardLinkResponse(
        url=url,
        token=link.token,
    )
