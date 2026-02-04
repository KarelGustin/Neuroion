"""
WiFi status checking service.

Determines connection status: online (green), no signal (blue), or error (red).
"""
import logging
import subprocess
from typing import Tuple, Optional
from enum import Enum

from neuroion.core.services.wifi_service import WiFiService

logger = logging.getLogger(__name__)


class WiFiStatus(str, Enum):
    """WiFi connection status."""
    ONLINE = "online"  # Green - connected and working
    NO_SIGNAL = "no_signal"  # Blue - no WiFi connection
    ERROR = "error"  # Red - error state


class WiFiStatusService:
    """Service for checking WiFi connection status."""
    
    @staticmethod
    def get_status() -> Tuple[WiFiStatus, str]:
        """
        Get current WiFi status.
        
        Returns:
            Tuple of (status, message)
        """
        try:
            # First check if we have a WiFi connection
            current_ssid = WiFiService.get_current_ssid()
            
            if not current_ssid:
                return (WiFiStatus.NO_SIGNAL, "No WiFi connection")
            
            # Test internet connectivity
            connected, message = WiFiService.test_connection()
            
            if connected:
                return (WiFiStatus.ONLINE, f"Connected to {current_ssid}")
            else:
                # We have WiFi but no internet - could be no signal or router issue
                return (WiFiStatus.NO_SIGNAL, f"Connected to {current_ssid} but no internet")
        
        except Exception as e:
            logger.error(f"Error checking WiFi status: {e}", exc_info=True)
            return (WiFiStatus.ERROR, f"Error: {str(e)}")
    
    @staticmethod
    def get_status_color(status: WiFiStatus) -> str:
        """
        Get color code for status (for frontend).
        
        Args:
            status: WiFi status
            
        Returns:
            Color name: "green", "blue", or "red"
        """
        if status == WiFiStatus.ONLINE:
            return "green"
        elif status == WiFiStatus.NO_SIGNAL:
            return "blue"
        else:
            return "red"
