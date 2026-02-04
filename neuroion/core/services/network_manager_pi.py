"""
Raspberry Pi specific network management.

Handles SoftAP and LAN mode switching on Raspberry Pi OS.
"""
import subprocess
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class RaspberryPiNetworkManager:
    """Raspberry Pi specific network operations."""
    
    WIFI_INTERFACE = "wlan0"  # Default WiFi interface on Pi
    SOFTAP_SSID = "Neuroion-Setup"
    SOFTAP_PASSWORD = "neuroion123"  # Default, should be from device label
    
    @staticmethod
    def configure_hostapd(ssid: str, password: str) -> bool:
        """Configure hostapd for SoftAP."""
        config = f"""
interface={RaspberryPiNetworkManager.WIFI_INTERFACE}
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
        config = f"""
interface={RaspberryPiNetworkManager.WIFI_INTERFACE}
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
    
    @staticmethod
    def configure_static_ip(ip: str = "192.168.4.1") -> bool:
        """Configure static IP for SoftAP interface."""
        config = f"""
interface {RaspberryPiNetworkManager.WIFI_INTERFACE}
static ip_address={ip}/24
nohook wpa_supplicant
"""
        try:
            with open("/etc/dhcpcd.conf", "a") as f:
                f.write(f"\n# Neuroion SoftAP configuration\n{config}")
            return True
        except Exception as e:
            logger.error(f"Error configuring static IP: {e}")
            return False
