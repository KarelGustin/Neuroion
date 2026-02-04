"""
Gmail integration using OAuth 2.0.

Allows users to connect their Gmail account and grant permissions.
"""
import os
import logging
import requests
from typing import Dict, Any, List, Optional
from urllib.parse import urlencode

from neuroion.core.integrations.base import BaseIntegration

logger = logging.getLogger(__name__)


class GmailIntegration(BaseIntegration):
    """Gmail OAuth integration."""
    
    # Gmail OAuth endpoints
    AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    REVOKE_URL = "https://oauth2.googleapis.com/revoke"
    
    # Gmail API scopes
    SCOPES = [
        "https://www.googleapis.com/auth/gmail.readonly",  # Read emails
        "https://www.googleapis.com/auth/gmail.send",  # Send emails
        "https://www.googleapis.com/auth/gmail.modify",  # Modify emails (delete, etc.)
    ]
    
    def __init__(self):
        """Initialize Gmail integration."""
        super().__init__("gmail")
        self.client_id = os.getenv("GMAIL_CLIENT_ID", "")
        self.client_secret = os.getenv("GMAIL_CLIENT_SECRET", "")
    
    def get_oauth_authorize_url(self, redirect_uri: str, state: str) -> str:
        """
        Get Gmail OAuth authorization URL.
        
        Args:
            redirect_uri: Redirect URI after authorization
            state: State parameter for CSRF protection
            
        Returns:
            Authorization URL
        """
        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.SCOPES),
            "access_type": "offline",  # Request refresh token
            "prompt": "consent",  # Force consent screen to get refresh token
            "state": state,
        }
        
        return f"{self.AUTHORIZE_URL}?{urlencode(params)}"
    
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
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        }
        
        try:
            response = requests.post(self.TOKEN_URL, data=data, timeout=30)
            response.raise_for_status()
            token_data = response.json()
            
            return {
                "access_token": token_data.get("access_token"),
                "refresh_token": token_data.get("refresh_token"),
                "expires_in": token_data.get("expires_in"),
                "token_type": token_data.get("token_type", "Bearer"),
            }
        except requests.RequestException as e:
            logger.error(f"Error exchanging Gmail OAuth code: {e}")
            raise Exception(f"Failed to exchange authorization code: {str(e)}")
    
    def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh access token using refresh token.
        
        Args:
            refresh_token: Refresh token
            
        Returns:
            Dict with new access_token, expires_in, etc.
        """
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
        
        try:
            response = requests.post(self.TOKEN_URL, data=data, timeout=30)
            response.raise_for_status()
            token_data = response.json()
            
            return {
                "access_token": token_data.get("access_token"),
                "expires_in": token_data.get("expires_in"),
                "token_type": token_data.get("token_type", "Bearer"),
            }
        except requests.RequestException as e:
            logger.error(f"Error refreshing Gmail token: {e}")
            raise Exception(f"Failed to refresh token: {str(e)}")
    
    def get_permissions(self) -> List[str]:
        """
        Get list of available permissions for Gmail.
        
        Returns:
            List of permission strings
        """
        return ["read", "write", "delete"]
    
    def test_connection(self, access_token: str) -> bool:
        """
        Test Gmail API connection.
        
        Args:
            access_token: OAuth access token
            
        Returns:
            True if connection successful
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
        }
        
        try:
            # Test with Gmail API profile endpoint
            response = requests.get(
                "https://gmail.googleapis.com/gmail/v1/users/me/profile",
                headers=headers,
                timeout=10,
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error testing Gmail connection: {e}")
            return False
