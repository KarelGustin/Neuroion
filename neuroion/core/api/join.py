"""
Join token endpoints for secure member onboarding.
"""
import logging
import secrets
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

from neuroion.core.memory.db import get_db
from neuroion.core.memory.repository import (
    HouseholdRepository,
    UserRepository,
    DeviceConfigRepository,
)
from neuroion.core.security.join_tokens import JoinTokenManager
from neuroion.core.utils.slug import slugify
from neuroion.core.security.permissions import get_current_user, require_role

router = APIRouter(prefix="/api", tags=["join"])


# Request/Response Models

class JoinTokenCreateRequest(BaseModel):
    """Request to create a join token."""
    expires_in_minutes: Optional[int] = 10


class JoinTokenCreateResponse(BaseModel):
    """Response with created join token."""
    token: str
    expires_at: str
    qr_url: str
    join_url: str


class JoinTokenConsumeRequest(BaseModel):
    """Request to consume a join token and create member."""
    token: str
    member: Dict[str, Any]  # name, language, timezone, style_prefs, preferences, consent


class JoinTokenConsumeResponse(BaseModel):
    """Response after consuming join token."""
    success: bool
    member_id: int
    household_id: int
    message: str
    page_name: str  # slug for /p/{page_name}
    setup_token: str  # one-time token to set passcode (POST /dashboard/set-passcode)


# Endpoints

@router.post("/join-token/create", response_model=JoinTokenCreateResponse)
def create_join_token(
    request: JoinTokenCreateRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role(["owner"])),
) -> JoinTokenCreateResponse:
    """
    Create a new join token (owner-only).
    
    Returns token with QR URL for member onboarding.
    """
    try:
        token_data = JoinTokenManager.create_token(
            db=db,
            household_id=user["household_id"],
            created_by_member_id=user["user_id"],
            expires_in_minutes=request.expires_in_minutes,
        )
        
        return JoinTokenCreateResponse(**token_data)
    except Exception as e:
        logger.error(f"Error creating join token: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create join token: {str(e)}",
        )


@router.post("/join-token/consume", response_model=JoinTokenConsumeResponse)
def consume_join_token(
    request: JoinTokenConsumeRequest,
    db: Session = Depends(get_db),
) -> JoinTokenConsumeResponse:
    """
    Consume a join token and create a new member.
    
    Public endpoint (no auth required, token provides security).
    """
    try:
        # Verify and consume token
        token_data = JoinTokenManager.consume_token(db, request.token)
        
        if not token_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired token",
            )
        
        household_id = token_data["household_id"]
        
        # Verify household exists
        household = HouseholdRepository.get_by_id(db, household_id)
        if not household:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Household not found",
            )
        
        # Extract member data
        member_data = request.member
        name = member_data.get("name", "")
        if not name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Member name is required",
            )

        # Generate unique page_name (slug) for personal dashboard
        base_slug = slugify(name)
        if not base_slug:
            base_slug = "user"
        page_name = UserRepository.ensure_unique_page_name(db, base_slug, exclude_user_id=None)

        # Create member with page_name
        member = UserRepository.create(
            db=db,
            household_id=household_id,
            name=name,
            role="member",
            device_type="web",
            page_name=page_name,
        )

        # Update member profile fields
        if "language" in member_data:
            member.language = member_data["language"]
        if "timezone" in member_data:
            member.timezone = member_data["timezone"]
        if "style_prefs" in member_data:
            member.style_prefs_json = member_data["style_prefs"]
        if "preferences" in member_data:
            member.preferences_json = member_data["preferences"]
        if "consent" in member_data:
            member.consent_json = member_data["consent"]

        db.commit()
        db.refresh(member)

        # One-time setup_token so frontend can call set-passcode (no auth yet)
        setup_token = secrets.token_urlsafe(32)
        UserRepository.set_setup_token(db, member.id, setup_token, expires_in_minutes=10)

        return JoinTokenConsumeResponse(
            success=True,
            member_id=member.id,
            household_id=household_id,
            message="Member created successfully",
            page_name=page_name,
            setup_token=setup_token,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error consuming join token: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to consume join token: {str(e)}",
        )


@router.get("/join-token/verify")
def verify_join_token(
    token: str = Query(..., description="Join token to verify"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Verify if a join token is valid (without consuming it).
    
    Public endpoint for checking token validity before showing join form.
    """
    is_valid = JoinTokenManager.verify_token(db, token)
    
    if not is_valid:
        return {
            "valid": False,
            "message": "Invalid or expired token",
        }
    
    return {
        "valid": True,
        "message": "Token is valid",
    }


@router.get("/join", response_class=HTMLResponse)
def get_join_page(
    token: Optional[str] = Query(None, description="Join token"),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """
    Serve the join page for member onboarding.
    
    If token is provided, validates it and shows onboarding form.
    If no token, shows error page.
    """
    # Get device config for hostname
    device_config = DeviceConfigRepository.get(db)
    hostname = device_config.hostname if device_config else "neuroion.local"
    
    if not token:
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Join Neuroion - Invalid Token</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    min-height: 100vh;
                    margin: 0;
                    background: #000;
                    color: #fff;
                }}
                .container {{
                    text-align: center;
                    padding: 2rem;
                }}
                h1 {{ color: #ff4444; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Invalid Token</h1>
                <p>No join token provided. Please scan the QR code or use the join link.</p>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(content=html)
    
    # Verify token
    is_valid = JoinTokenManager.verify_token(db, token)
    
    if not is_valid:
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Join Neuroion - Invalid Token</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    min-height: 100vh;
                    margin: 0;
                    background: #000;
                    color: #fff;
                }}
                .container {{
                    text-align: center;
                    padding: 2rem;
                }}
                h1 {{ color: #ff4444; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Invalid or Expired Token</h1>
                <p>The join token is invalid or has expired. Please request a new one.</p>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(content=html)
    
    # Serve join form (will be replaced by Next.js dashboard in production)
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Join Neuroion</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                display: flex;
                align-items: center;
                justify-content: center;
                min-height: 100vh;
                margin: 0;
                background: #000;
                color: #fff;
            }}
            .container {{
                max-width: 500px;
                padding: 2rem;
            }}
            h1 {{ margin-bottom: 1rem; }}
            .note {{
                color: #888;
                font-size: 0.9rem;
                margin-top: 1rem;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Join Neuroion</h1>
            <p>Redirecting to join form...</p>
            <p class="note">This page will be replaced by the Next.js dashboard join form.</p>
            <script>
                // Redirect to Next.js dashboard join page
                window.location.href = '/dashboard/join?token={token}';
            </script>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)
