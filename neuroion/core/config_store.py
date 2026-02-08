"""
Central device config and runtime state.

Single source of truth for device configuration and setup state.
All setup-related reads/writes should go through this module (or the repositories
it uses). See docs/CONFIG_SCHEMA.md for schema v1.
"""
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session

from neuroion.core.memory.repository import (
    SystemConfigRepository,
    DeviceConfigRepository,
)


def get_device_config(db: Session) -> Dict[str, Any]:
    """
    Return the full device config and runtime state as a single dict.
    Keys: device_name (hostname), timezone, wifi_configured, setup_completed,
    hostname, retention_policy, wifi (ssid only, no password), llm_provider,
    llm_ollama, llm_cloud, llm_openai, llm_custom (no api_key), neuroion_core, privacy.
    """
    device = DeviceConfigRepository.get_or_create(db)
    sys_all = SystemConfigRepository.get_all(db)

    # Build safe view: never include passwords or api_key in returned dict
    wifi = sys_all.get("wifi") or {}
    wifi_safe = {"ssid": wifi.get("ssid")} if wifi else {}

    llm_ollama = sys_all.get("llm_ollama") or {}
    llm_cloud = sys_all.get("llm_cloud") or {}
    llm_openai = sys_all.get("llm_openai") or {}
    llm_custom = sys_all.get("llm_custom") or {}
    llm_openai_safe = {k: v for k, v in llm_openai.items() if k != "api_key"}
    llm_custom_safe = {k: v for k, v in llm_custom.items() if k != "api_key"}

    neuroion_core = sys_all.get("neuroion_core")

    return {
        "device_name": device.hostname or "Neuroion Core",
        "hostname": device.hostname or "neuroion",
        "timezone": sys_all.get("timezone") or "Europe/Amsterdam",
        "wifi_configured": device.wifi_configured,
        "setup_completed": device.setup_completed,
        "retention_policy": device.retention_policy,
        "wifi": wifi_safe,
        "llm_provider": sys_all.get("llm_provider"),
        "llm_ollama": llm_ollama,
        "llm_cloud": {k: v for k, v in llm_cloud.items() if k != "api_key"},
        "llm_openai": llm_openai_safe,
        "llm_custom": llm_custom_safe,
        "neuroion_core": neuroion_core,
        "privacy": sys_all.get("privacy"),
    }


def get_neuroion_core_config(db: Session) -> Optional[Dict[str, Any]]:
    """Get Neuroion Core (agent/gateway) config. Returns None if not set."""
    raw = SystemConfigRepository.get(db, "neuroion_core")
    if not raw or not raw.value:
        return None
    import json
    try:
        return json.loads(raw.value) if isinstance(raw.value, str) else raw.value
    except (json.JSONDecodeError, TypeError):
        return None


def set_neuroion_core_config(db: Session, payload: Dict[str, Any]) -> None:
    """Store Neuroion Core config (gateway, ui, models, etc.)."""
    SystemConfigRepository.set(db, "neuroion_core", payload, category="agent")


def get_wifi_config(db: Session) -> Optional[Dict[str, Any]]:
    """Get stored WiFi config (ssid + password). Caller must not log or expose password."""
    raw = SystemConfigRepository.get(db, "wifi")
    if not raw or not raw.value:
        return None
    import json
    try:
        return json.loads(raw.value)
    except (json.JSONDecodeError, TypeError):
        return None


def set_wifi(db: Session, ssid: str, password: str) -> None:
    """Store WiFi credentials. Does not apply to the system; use WiFiService for that."""
    SystemConfigRepository.set(
        db, "wifi", {"ssid": ssid, "password": password}, category="wifi"
    )


def set_device(db: Session, device_name: Optional[str] = None, timezone: Optional[str] = None) -> None:
    """Update device name (hostname) and/or timezone."""
    if device_name is not None:
        DeviceConfigRepository.update(db, hostname=device_name)
    if timezone is not None:
        SystemConfigRepository.set(db, "timezone", timezone, category="device")


def set_privacy(db: Session, telemetry: Optional[bool] = None, updates_check: Optional[bool] = None) -> None:
    """Store privacy toggles."""
    raw = SystemConfigRepository.get(db, "privacy")
    import json
    current = {}
    if raw and raw.value:
        try:
            current = json.loads(raw.value)
        except (json.JSONDecodeError, TypeError):
            pass
    if telemetry is not None:
        current["telemetry"] = telemetry
    if updates_check is not None:
        current["updates_check"] = updates_check
    if current:
        SystemConfigRepository.set(db, "privacy", current, category="privacy")


def set_setup_completed(db: Session, completed: bool = True) -> None:
    """Mark setup as completed or not."""
    DeviceConfigRepository.update(db, setup_completed=completed)


def set_wifi_configured(db: Session, configured: bool) -> None:
    """Mark WiFi as configured (e.g. after successful connect)."""
    DeviceConfigRepository.update(db, wifi_configured=configured)


def is_setup_complete(db: Session) -> bool:
    """True if device has been marked as setup completed. For full step check use setup API."""
    device = DeviceConfigRepository.get_or_create(db)
    return bool(device.setup_completed)
