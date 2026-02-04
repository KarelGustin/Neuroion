"""
Jetson Nano specific network management.

Handles SoftAP and LAN mode switching on Jetson Nano (Ubuntu-based).
Note: Network interface may be wlan1 instead of wlan0.
"""
import subprocess
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class JetsonNetworkManager:
    """Jetson Nano specific network operations."""
    
    # Jetson may use wlan1 instead of wlan0
    WIFI_INTERFACE = "wlan1"  # May need to be detected dynamically
    SOFTAP_SSID = "Neuroion-Setup"
    SOFTAP_PASSWORD = "neuroion123"  # Default, should be from device label
    
    @staticmethod
    def detect_wifi_interface() -> Optional[str]:
        """Detect WiFi interface name on Jetson."""
        try:
            result = subprocess.run(
                ["iw", "dev"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                for line in result.stdout.split("\n"):
                    if "Interface" in line:
                        interface = line.split()[-1]
                        if interface.startswith("wlan"):
                            return interface
        except Exception:
            pass
        return JetsonNetworkManager.WIFI_INTERFACE
    
    @staticmethod
    def configure_hostapd(ssid: str, password: str) -> bool:
        """Configure hostapd for SoftAP."""
        interface = JetsonNetworkManager.detect_wifi_interface()
        config = f"""
interface={interface}
driver=nl80211
ssid={ssid}
hw_mode=g
channel=7
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase={password}
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
"""
        try:
            with open("/etc/hostapd/hostapd.conf", "w") as f:
                f.write(config)
            return True
        except Exception as e:
            logger.error(f"Error configuring hostapd: {e}")
            return False
    
    @staticmethod
    def configure_dnsmasq() -> bool:
        """Configure dnsmasq for SoftAP DHCP and DNS."""
        interface = JetsonNetworkManager.detect_wifi_interface()
        config = f"""
interface={interface}
dhcp-range=192.168.4.2,192.168.4.20,255.255.255.0,24h
dhcp-option=3,192.168.4.1
dhcp-option=6,192.168.4.1
server=8.8.8.8
address=/#/192.168.4.1
"""
        try:
            with open("/etc/dnsmasq.d/neuroion-setup.conf", "w") as f:
                f.write(config)
            return True
        except Exception as e:
            logger.error(f"Error configuring dnsmasq: {e}")
            return False
