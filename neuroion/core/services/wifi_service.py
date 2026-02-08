"""
WiFi configuration service.

Platform-specific WiFi configuration for macOS and Linux (Raspberry Pi).
"""
import platform
import subprocess
import logging
import os
from typing import Optional, Tuple, List, Dict

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
            def nmcli_cmd(args: List[str]) -> List[str]:
                if os.geteuid() != 0:
                    return ["sudo", "-n", "nmcli"] + args
                return ["nmcli"] + args

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
                nmcli_cmd(["radio", "wifi"]),
                capture_output=True,
                text=True,
                timeout=5,
            )
            
            if "enabled" not in result.stdout.lower():
                # Enable WiFi
                subprocess.run(
                    nmcli_cmd(["radio", "wifi", "on"]),
                    capture_output=True,
                    text=True,
                    timeout=5,
                )

            # Use connection add with explicit wifi-sec.key-mgmt to avoid
            # "802-11-wireless-security.key-mgmt: property is missing" on some NM versions
            con_name = "Neuroion-" + "".join(c if c.isalnum() or c in "-_" else "_" for c in ssid)[:32]
            subprocess.run(
                nmcli_cmd(["connection", "delete", con_name]),
                capture_output=True,
                text=True,
                timeout=5,
            )

            if password:
                result = subprocess.run(
                    nmcli_cmd([
                        "connection", "add",
                        "type", "wifi",
                        "ifname", "wlan0",
                        "con-name", con_name,
                        "ssid", ssid,
                        "wifi-sec.key-mgmt", "wpa-psk",
                        "wifi-sec.psk", password,
                    ]),
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
            else:
                result = subprocess.run(
                    nmcli_cmd([
                        "connection", "add",
                        "type", "wifi",
                        "ifname", "wlan0",
                        "con-name", con_name,
                        "ssid", ssid,
                    ]),
                    capture_output=True,
                    text=True,
                    timeout=15,
                )

            if result.returncode != 0:
                error_msg = result.stderr or result.stdout or "Unknown error"
                return (False, f"Failed to add connection: {error_msg}")

            result = subprocess.run(
                nmcli_cmd(["connection", "up", con_name]),
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
    
    @staticmethod
    def scan_wifi_networks() -> List[Dict[str, any]]:
        """
        Scan for available WiFi networks.
        
        Returns:
            List of dictionaries with keys: ssid, signal_strength, security, frequency
        """
        platform_name = WiFiService.get_platform()
        
        if platform_name == "macos":
            return WiFiService._scan_macos()
        elif platform_name == "linux":
            return WiFiService._scan_linux()
        else:
            logger.warning(f"WiFi scanning not supported on platform: {platform_name}")
            return []
    
    @staticmethod
    def _scan_macos() -> List[Dict[str, any]]:
        """Scan WiFi networks on macOS using airport command."""
        networks = []
        try:
            result = subprocess.run(
                ["/System/Library/PrivateFrameworks/Apple80211.framework/Resources/airport", "-s"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            
            if result.returncode != 0:
                logger.error(f"Failed to scan WiFi networks: {result.stderr}")
                return networks
            
            # Parse airport output
            # Format: SSID BSSID RSSI CHANNEL HT CC SECURITY (auth/unicast/group)
            lines = result.stdout.strip().split("\n")
            if len(lines) < 2:
                return networks
            
            # Skip header line
            for line in lines[1:]:
                if not line.strip():
                    continue
                
                parts = line.split()
                if len(parts) < 6:
                    continue
                
                ssid = parts[0]
                rssi = parts[2]
                channel = parts[3]
                security = " ".join(parts[5:]) if len(parts) > 5 else "Open"
                
                # Convert RSSI to signal strength percentage (rough estimate)
                try:
                    rssi_value = int(rssi)
                    # RSSI ranges from -100 (worst) to 0 (best)
                    signal_strength = max(0, min(100, 2 * (rssi_value + 100)))
                except ValueError:
                    signal_strength = 0
                
                networks.append({
                    "ssid": ssid,
                    "signal_strength": signal_strength,
                    "security": "WPA2" if "WPA2" in security else ("WPA" if "WPA" in security else "Open"),
                    "frequency": "2.4GHz" if int(channel) <= 14 else "5GHz" if channel else "Unknown",
                    "rssi": rssi_value if isinstance(rssi_value, int) else None,
                })
        
        except subprocess.TimeoutExpired:
            logger.error("WiFi scan timed out")
        except Exception as e:
            logger.error(f"Error scanning WiFi networks on macOS: {e}", exc_info=True)
        
        return networks
    
    @staticmethod
    def _scan_linux() -> List[Dict[str, any]]:
        """Scan WiFi networks on Linux using nmcli."""
        networks = []
        try:
            # Check if nmcli is available
            result = subprocess.run(
                ["which", "nmcli"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            
            if result.returncode != 0:
                logger.error("nmcli not found. Install NetworkManager: sudo apt-get install network-manager")
                return networks
            
            # Enable WiFi if needed
            subprocess.run(
                ["nmcli", "radio", "wifi", "on"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            
            # Scan for networks
            result = subprocess.run(
                ["nmcli", "device", "wifi", "rescan"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            
            # Get list of networks
            result = subprocess.run(
                ["nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY,FREQ", "device", "wifi", "list"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            
            if result.returncode != 0:
                logger.error(f"Failed to list WiFi networks: {result.stderr}")
                return networks
            
            # Parse nmcli output (tab-separated)
            for line in result.stdout.strip().split("\n"):
                if not line.strip():
                    continue
                
                parts = line.split(":")
                if len(parts) < 4:
                    continue
                
                ssid = parts[0] if parts[0] else "Hidden Network"
                signal_str = parts[1]
                security = parts[2] if len(parts) > 2 else ""
                freq = parts[3] if len(parts) > 3 else ""
                
                # Convert signal to percentage
                try:
                    signal_strength = int(signal_str)
                except ValueError:
                    signal_strength = 0
                
                # Determine security type
                if "WPA2" in security:
                    security_type = "WPA2"
                elif "WPA" in security:
                    security_type = "WPA"
                else:
                    security_type = "Open"
                
                # Determine frequency band
                try:
                    freq_value = float(freq)
                    if freq_value < 3000:
                        frequency = "2.4GHz"
                    else:
                        frequency = "5GHz"
                except (ValueError, TypeError):
                    frequency = "Unknown"
                
                networks.append({
                    "ssid": ssid,
                    "signal_strength": signal_strength,
                    "security": security_type,
                    "frequency": frequency,
                    "rssi": None,  # nmcli doesn't provide RSSI directly
                })
        
        except subprocess.TimeoutExpired:
            logger.error("WiFi scan timed out")
        except Exception as e:
            logger.error(f"Error scanning WiFi networks on Linux: {e}", exc_info=True)
        
        return networks