"""
Integration endpoints for managing external service connections.

Handles OAuth flows and integration management.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any

from neuroion.core.memory.db import get_db
from neuroion.core.memory.repository import UserRepository, UserIntegrationRepository
from neuroion.core.integrations.oauth import OAuthFlowHandler
from neuroion.core.integrations.gmail import GmailIntegration

router = APIRouter(prefix="/integrations", tags=["integrations"])


class IntegrationResponse(BaseModel):
    """Integration response model."""
    integration_type: str
    permissions: Optional[Dict[str, bool]] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: str


class IntegrationsListResponse(BaseModel):
    """List of user integrations."""
    integrations: List[IntegrationResponse]


class ConnectIntegrationRequest(BaseModel):
    """Request to connect an integration."""
    user_id: int
    integration_type: str
    code: str
    redirect_uri: str


class ConnectIntegrationResponse(BaseModel):
    """Response from connecting integration."""
    success: bool
    message: str


class OAuthAuthorizeResponse(BaseModel):
    """OAuth authorization URL response."""
    url: str
    state: str


@router.get("/user/{user_id}", response_model=IntegrationsListResponse)
def get_user_integrations(
    user_id: int,
    db: Session = Depends(get_db),
) -> IntegrationsListResponse:
    """
    Get all integrations for a user.
    """
    # Verify user exists
    user = UserRepository.get_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    integrations = UserIntegrationRepository.get_by_user(db, user_id)
    
    return IntegrationsListResponse(
        integrations=[
            IntegrationResponse(
                integration_type=integration.integration_type,
                permissions=integration.permissions,
                metadata=integration.metadata,
                created_at=integration.created_at.isoformat(),
            )
            for integration in integrations
        ]
    )


@router.get("/oauth/authorize", response_model=OAuthAuthorizeResponse)
def get_oauth_authorize_url(
    integration_type: str = Query(..., description="Integration type (e.g., gmail)"),
    redirect_uri: str = Query(..., description="OAuth redirect URI"),
    user_id: int = Query(..., description="User ID"),
    db: Session = Depends(get_db),
) -> OAuthAuthorizeResponse:
    """
    Get OAuth authorization URL for an integration.
    """
    # Verify user exists
    user = UserRepository.get_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Get integration instance
    integration = OAuthFlowHandler.get_integration(integration_type)
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown integration type: {integration_type}",
        )
    
    # Generate state
    state = OAuthFlowHandler.generate_state(user_id, integration_type)
    
    # Get authorization URL
    url = integration.get_oauth_authorize_url(redirect_uri, state)
    
    return OAuthAuthorizeResponse(url=url, state=state)


@router.post("/connect", response_model=ConnectIntegrationResponse)
def connect_integration(
    request: ConnectIntegrationRequest,
    db: Session = Depends(get_db),
) -> ConnectIntegrationResponse:
    """
    Connect an integration using OAuth callback code.
    """
    # Verify user exists
    user = UserRepository.get_by_id(db, request.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Get integration instance
    integration = OAuthFlowHandler.get_integration(request.integration_type)
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown integration type: {request.integration_type}",
        )
    
    try:
        # Exchange code for token
        token_data = integration.exchange_code_for_token(
            request.code,
            request.redirect_uri,
        )
        
        # Determine permissions based on integration type
        permissions = {}
        available_perms = integration.get_permissions()
        # For now, grant all available permissions
        for perm in available_perms:
            permissions[perm] = True
        
        # Save integration
        integration.save_integration(
            db=db,
            user_id=request.user_id,
            access_token=token_data["access_token"],
            refresh_token=token_data.get("refresh_token"),
            expires_in=token_data.get("expires_in"),
            permissions=permissions,
        )
        
        return ConnectIntegrationResponse(
            success=True,
            message=f"Successfully connected {request.integration_type}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to connect integration: {str(e)}",
        )


@router.delete("/user/{user_id}/{integration_type}")
def disconnect_integration(
    user_id: int,
    integration_type: str,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Disconnect an integration for a user.
    """
    # Verify user exists
    user = UserRepository.get_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Delete integration
    deleted = UserIntegrationRepository.delete(db, user_id, integration_type)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Integration {integration_type} not found for user",
        )
    
    return {
        "success": True,
        "message": f"Successfully disconnected {integration_type}",
    }
