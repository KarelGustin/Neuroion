"""
WiFi configuration service.

Platform-specific WiFi configuration for macOS and Linux (Raspberry Pi).
"""
import platform
import subprocess
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class WiFiService:
    """WiFi configuration service."""
    
    @staticmethod
    def get_platform() -> str:
        """Get current platform."""
        system = platform.system().lower()
        if system == "darwin":
            return "macos"
        elif system == "linux":
            return "linux"
        else:
            return "unknown"
    
    @staticmethod
    def configure_wifi(ssid: str, password: str) -> Tuple[bool, str]:
        """
        Configure WiFi connection.
        
        Args:
            ssid: WiFi network SSID
            password: WiFi password
        
        Returns:
            Tuple of (success, message)
        """
        platform_name = WiFiService.get_platform()
        
        if platform_name == "macos":
            return WiFiService._configure_macos(ssid, password)
        elif platform_name == "linux":
            return WiFiService._configure_linux(ssid, password)
        else:
            logger.warning(f"WiFi configuration not supported on platform: {platform_name}")
            return (False, f"WiFi configuration not supported on {platform_name}")
    
    @staticmethod
    def _configure_macos(ssid: str, password: str) -> Tuple[bool, str]:
        """
        Configure WiFi on macOS using networksetup.
        
        Note: This requires admin privileges and may not work in all scenarios.
        For production, consider using NetworkManager or system preferences API.
        """
        try:
            # Check if network exists
            result = subprocess.run(
                ["networksetup", "-listallhardwareports"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            
            if result.returncode != 0:
                return (False, "Failed to list network interfaces")
            
            # Find Wi-Fi interface (usually en0 or en1)
            wifi_interface = None
            for line in result.stdout.split("\n"):
                if "Wi-Fi" in line or "AirPort" in line:
                    # Next line should contain the device
                    continue
                if "Device:" in line and not wifi_interface:
                    wifi_interface = line.split("Device:")[-1].strip()
                    break
            
            if not wifi_interface:
                return (False, "Wi-Fi interface not found")
            
            # Connect to network
            # Note: This is a simplified approach. Real implementation may need
            # to handle security types (WPA, WPA2, etc.)
            result = subprocess.run(
                [
                    "networksetup",
                    "-setairportnetwork",
                    wifi_interface,
                    ssid,
                    password,
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            
            if result.returncode == 0:
                return (True, f"Successfully connected to {ssid}")
            else:
                error_msg = result.stderr or result.stdout or "Unknown error"
                return (False, f"Failed to connect: {error_msg}")
        
        except subprocess.TimeoutExpired:
            return (False, "WiFi configuration timed out")
        except Exception as e:
            logger.error(f"Error configuring WiFi on macOS: {e}", exc_info=True)
            return (False, f"Error: {str(e)}")
    
    @staticmethod
    def _configure_linux(ssid: str, password: str) -> Tuple[bool, str]:
        """
        Configure WiFi on Linux using nmcli (NetworkManager).
        
        This is the standard approach for Raspberry Pi and most Linux systems.
        """
        try:
            # Check if nmcli is available
            result = subprocess.run(
                ["which", "nmcli"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            
            if result.returncode != 0:
                return (
                    False,
                    "nmcli not found. Install NetworkManager: sudo apt-get install network-manager",
                )
            
            # Check if WiFi is enabled
            result = subprocess.run(
                ["nmcli", "radio", "wifi"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            
            if "enabled" not in result.stdout.lower():
                # Enable WiFi
                subprocess.run(
                    ["nmcli", "radio", "wifi", "on"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
            
            # Connect to network
            # nmcli device wifi connect SSID password PASSWORD
            result = subprocess.run(
                [
                    "nmcli",
                    "device",
                    "wifi",
                    "connect",
                    ssid,
                    "password",
                    password,
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            
            if result.returncode == 0:
                return (True, f"Successfully connected to {ssid}")
            else:
                error_msg = result.stderr or result.stdout or "Unknown error"
                return (False, f"Failed to connect: {error_msg}")
        
        except subprocess.TimeoutExpired:
            return (False, "WiFi configuration timed out")
        except Exception as e:
            logger.error(f"Error configuring WiFi on Linux: {e}", exc_info=True)
            return (False, f"Error: {str(e)}")
    
    @staticmethod
    def test_connection() -> Tuple[bool, str]:
        """
        Test current WiFi connection.
        
        Returns:
            Tuple of (connected, message)
        """
        try:
            # Simple ping test
            result = subprocess.run(
                ["ping", "-c", "1", "8.8.8.8"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            
            if result.returncode == 0:
                return (True, "Internet connection available")
            else:
                return (False, "No internet connection")
        except Exception as e:
            return (False, f"Connection test failed: {str(e)}")
    
    @staticmethod
    def get_current_ssid() -> Optional[str]:
        """
        Get current WiFi SSID.
        
        Returns:
            SSID string or None if not connected
        """
        platform_name = WiFiService.get_platform()
        
        try:
            if platform_name == "macos":
                result = subprocess.run(
                    ["/System/Library/PrivateFrameworks/Apple80211.framework/Resources/airport", "-I"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    for line in result.stdout.split("\n"):
                        if "SSID:" in line:
                            return line.split("SSID:")[-1].strip()
            
            elif platform_name == "linux":
                result = subprocess.run(
                    ["nmcli", "-t", "-f", "active,ssid", "dev", "wifi"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    for line in result.stdout.split("\n"):
                        if line.startswith("yes:"):
                            return line.split(":")[1].strip()
        
        except Exception as e:
            logger.error(f"Error getting current SSID: {e}")
        
        return None
