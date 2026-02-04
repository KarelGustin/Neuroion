"""
Base integration class for external services.

All integrations should inherit from this class.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from neuroion.core.memory.repository import UserIntegrationRepository


class BaseIntegration(ABC):
    """Base class for all integrations."""
    
    def __init__(self, integration_type: str):
        """
        Initialize integration.
        
        Args:
            integration_type: Type identifier (e.g., "gmail")
        """
        self.integration_type = integration_type
    
    @abstractmethod
    def get_oauth_authorize_url(self, redirect_uri: str, state: str) -> str:
        """
        Get OAuth authorization URL.
        
        Args:
            redirect_uri: Redirect URI after authorization
            state: State parameter for CSRF protection
            
        Returns:
            Authorization URL
        """
        pass
    
    @abstractmethod
    def exchange_code_for_token(
        self,
        code: str,
        redirect_uri: str,
    ) -> Dict[str, Any]:
        """
        Exchange authorization code for access token.
        
        Args:
            code: Authorization code from OAuth callback
            redirect_uri: Redirect URI used in authorization
            
        Returns:
            Dict with access_token, refresh_token, expires_in, etc.
        """
        pass
    
    @abstractmethod
    def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh access token using refresh token.
        
        Args:
            refresh_token: Refresh token
            
        Returns:
            Dict with new access_token, expires_in, etc.
        """
        pass
    
    @abstractmethod
    def get_permissions(self) -> List[str]:
        """
        Get list of available permissions for this integration.
        
        Returns:
            List of permission strings (e.g., ["read", "write", "delete"])
        """
        pass
    
    def save_integration(
        self,
        db: Session,
        user_id: int,
        access_token: str,
        refresh_token: Optional[str] = None,
        expires_in: Optional[int] = None,
        permissions: Optional[Dict[str, bool]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Save integration tokens to database.
        
        Args:
            db: Database session
            user_id: User ID
            access_token: OAuth access token
            refresh_token: OAuth refresh token (optional)
            expires_in: Token expiration in seconds (optional)
            permissions: Granted permissions dict (optional)
            metadata: Additional metadata (optional)
        """
        token_expires_at = None
        if expires_in:
            token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        
        UserIntegrationRepository.create_or_update(
            db=db,
            user_id=user_id,
            integration_type=self.integration_type,
            access_token=access_token,
            refresh_token=refresh_token,
            token_expires_at=token_expires_at,
            permissions=permissions,
            metadata=metadata,
        )
    
    def get_integration(self, db: Session, user_id: int) -> Optional[Any]:
        """
        Get integration data for user.
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            UserIntegration object or None
        """
        return UserIntegrationRepository.get_by_user_and_type(
            db, user_id, self.integration_type
        )
    
    def delete_integration(self, db: Session, user_id: int) -> bool:
        """
        Delete integration for user.
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            True if deleted, False if not found
        """
        return UserIntegrationRepository.delete(db, user_id, self.integration_type)
