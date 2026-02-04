"""
Network mode management abstraction.

Provides platform-agnostic interface for managing SoftAP and LAN modes.
"""
import platform
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class NetworkManager:
    """Manages network modes: SoftAP (setup) and LAN (normal)."""
    
    @staticmethod
    def get_platform() -> str:
        """Get current platform."""
        system = platform.system().lower()
        if system == "darwin":
            return "macos"
        elif system == "linux":
            # Try to detect if it's Raspberry Pi or Jetson
            try:
                with open("/proc/device-tree/model", "r") as f:
                    model = f.read().lower()
                    if "raspberry" in model:
                        return "raspberry_pi"
                    elif "jetson" in model:
                        return "jetson"
            except Exception:
                pass
            return "linux"
        else:
            return "unknown"
    
    @staticmethod
    def get_current_mode() -> str:
        """
        Get current network mode.
        
        Returns:
            "setup" if SoftAP is active, "lan" if WiFi/LAN is active, "unknown" otherwise
        """
        platform_name = NetworkManager.get_platform()
        
        if platform_name == "macos":
            # On macOS, assume LAN mode (no SoftAP support for demo)
            return "lan"
        elif platform_name in ["raspberry_pi", "jetson", "linux"]:
            # Check if hostapd is running (SoftAP active)
            import subprocess
            try:
                result = subprocess.run(
                    ["systemctl", "is-active", "hostapd"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0 and "active" in result.stdout:
                    return "setup"
                else:
                    return "lan"
            except Exception:
                return "unknown"
        else:
            return "unknown"
    
    @staticmethod
    def start_softap() -> bool:
        """
        Start SoftAP mode with SSID 'Neuroion-Setup'.
        
        Returns:
            True if successful, False otherwise
        """
        platform_name = NetworkManager.get_platform()
        
        if platform_name == "macos":
            logger.warning("SoftAP not supported on macOS (demo mode)")
            return False
        elif platform_name in ["raspberry_pi", "jetson", "linux"]:
            import subprocess
            try:
                # Start setup mode service
                result = subprocess.run(
                    ["systemctl", "start", "neuroion-setup-mode"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                return result.returncode == 0
            except Exception as e:
                logger.error(f"Error starting SoftAP: {e}", exc_info=True)
                return False
        else:
            logger.warning(f"SoftAP not supported on platform: {platform_name}")
            return False
    
    @staticmethod
    def stop_softap() -> bool:
        """
        Stop SoftAP and switch to LAN mode.
        
        Returns:
            True if successful, False otherwise
        """
        platform_name = NetworkManager.get_platform()
        
        if platform_name == "macos":
            return True  # No-op on macOS
        elif platform_name in ["raspberry_pi", "jetson", "linux"]:
            import subprocess
            try:
                # Stop setup mode, start normal mode
                subprocess.run(
                    ["systemctl", "stop", "neuroion-setup-mode"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                subprocess.run(
                    ["systemctl", "start", "neuroion-normal-mode"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                return True
            except Exception as e:
                logger.error(f"Error stopping SoftAP: {e}", exc_info=True)
                return False
        else:
            return False
    
    @staticmethod
    def get_lan_ip() -> Optional[str]:
        """
        Get current LAN IP address.
        
        Returns:
            IP address string or None if not available
        """
        import socket
        try:
            # Connect to a remote address to determine local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            # Fallback: try to get IP from network interfaces
            import subprocess
            try:
                if platform.system() == "Linux":
                    result = subprocess.run(
                        ["hostname", "-I"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    if result.returncode == 0:
                        ips = result.stdout.strip().split()
                        # Return first non-loopback IP
                        for ip in ips:
                            if not ip.startswith("127."):
                                return ip
                elif platform.system() == "Darwin":
                    result = subprocess.run(
                        ["ipconfig", "getifaddr", "en0"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    if result.returncode == 0:
                        return result.stdout.strip()
            except Exception:
                pass
        return None
    
    @staticmethod
    def get_hostname() -> str:
        """
        Get device hostname.
        
        Returns:
            Hostname string (default: "neuroion.local")
        """
        try:
            import socket
            hostname = socket.gethostname()
            # Ensure .local suffix for mDNS
            if not hostname.endswith(".local"):
                hostname = f"{hostname}.local"
            return hostname
        except Exception:
            return "neuroion.local"
    
    @staticmethod
    def is_wifi_configured() -> bool:
        """
        Check if WiFi is configured.
        
        Returns:
            True if WiFi is configured, False otherwise
        """
        # This will be checked via DeviceConfig in the API
        # For now, check if we can get a LAN IP
        ip = NetworkManager.get_lan_ip()
        return ip is not None and not ip.startswith("192.168.4.")  # SoftAP IP range
