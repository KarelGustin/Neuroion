"""
Network utilities for detecting local IP addresses.
"""
import socket
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def get_local_ip() -> Optional[str]:
    """
    Get the local network IP address of this machine.
    
    Returns:
        Local IP address (e.g., "192.168.1.100") or None if not found
    """
    try:
        # Connect to a remote address to determine local IP
        # This doesn't actually send data, just determines the route
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # Connect to a public DNS server (doesn't actually connect)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            return local_ip
        except Exception:
            # Fallback: try to get hostname IP
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            # Filter out localhost
            if local_ip != "127.0.0.1":
                return local_ip
            return None
        finally:
            s.close()
    except Exception as e:
        logger.error(f"Error getting local IP: {e}")
        return None


def get_dashboard_base_url(port: int, prefer_localhost: bool = False) -> str:
    """
    Get base URL for dashboard access.
    
    Args:
        port: Dashboard port number
        prefer_localhost: If True, prefer localhost over IP address
        
    Returns:
        Base URL (e.g., "http://192.168.1.100:3001" or "http://localhost:3001")
    """
    if prefer_localhost:
        return f"http://localhost:{port}"
    
    local_ip = get_local_ip()
    if local_ip:
        return f"http://{local_ip}:{port}"
    
    # Fallback to localhost if IP detection fails
    return f"http://localhost:{port}"
