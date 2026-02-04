"""
Captive portal management for SoftAP setup mode.

Handles DNS and HTTP redirects to guide users to the setup page.
"""
import logging
import subprocess
from typing import Optional

logger = logging.getLogger(__name__)


class CaptivePortal:
    """Manages captive portal for SoftAP setup."""
    
    SETUP_IP = "192.168.4.1"
    SETUP_URL = f"http://{SETUP_IP}/setup"
    
    @staticmethod
    def setup_dns_redirect() -> bool:
        """
        Configure dnsmasq to redirect all DNS queries to setup page.
        
        This makes any domain resolve to the setup IP, triggering
        captive portal detection on mobile devices.
        """
        try:
            dnsmasq_config = f"""
# Neuroion Captive Portal DNS Redirect
# Redirect all DNS queries to setup page
address=/#/{CaptivePortal.SETUP_IP}
"""
            
            with open("/etc/dnsmasq.d/neuroion-captive-portal.conf", "w") as f:
                f.write(dnsmasq_config)
            
            # Restart dnsmasq to apply changes
            result = subprocess.run(
                ["systemctl", "restart", "dnsmasq"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            
            if result.returncode == 0:
                logger.info("DNS redirect configured for captive portal")
                return True
            else:
                logger.error(f"Failed to restart dnsmasq: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"Error setting up DNS redirect: {e}", exc_info=True)
            return False
    
    @staticmethod
    def setup_http_redirect() -> bool:
        """
        Configure HTTP redirect to setup page.
        
        This is handled by nginx configuration (captive-portal.conf).
        Returns True if nginx config exists.
        """
        import os
        nginx_config_path = "/etc/nginx/sites-available/neuroion-captive-portal"
        
        # Check if config exists
        if os.path.exists(nginx_config_path):
            try:
                # Reload nginx
                result = subprocess.run(
                    ["systemctl", "reload", "nginx"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.returncode == 0:
                    logger.info("HTTP redirect configured for captive portal")
                    return True
            except Exception as e:
                logger.error(f"Error reloading nginx: {e}")
        
        logger.warning("Nginx captive portal config not found")
        return False
    
    @staticmethod
    def enable() -> bool:
        """
        Enable captive portal (both DNS and HTTP redirects).
        
        Returns:
            True if successful, False otherwise
        """
        dns_ok = CaptivePortal.setup_dns_redirect()
        http_ok = CaptivePortal.setup_http_redirect()
        
        return dns_ok or http_ok  # At least one should work
    
    @staticmethod
    def disable() -> bool:
        """
        Disable captive portal.
        
        Removes DNS and HTTP redirects.
        """
        try:
            # Remove DNS redirect config
            import os
            dns_config = "/etc/dnsmasq.d/neuroion-captive-portal.conf"
            if os.path.exists(dns_config):
                os.remove(dns_config)
                subprocess.run(
                    ["systemctl", "restart", "dnsmasq"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
            
            logger.info("Captive portal disabled")
            return True
        except Exception as e:
            logger.error(f"Error disabling captive portal: {e}", exc_info=True)
            return False
    
    @staticmethod
    def get_setup_url() -> str:
        """
        Get the setup page URL.
        
        Returns:
            URL string for the setup page
        """
        return CaptivePortal.SETUP_URL
