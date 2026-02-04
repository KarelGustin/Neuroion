"""
OAuth flow handlers for integrations.

Manages OAuth authorization flows and callbacks.
"""
import secrets
import logging
from typing import Dict, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from neuroion.core.integrations.base import BaseIntegration
from neuroion.core.integrations.gmail import GmailIntegration

logger = logging.getLogger(__name__)

# In-memory store for OAuth states (in production, use Redis)
_oauth_states: Dict[str, Dict[str, any]] = {}


class OAuthFlowHandler:
    """Handles OAuth flows for integrations."""
    
    @staticmethod
    def get_integration(integration_type: str) -> Optional[BaseIntegration]:
        """
        Get integration instance by type.
        
        Args:
            integration_type: Integration type (e.g., "gmail")
            
        Returns:
            Integration instance or None
        """
        if integration_type == "gmail":
            return GmailIntegration()
        return None
    
    @staticmethod
    def generate_state(user_id: int, integration_type: str) -> str:
        """
        Generate OAuth state for CSRF protection.
        
        Args:
            user_id: User ID
            integration_type: Integration type
            
        Returns:
            State token
        """
        state = secrets.token_urlsafe(32)
        _oauth_states[state] = {
            "user_id": user_id,
            "integration_type": integration_type,
            "created_at": datetime.utcnow(),
        }
        return state
    
    @staticmethod
    def verify_state(state: str) -> Optional[Dict[str, any]]:
        """
        Verify and consume OAuth state.
        
        Args:
            state: State token
            
        Returns:
            State data dict or None if invalid
        """
        state_data = _oauth_states.pop(state, None)
        
        if not state_data:
            return None
        
        # Check expiration (5 minutes)
        if datetime.utcnow() - state_data["created_at"] > timedelta(minutes=5):
            return None
        
        return state_data
    
    @staticmethod
    def cleanup_expired_states() -> int:
        """Clean up expired OAuth states."""
        now = datetime.utcnow()
        expired_keys = [
            key for key, data in _oauth_states.items()
            if now - data["created_at"] > timedelta(minutes=5)
        ]
        for key in expired_keys:
            del _oauth_states[key]
        return len(expired_keys)
