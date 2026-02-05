"""
Health check endpoint.

Returns service status and system information.
"""
from fastapi import APIRouter
from datetime import datetime

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def health():
    """
    Health check endpoint.
    
    Returns:
        Service status and basic system information
    """
    return {
        "status": "ok",
        "service": "neuroion-core",
        "timestamp": datetime.utcnow().isoformat(),
    }
