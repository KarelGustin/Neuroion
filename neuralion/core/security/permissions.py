"""
Permission checking and access control.

Provides middleware and utilities for household-scoped access control.
"""
from typing import Optional
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from neuralion.core.memory.db import get_db
from neuralion.core.memory.repository import UserRepository, HouseholdRepository
from neuralion.core.security.tokens import TokenManager


security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> dict:
    """
    Dependency to get current authenticated user from JWT token.
    
    Returns:
        Dict with user_id, household_id, role, and other token claims
    
    Raises:
        HTTPException if token is invalid or user not found
    """
    token = credentials.credentials
    payload = TokenManager.verify_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("user_id")
    household_id = payload.get("household_id")
    
    if not user_id or not household_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify user still exists
    user = UserRepository.get_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify household still exists
    household = HouseholdRepository.get_by_id(db, household_id)
    if not household:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Household not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Update last seen
    UserRepository.update_last_seen(db, user_id)
    
    return {
        "user_id": user_id,
        "household_id": household_id,
        "role": user.role,
        "name": user.name,
    }


def require_role(allowed_roles: list[str]):
    """
    Decorator factory to require specific user roles.
    
    Usage:
        @app.get("/admin")
        def admin_endpoint(user: dict = Depends(require_role(["owner", "admin"]))):
            ...
    """
    def role_checker(user: dict = Depends(get_current_user)) -> dict:
        if user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {', '.join(allowed_roles)}",
            )
        return user
    
    return role_checker


def require_household_access(user: dict = Depends(get_current_user)) -> dict:
    """
    Dependency to ensure user has access to their household.
    Basic check that user is authenticated and has a household.
    """
    return user
