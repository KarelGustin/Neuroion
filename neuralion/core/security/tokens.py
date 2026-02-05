"""
Token management for authentication and pairing.

Handles JWT token generation/validation and pairing code management.
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
import secrets
import hashlib

from neuralion.core.config import settings


class TokenManager:
    """Manages JWT tokens and pairing codes."""
    
    @staticmethod
    def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """
        Create a JWT access token.
        
        Args:
            data: Payload data (should include household_id, user_id)
            expires_delta: Optional expiration time delta
        
        Returns:
            Encoded JWT token string
        """
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(hours=settings.token_expire_hours)
        
        to_encode.update({"exp": expire, "iat": datetime.utcnow()})
        
        encoded_jwt = jwt.encode(
            to_encode,
            settings.secret_key,
            algorithm=settings.token_algorithm
        )
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str) -> Optional[Dict[str, Any]]:
        """
        Verify and decode a JWT token.
        
        Args:
            token: JWT token string
        
        Returns:
            Decoded payload dict or None if invalid
        """
        try:
            payload = jwt.decode(
                token,
                settings.secret_key,
                algorithms=[settings.token_algorithm]
            )
            return payload
        except JWTError:
            return None
    
    @staticmethod
    def generate_pairing_code() -> str:
        """
        Generate a short-lived pairing code (6 digits).
        
        Returns:
            6-digit pairing code string
        """
        return f"{secrets.randbelow(1000000):06d}"
    
    @staticmethod
    def hash_pairing_code(code: str) -> str:
        """
        Hash a pairing code for storage.
        
        Args:
            code: Plain pairing code
        
        Returns:
            SHA256 hash of the code
        """
        return hashlib.sha256(code.encode()).hexdigest()
    
    @staticmethod
    def verify_pairing_code(code: str, hashed_code: str) -> bool:
        """
        Verify a pairing code against its hash.
        
        Args:
            code: Plain pairing code
            hashed_code: Stored hash
        
        Returns:
            True if code matches hash
        """
        return TokenManager.hash_pairing_code(code) == hashed_code


# In-memory pairing code store (in production, use Redis or database)
_pairing_codes: Dict[str, Dict[str, Any]] = {}


class PairingCodeStore:
    """Temporary store for pairing codes (expires after timeout)."""
    
    @staticmethod
    def store(code: str, household_id: int, expires_in_minutes: int = None) -> None:
        """Store a pairing code with expiration."""
        expires_in = expires_in_minutes or settings.pairing_code_expire_minutes
        expires_at = datetime.utcnow() + timedelta(minutes=expires_in)
        
        hashed = TokenManager.hash_pairing_code(code)
        _pairing_codes[hashed] = {
            "household_id": household_id,
            "expires_at": expires_at,
        }
    
    @staticmethod
    def verify(code: str) -> Optional[int]:
        """
        Verify a pairing code and return household_id if valid.
        
        Returns:
            household_id if valid, None otherwise
        """
        hashed = TokenManager.hash_pairing_code(code)
        entry = _pairing_codes.get(hashed)
        
        if not entry:
            return None
        
        # Check expiration
        if datetime.utcnow() > entry["expires_at"]:
            del _pairing_codes[hashed]
            return None
        
        # Return household_id and remove code (one-time use)
        household_id = entry["household_id"]
        del _pairing_codes[hashed]
        return household_id
    
    @staticmethod
    def cleanup_expired() -> None:
        """Remove expired pairing codes."""
        now = datetime.utcnow()
        expired_keys = [
            key for key, entry in _pairing_codes.items()
            if now > entry["expires_at"]
        ]
        for key in expired_keys:
            del _pairing_codes[key]
