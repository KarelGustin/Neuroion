"""
Join token management for secure member onboarding.

Handles creation, validation, and consumption of single-use join tokens.
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from neuroion.core.memory.repository import JoinTokenRepository


class JoinTokenManager:
    """Manages join tokens for secure member onboarding."""
    
    DEFAULT_EXPIRY_MINUTES = 10
    
    @staticmethod
    def create_token(
        db: Session,
        household_id: int,
        created_by_member_id: int,
        expires_in_minutes: int = None,
    ) -> Dict[str, Any]:
        """
        Create a new join token.
        
        Args:
            db: Database session
            household_id: Household ID
            created_by_member_id: Member ID who created the token (must be owner)
            expires_in_minutes: Expiration time in minutes (default: 10)
        
        Returns:
            Dict with token, expires_at, and qr_url
        """
        if expires_in_minutes is None:
            expires_in_minutes = JoinTokenManager.DEFAULT_EXPIRY_MINUTES
        
        join_token = JoinTokenRepository.create(
            db=db,
            household_id=household_id,
            created_by_member_id=created_by_member_id,
            expires_in_minutes=expires_in_minutes,
        )
        
        # Generate QR URL (will use actual hostname/IP in production)
        qr_url = f"http://neuroion.local/join?token={join_token.token}"
        
        return {
            "token": join_token.token,
            "expires_at": join_token.expires_at.isoformat(),
            "qr_url": qr_url,
            "join_url": qr_url,
        }
    
    @staticmethod
    def consume_token(db: Session, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify and consume a join token.
        
        Args:
            db: Database session
            token: Token string to verify
        
        Returns:
            Dict with household_id and created_by_member_id if valid, None otherwise
        """
        join_token = JoinTokenRepository.consume(db, token)
        
        if not join_token:
            return None
        
        return {
            "household_id": join_token.household_id,
            "created_by_member_id": join_token.created_by_member_id,
            "token_id": join_token.id,
        }
    
    @staticmethod
    def verify_token(db: Session, token: str) -> bool:
        """
        Verify if a token is valid (without consuming it).
        
        Args:
            db: Database session
            token: Token string to verify
        
        Returns:
            True if token is valid and not expired, False otherwise
        """
        join_token = JoinTokenRepository.get_by_token(db, token)
        
        if not join_token:
            return False
        
        # Check if already used
        if join_token.used_at:
            return False
        
        # Check if expired
        if datetime.utcnow() > join_token.expires_at:
            return False
        
        return True
    
    @staticmethod
    def cleanup_expired(db: Session) -> int:
        """
        Remove expired join tokens.
        
        Args:
            db: Database session
        
        Returns:
            Number of tokens deleted
        """
        return JoinTokenRepository.cleanup_expired(db)
    
    @staticmethod
    def get_active_tokens(
        db: Session,
        household_id: Optional[int] = None,
        created_by_member_id: Optional[int] = None,
    ) -> list[Dict[str, Any]]:
        """
        Get active (unused, not expired) join tokens.
        
        Args:
            db: Database session
            household_id: Optional filter by household
            created_by_member_id: Optional filter by creator
        
        Returns:
            List of token dicts
        """
        tokens = JoinTokenRepository.get_active_tokens(
            db=db,
            household_id=household_id,
            created_by_member_id=created_by_member_id,
        )
        
        return [
            {
                "id": token.id,
                "token": token.token,
                "household_id": token.household_id,
                "created_by_member_id": token.created_by_member_id,
                "expires_at": token.expires_at.isoformat(),
                "created_at": token.created_at.isoformat(),
                "join_url": f"http://neuroion.local/join?token={token.token}",
            }
            for token in tokens
        ]
