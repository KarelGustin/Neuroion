"""
WireGuard peer management for VPN pairing.

Calls the add-peer script to generate client config and optionally removes peers on unpair.
"""
import json
import logging
import os
import re
import subprocess
from pathlib import Path
from typing import Optional

from neuroion.core.config import settings

logger = logging.getLogger(__name__)


def add_peer(device_id: str = "") -> Optional[dict]:
    """
    Add a WireGuard peer and return client config.

    Returns dict with client_config, client_ip, client_public_key, or None if WireGuard
    is not configured or the script fails.
    """
    if not settings.wireguard_endpoint:
        logger.debug("WireGuard endpoint not set; skipping add_peer")
        return None
    script = settings.wireguard_add_peer_script
    if not script or not Path(script).exists():
        logger.warning("WireGuard add-peer script not found: %s", script)
        return None
    env = os.environ.copy()
    env["WIREGUARD_CONFIG"] = settings.wireguard_config_path
    env["WIREGUARD_ENDPOINT"] = settings.wireguard_endpoint
    env["DEVICE_ID"] = device_id or ""
    try:
        cmd = ["bash", script] if script.endswith(".sh") else [script]
        out = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=Path(script).parent if Path(script).is_file() else None,
        )
        if out.returncode != 0:
            logger.warning("WireGuard add-peer script failed: %s", out.stderr or out.stdout)
            return None
        data = json.loads(out.stdout)
        if "error" in data:
            logger.warning("WireGuard script returned error: %s", data["error"])
            return None
        return {
            "client_config": data["client_config"],
            "client_ip": data["client_ip"],
            "client_public_key": data["client_public_key"],
        }
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError) as e:
        logger.warning("WireGuard add_peer failed: %s", e)
        return None


def remove_peer(client_public_key: str) -> bool:
    """
    Remove a WireGuard peer from the running interface and from the config file.

    Returns True if removal succeeded or peer was not found; False on error.
    """
    config_path = Path(settings.wireguard_config_path)
    if not config_path.exists():
        logger.debug("WireGuard config not found; nothing to remove")
        return True
    try:
        # Remove from running interface
        subprocess.run(
            ["wg", "set", "wg0", "peer", client_public_key, "remove"],
            capture_output=True,
            timeout=10,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        logger.debug("wg set peer remove: %s", e)

    # Remove [Peer] block from config file
    try:
        text = config_path.read_text()
        block_pattern = re.compile(
            r"(^|\n)\[Peer\]\s*\nPublicKey\s*=\s*"
            + re.escape(client_public_key)
            + r"\s*\nAllowedIPs\s*=.*?(?=\n\[Peer\]|\n\[Interface\]|\Z)",
            re.DOTALL | re.MULTILINE,
        )
        def replace_block(m):
            return "\n" if m.group(1) == "\n" else ""
        new_text = block_pattern.sub(replace_block, text)
        if new_text != text:
            config_path.write_text(new_text)
            logger.info("Removed VPN peer %s from config", client_public_key[:16] + "...")
        return True
    except OSError as e:
        logger.warning("Could not update WireGuard config: %s", e)
        return False
