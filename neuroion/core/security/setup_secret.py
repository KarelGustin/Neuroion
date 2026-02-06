"""
Per-device setup secret for AP (Wi-Fi) password.

Generated on first boot or factory reset; stored in a secure file.
Used as the SoftAP passphrase so there are no default credentials.
"""
import os
import secrets
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Default path: under user data dir so permissions can be restricted
def _secret_path() -> Path:
    path = os.environ.get("NEUROION_SETUP_SECRET_FILE")
    if path:
        return Path(path)
    data_dir = Path.home() / ".neuroion"
    return data_dir / "setup_secret"


def _ensure_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Restrict directory to owner on Unix
    try:
        os.chmod(path.parent, 0o700)
    except OSError:
        pass


def generate() -> str:
    """
    Generate a new setup secret (8–16 chars, alphanumeric for WPA passphrase).
    Writes to secure file (0o600). Overwrites existing.
    """
    # WPA2 passphrase: 8–63 ASCII; use alphanumeric for readability
    secret = "".join(secrets.choice("abcdefghjkmnpqrstuvwxyz23456789") for _ in range(12))
    path = _secret_path()
    _ensure_dir(path)
    path.write_text(secret, encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    logger.info("Setup secret generated and stored")
    return secret


def get() -> Optional[str]:
    """Read setup secret from file if it exists. Never log the value."""
    path = _secret_path()
    if not path.exists():
        return None
    try:
        return path.read_text(encoding="utf-8").strip()
    except (OSError, IOError) as e:
        logger.warning("Could not read setup secret file: %s", e)
        return None


def get_or_create() -> str:
    """Return existing setup secret or generate and store a new one."""
    existing = get()
    if existing:
        return existing
    return generate()


def clear() -> bool:
    """Remove the setup secret file (e.g. factory reset). Returns True if removed."""
    path = _secret_path()
    if path.exists():
        try:
            path.unlink()
            return True
        except OSError as e:
            logger.warning("Could not remove setup secret file: %s", e)
    return False
