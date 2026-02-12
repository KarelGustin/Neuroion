"""
Setup endpoints for initial Homebase configuration.

Handles WiFi configuration, LLM provider setup, and household initialization.
"""
import logging
import time
import os
import json
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)

from neuroion.core.memory.db import get_db, db_session
from starlette.concurrency import run_in_threadpool
from neuroion.core.memory.repository import (
    SystemConfigRepository,
    HouseholdRepository,
    UserRepository,
    DeviceConfigRepository,
    ContextSnapshotRepository,
)
from neuroion.core.config_store import (
    set_wifi as config_store_set_wifi,
    set_setup_completed as config_store_set_setup_completed,
    set_device as config_store_set_device,
    get_wifi_config as config_store_get_wifi_config,
    set_wifi_configured as config_store_set_wifi_configured,
    get_device_config as config_store_get_device_config,
    get_neuroion_core_config as config_store_get_neuroion_core_config,
    set_neuroion_core_config as config_store_set_neuroion_core_config,
)
from neuroion.core.llm import get_llm_client_from_config
from neuroion.core.llm.ollama import OllamaClient
from neuroion.core.llm.cloud import CloudLLMClient
from neuroion.core.llm.openai import OpenAILLMClient
from neuroion.core.services.wifi_service import WiFiService
from neuroion.core.services.network_manager import NetworkManager
from neuroion.core.security.setup_secret import get_or_create as get_setup_secret, clear as setup_secret_clear
from neuroion.core.memory.models import (
    JoinToken,
    LoginCode,
    DashboardLink,
    DailyRequestCount,
    CronJobRecord,
    CronRunRecord,
    UserIntegration,
    Preference,
    ContextSnapshot,
    AuditLog,
    ChatMessage,
    Household,
    SystemConfig,
)
from neuroion.core.config import settings as app_settings
from neuroion.core.services.network import get_dashboard_base_url

router = APIRouter(prefix="/setup", tags=["setup"])
status_router = APIRouter(prefix="/api", tags=["status"])


def _deep_merge_dict(base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
    """Merge nested dicts (update overrides base)."""
    result = dict(base or {})
    for key, value in (update or {}).items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge_dict(result[key], value)
        else:
            result[key] = value
    return result

# Track startup time for uptime calculation
_startup_time = time.time()


# Request/Response Models

class SetupStatusResponse(BaseModel):
    """Setup status response."""
    is_complete: bool
    steps: Dict[str, bool]  # wifi, llm, household
    message: str
    reset_at: Optional[str] = None


class DevStatusResponse(BaseModel):
    """Dev startup status response (sequenced dev launcher)."""
    progress: int
    stage: str
    updated_at: Optional[str] = None


class WiFiConfigRequest(BaseModel):
    """WiFi configuration request."""
    ssid: str
    password: str


class WiFiConfigResponse(BaseModel):
    """WiFi configuration response."""
    success: bool
    message: str


class WiFiApplyResponse(BaseModel):
    """WiFi apply (connect + switch to LAN) response."""
    success: bool
    message: str


class LLMConfigRequest(BaseModel):
    """LLM configuration request."""
    provider: str  # local, cloud, openai, custom
    config: Dict[str, Any]  # Provider-specific config


class LLMConfigResponse(BaseModel):
    """LLM configuration response."""
    success: bool
    message: str
    test_result: Optional[str] = None


class HouseholdSetupRequest(BaseModel):
    """Household setup request."""
    household_name: str
    owner_name: str


class HouseholdSetupResponse(BaseModel):
    """Household setup response."""
    success: bool
    household_id: int
    user_id: int
    message: str


class SetupCompleteResponse(BaseModel):
    """Setup completion check response."""
    is_complete: bool
    missing_steps: list[str]


class WiFiNetwork(BaseModel):
    """WiFi network information."""
    ssid: str
    signal_strength: int  # 0-100
    security: str  # WPA2, WPA, Open
    frequency: str  # 2.4GHz, 5GHz, Unknown
    rssi: Optional[int] = None


class WiFiScanResponse(BaseModel):
    """WiFi scan response."""
    networks: List[WiFiNetwork]


class InternetCheckResponse(BaseModel):
    """Internet connectivity check response."""
    connected: bool
    message: str


class OwnerSetupRequest(BaseModel):
    """Owner profile setup request."""
    name: str
    language: str = "nl"
    timezone: str = "Europe/Amsterdam"
    style_prefs: Optional[Dict[str, Any]] = None
    preferences: Optional[Dict[str, Any]] = None
    consent: Optional[Dict[str, Any]] = None


class OwnerSetupResponse(BaseModel):
    """Owner setup response."""
    success: bool
    member_id: int
    message: str


class OwnerContextRequest(BaseModel):
    """Save initial context for the owner (for Neuroion Agent ion)."""
    summary: str


class OwnerContextResponse(BaseModel):
    """Response after saving owner context."""
    success: bool
    message: str


class ModelPresetRequest(BaseModel):
    """LLM model choice: local (free), openai (own key), custom (OpenAI-compatible), or neuroion_agent (unavailable)."""
    choice: str  # "local" | "openai" | "custom" | "neuroion_agent"
    model_name: Optional[str] = None  # Optional override for local model
    api_key: Optional[str] = None  # Required when choice is "custom"
    base_url: Optional[str] = None  # Optional for custom (default OpenAI)
    model: Optional[str] = None  # Optional for custom (default gpt-3.5-turbo)


class ModelPresetResponse(BaseModel):
    """Model choice response."""
    success: bool
    choice: str
    model_name: str
    message: str


class DeviceConfigResponse(BaseModel):
    """Device configuration response."""
    wifi_configured: bool
    hostname: str
    setup_completed: bool
    retention_policy: Optional[Dict[str, Any]] = None


class StatusResponse(BaseModel):
    """System status response."""
    network: Dict[str, Any]
    model: Dict[str, Any]
    uptime: int
    household: Dict[str, Any]
    degraded_message: Optional[str] = None  # e.g. "Low memory; responses may be slow."
    storage: Optional[Dict[str, Any]] = None  # free_gb, total_gb
    agent: Optional[Dict[str, Any]] = None  # name "Neuroion Agent", status running/stopped
    dashboard_url: Optional[str] = None  # base URL for dashboard UI (e.g. http://host:3001)
    setup_ui_url: Optional[str] = None  # URL for setup wizard (QR on kiosk; e.g. http://10.42.0.1:3000)
    telegram_connected: Optional[bool] = None  # True if Telegram bot token is configured
    agent_running: Optional[bool] = None  # True if Neuroion Agent (Neuroion) is running
    neuroion_ui_url: Optional[str] = None  # URL for Neuroion Control UI


class SetupSecretResponse(BaseModel):
    """One-time setup secret (AP password). Shown on kiosk or sticker."""
    setup_secret: str


class TelegramInfoResponse(BaseModel):
    """Telegram bot info for onboarding display."""
    bot_username: Optional[str] = None
    connected: bool


class NeuroionGatewayRequest(BaseModel):
    """Neuroion gateway basics."""
    port: int = 3141
    bind: str = "lan"
    token: str


class NeuroionWorkspaceRequest(BaseModel):
    """Neuroion workspace settings."""
    workspace: str


class NeuroionChannelsRequest(BaseModel):
    """Neuroion channel settings (Telegram only)."""
    enabled: bool = True
    dm_policy: str = "pairing"


class NeuroionSetupResponse(BaseModel):
    """Neuroion setup response."""
    success: bool
    message: str


class DeviceSetupRequest(BaseModel):
    """Device name and timezone."""
    device_name: str
    timezone: str = "Europe/Amsterdam"


class DeviceSetupResponse(BaseModel):
    """Device setup response."""
    success: bool
    message: str


class AgentNameRequest(BaseModel):
    """Agent name for setup."""
    name: str = "ion"


class AgentNameResponse(BaseModel):
    """Agent name setup response."""
    success: bool
    message: str


class ValidateResponse(BaseModel):
    """Setup validation result."""
    network_ok: bool
    model_ok: bool
    error: Optional[str] = None


class FactoryResetResponse(BaseModel):
    """Factory reset response."""
    success: bool
    message: str


class SetupSummaryMember(BaseModel):
    """Member in setup summary."""
    name: str
    role: str


class SetupSummaryResponse(BaseModel):
    """Onboarding/setup summary for Core dashboard overview."""
    device_name: str
    timezone: str
    wifi_ssid: Optional[str] = None
    wifi_configured: bool
    household_name: str
    members: List[SetupSummaryMember]
    llm_preset: str
    llm_model: str
    retention_policy: Optional[Dict[str, Any]] = None


# Endpoints

@router.get("/setup-secret", response_model=SetupSecretResponse)
def get_setup_secret_for_display() -> SetupSecretResponse:
    """
    Return the per-device setup secret (AP Wi-Fi password) for one-time display on kiosk or label.
    Never log this value.
    """
    secret = get_setup_secret()
    return SetupSecretResponse(setup_secret=secret)


@router.get("/telegram-info", response_model=TelegramInfoResponse)
def get_telegram_info() -> TelegramInfoResponse:
    """
    Return Telegram bot info for onboarding display (no secrets).
    """
    bot_username = getattr(app_settings, "telegram_bot_username", None)
    bot_token = getattr(app_settings, "telegram_bot_token", None)
    return TelegramInfoResponse(
        bot_username=bot_username,
        connected=bool(bot_token),
    )


@router.post("/neuroion/gateway", response_model=NeuroionSetupResponse)
def setup_neuroion_gateway(
    request: NeuroionGatewayRequest,
    db: Session = Depends(get_db),
) -> NeuroionSetupResponse:
    """Store Neuroion gateway basics in neuroion_core config."""
    try:
        core = config_store_get_neuroion_core_config(db) or {}
        gateway = core.get("gateway") if isinstance(core.get("gateway"), dict) else {}
        gateway_update = {
            "port": request.port,
            "bind": request.bind,
            "auth": {"mode": "token", "token": request.token},
        }
        core = _deep_merge_dict(core, {"gateway": _deep_merge_dict(gateway, gateway_update)})
        config_store_set_neuroion_core_config(db, core)
        return NeuroionSetupResponse(success=True, message="Gateway saved")
    except Exception as e:
        logger.error("Failed to save Neuroion gateway: %s", e, exc_info=True)
        return NeuroionSetupResponse(success=False, message=str(e))


@router.post("/neuroion/workspace", response_model=NeuroionSetupResponse)
def setup_neuroion_workspace(
    request: NeuroionWorkspaceRequest,
    db: Session = Depends(get_db),
) -> NeuroionSetupResponse:
    """Store Neuroion workspace path in neuroion_core config."""
    try:
        core = config_store_get_neuroion_core_config(db) or {}
        agents = core.get("agents") if isinstance(core.get("agents"), dict) else {}
        defaults = agents.get("defaults") if isinstance(agents.get("defaults"), dict) else {}
        defaults["workspace"] = request.workspace
        agents["defaults"] = defaults
        core = _deep_merge_dict(core, {"agents": agents})
        config_store_set_neuroion_core_config(db, core)
        return NeuroionSetupResponse(success=True, message="Workspace saved")
    except Exception as e:
        logger.error("Failed to save Neuroion workspace: %s", e, exc_info=True)
        return NeuroionSetupResponse(success=False, message=str(e))


@router.post("/neuroion/channels", response_model=NeuroionSetupResponse)
def setup_neuroion_channels(
    request: NeuroionChannelsRequest,
    db: Session = Depends(get_db),
) -> NeuroionSetupResponse:
    """Store Neuroion channel config (Telegram only)."""
    try:
        core = config_store_get_neuroion_core_config(db) or {}
        channels = core.get("channels") if isinstance(core.get("channels"), dict) else {}
        if request.enabled:
            channels["telegram"] = {"dmPolicy": request.dm_policy}
        else:
            channels.pop("telegram", None)
        core = _deep_merge_dict(core, {"channels": channels})
        config_store_set_neuroion_core_config(db, core)
        return NeuroionSetupResponse(success=True, message="Channels saved")
    except Exception as e:
        logger.error("Failed to save Neuroion channels: %s", e, exc_info=True)
        return NeuroionSetupResponse(success=False, message=str(e))


def _ensure_default_llm_config(db: Session) -> None:
    """If no LLM config exists, write default (local Ollama qwen2:7b-instruct) so setup can complete without LLM step."""
    llm_provider = SystemConfigRepository.get(db, "llm_provider")
    if llm_provider is not None:
        return
    SystemConfigRepository.set(
        db,
        "llm_provider",
        {"provider": "local"},
        category="llm",
    )
    SystemConfigRepository.set(
        db,
        "llm_ollama",
        {
            "base_url": app_settings.ollama_url,
            "model": app_settings.ollama_model,
            "timeout": app_settings.ollama_timeout,
        },
        category="llm",
    )
    db.commit()


def _ensure_default_gateway_config(db: Session) -> None:
    """If no Neuroion gateway config exists, write default (port 3141, bind 0.0.0.0) so setup can complete without gateway step."""
    core = config_store_get_neuroion_core_config(db)
    if core and isinstance(core.get("gateway"), dict):
        return
    gateway_defaults = {
        "gateway": {
            "port": 3141,
            "bind": "0.0.0.0",
            "auth": {"mode": "token", "token": ""},
        },
    }
    core = _deep_merge_dict(core or {}, gateway_defaults)
    config_store_set_neuroion_core_config(db, core)
    db.commit()


@router.get("/status", response_model=SetupStatusResponse)
def get_setup_status(db: Session = Depends(get_db)) -> SetupStatusResponse:
    """
    Check if system is fully configured.
    
    Returns status of WiFi, LLM, and household setup.
    If no LLM config exists, default (local Ollama qwen2:7b-instruct) is written so setup can complete without the LLM step.
    """
    # Check WiFi config
    wifi_config = SystemConfigRepository.get(db, "wifi")
    wifi_configured = wifi_config is not None

    # Ensure default LLM config when missing (local Ollama qwen2:7b-instruct)
    _ensure_default_llm_config(db)

    # Check LLM config (now at least default exists)
    llm_provider = SystemConfigRepository.get(db, "llm_provider")
    llm_configured = llm_provider is not None

    # Check household
    households = HouseholdRepository.get_all(db)
    household_configured = len(households) > 0

    # WiFi is optional - system can work offline
    is_complete = llm_configured and household_configured
    
    steps = {
        "wifi": wifi_configured,
        "llm": llm_configured,
        "household": household_configured,
    }
    
    if is_complete:
        message = "Setup complete"
    else:
        missing = [step for step, done in steps.items() if not done]
        message = f"Setup incomplete. Missing: {', '.join(missing)}"
    
    reset_at = None
    try:
        reset_cfg = SystemConfigRepository.get(db, "setup_reset_at")
        if reset_cfg and isinstance(reset_cfg.value, str):
            reset_at = reset_cfg.value
    except Exception:
        pass

    return SetupStatusResponse(
        is_complete=is_complete,
        steps=steps,
        message=message,
        reset_at=reset_at,
    )


@router.get("/dev-status", response_model=DevStatusResponse)
def get_dev_status() -> DevStatusResponse:
    """
    Dev-only startup progress for sequenced npm run dev.
    Reads progress from NEUROION_DEV_STATUS_PATH (defaults to /tmp/neuroion-dev-status.json).
    """
    status_path = os.environ.get("NEUROION_DEV_STATUS_PATH", "/tmp/neuroion-dev-status.json")
    try:
        if os.path.exists(status_path):
            with open(status_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            progress = int(data.get("progress", 0))
            stage = str(data.get("stage", "starting"))
            updated_at = data.get("updated_at")
            return DevStatusResponse(progress=progress, stage=stage, updated_at=updated_at)
    except Exception as e:
        logger.debug("Failed to read dev status file: %s", e)
    return DevStatusResponse(progress=0, stage="starting", updated_at=None)


@router.get("/internet/check", response_model=InternetCheckResponse)
def check_internet_connection() -> InternetCheckResponse:
    """
    Check if device has internet connectivity.
    
    Uses WiFiService.test_connection() to ping 8.8.8.8.
    """
    try:
        connected, message = WiFiService.test_connection()
        return InternetCheckResponse(
            connected=connected,
            message=message,
        )
    except Exception as e:
        logger.error(f"Error checking internet connection: {e}", exc_info=True)
        return InternetCheckResponse(
            connected=False,
            message=f"Connection check failed: {str(e)}",
        )


@router.get("/wifi/scan", response_model=WiFiScanResponse)
def scan_wifi_networks() -> WiFiScanResponse:
    """
    Scan for available WiFi networks.
    
    Returns list of available networks with signal strength and security info.
    """
    try:
        networks_data = WiFiService.scan_wifi_networks()
        networks = [
            WiFiNetwork(
                ssid=net.get("ssid", ""),
                signal_strength=net.get("signal_strength", 0),
                security=net.get("security", "Unknown"),
                frequency=net.get("frequency", "Unknown"),
                rssi=net.get("rssi"),
            )
            for net in networks_data
        ]
        return WiFiScanResponse(networks=networks)
    except Exception as e:
        logger.error(f"Error scanning WiFi networks: {e}", exc_info=True)
        return WiFiScanResponse(networks=[])


@router.post("/wifi", response_model=WiFiConfigResponse)
def configure_wifi(
    request: WiFiConfigRequest,
    db: Session = Depends(get_db),
) -> WiFiConfigResponse:
    """
    Configure WiFi settings.
    
    Stores WiFi credentials in SystemConfig. Actual WiFi connection
    is handled by WiFiService (platform-specific).
    """
    try:
        # Store WiFi config via config_store (single source of truth)
        config_store_set_wifi(db, request.ssid, request.password)

        return WiFiConfigResponse(
            success=True,
            message="WiFi configuration saved successfully",
        )
    except Exception as e:
        logger.error(f"Error configuring WiFi: {e}", exc_info=True)
        try:
            db.rollback()
        except Exception:
            pass  # Ignore rollback errors
        return WiFiConfigResponse(
            success=False,
            message=f"Failed to configure WiFi: {str(e)}",
        )


@router.post("/wifi/apply", response_model=WiFiApplyResponse)
def apply_wifi(db: Session = Depends(get_db)) -> WiFiApplyResponse:
    """
    Apply stored WiFi credentials: connect via WiFiService, then switch to normal mode.
    On failure returns 4xx and stays in AP mode (rollback).
    """
    wifi = config_store_get_wifi_config(db)
    if not wifi or not wifi.get("ssid"):
        return WiFiApplyResponse(
            success=False,
            message="No WiFi configuration saved. Complete the WiFi step first.",
        )
    ssid = wifi.get("ssid", "")
    password = wifi.get("password", "")
    success, message = WiFiService.configure_wifi(ssid, password)
    if not success:
        return WiFiApplyResponse(success=False, message=message or "Could not join network.")
    try:
        config_store_set_wifi_configured(db, True)
        NetworkManager.stop_softap()
    except Exception as e:
        logger.warning("Could not switch to normal mode after WiFi connect: %s", e)
    return WiFiApplyResponse(success=True, message=message or "Connected and switched to normal mode.")


@router.post("/llm", response_model=LLMConfigResponse)
def configure_llm(
    request: LLMConfigRequest,
    db: Session = Depends(get_db),
) -> LLMConfigResponse:
    """
    Configure LLM provider.
    
    Supports:
    - local: Ollama (default)
    - cloud: Free HuggingFace API
    - custom: OpenAI-compatible APIs
    """
    try:
        # Validate provider
        if request.provider not in ["local", "cloud", "openai", "custom"]:
            raise ValueError(f"Invalid provider: {request.provider}")
        
        # Store provider selection
        SystemConfigRepository.set(
            db=db,
            key="llm_provider",
            value={"provider": request.provider},
            category="llm",
        )
        
        # Store provider-specific config
        if request.provider == "local":
            config = {
                "base_url": request.config.get("base_url"),
                "model": request.config.get("model", "qwen2:7b-instruct"),
                "timeout": request.config.get("timeout", 120),
            }
            SystemConfigRepository.set(
                db=db,
                key="llm_ollama",
                value=config,
                category="llm",
            )
        
        elif request.provider == "openai":
            api_key = request.config.get("api_key", "")
            if not api_key:
                raise ValueError("OpenAI provider requires API key")

            config = {
                "api_key": api_key,
                "base_url": request.config.get("base_url", "https://api.openai.com/v1"),
                "model": request.config.get("model", "gpt-4o-mini"),
                "timeout": request.config.get("timeout", 120),
            }
            SystemConfigRepository.set(
                db=db,
                key="llm_openai",
                value=config,
                category="llm",
            )

        elif request.provider == "cloud":
            config = {
                "model": request.config.get("model", "mistralai/Mixtral-8x7B-Instruct-v0.1"),
                "api_key": request.config.get("api_key"),
                "base_url": request.config.get("base_url"),
                "timeout": request.config.get("timeout", 120),
            }
            SystemConfigRepository.set(
                db=db,
                key="llm_cloud",
                value=config,
                category="llm",
            )
        
        elif request.provider == "custom":
            api_key = request.config.get("api_key", "")
            if not api_key:
                raise ValueError("Custom LLM provider requires API key")
            
            config = {
                "api_key": api_key,
                "base_url": request.config.get("base_url", "https://api.openai.com/v1"),
                "model": request.config.get("model", "gpt-4o-mini"),
                "timeout": request.config.get("timeout", 120),
            }
            SystemConfigRepository.set(
                db=db,
                key="llm_custom",
                value=config,
                category="llm",
            )
        
        # Test LLM connection (never return or log API keys)
        test_result = None
        try:
            llm_client = get_llm_client_from_config(db)
            test_messages = [{"role": "user", "content": "Hello"}]
            test_response = llm_client.chat(test_messages, temperature=0.7, max_tokens=10)
            test_result = f"Connection successful. Test response: {test_response[:50]}..."
        except Exception as test_error:
            test_result = f"Connection test failed: {str(test_error)}"

        # Restart Neuroion Agent (Neuroion) if setup is complete
        try:
            from neuroion.core.services import neuroion_adapter
            if neuroion_adapter.is_available():
                device = config_store_get_device_config(db)
                if device.get("setup_completed"):
                    from pathlib import Path
                    state_dir = Path(app_settings.database_path).parent / "neuroion"
                    neuroion_adapter.write_config(device, state_dir)
                    env_extra = neuroion_adapter.build_env_extra_from_db(db)
                    neuroion_adapter.stop()
                    neuroion_adapter.start(config_dir=state_dir, env_extra=env_extra)
        except Exception as agent_error:
            logger.warning("Could not restart Neuroion Agent after LLM change: %s", agent_error)

        # Response must never include api_key or any secret (see CONTRIBUTING.md)
        return LLMConfigResponse(
            success=True,
            message="LLM configuration saved successfully",
            test_result=test_result,
        )
    except Exception as e:
        return LLMConfigResponse(
            success=False,
            message=f"Failed to configure LLM: {str(e)}",
        )


@router.post("/household", response_model=HouseholdSetupResponse)
def setup_household(
    request: HouseholdSetupRequest,
    db: Session = Depends(get_db),
) -> HouseholdSetupResponse:
    """
    Create household and first user (owner).
    
    This is typically called during initial setup.
    """
    try:
        # Check if household already exists
        existing_households = HouseholdRepository.get_all(db)
        if existing_households:
            # Use existing household
            household = existing_households[0]
            # Check if owner user exists
            users = UserRepository.get_by_household(db, household.id)
            owner = next((u for u in users if u.role == "owner"), None)
            
            if owner:
                return HouseholdSetupResponse(
                    success=True,
                    household_id=household.id,
                    user_id=owner.id,
                    message="Household already exists",
                )
            else:
                # Create owner user
                owner = UserRepository.create(
                    db=db,
                    household_id=household.id,
                    name=request.owner_name,
                    role="owner",
                )
                return HouseholdSetupResponse(
                    success=True,
                    household_id=household.id,
                    user_id=owner.id,
                    message="Owner user created for existing household",
                )
        
        # Create new household
        household = HouseholdRepository.create(db=db, name=request.household_name)
        
        # Create owner user
        owner = UserRepository.create(
            db=db,
            household_id=household.id,
            name=request.owner_name,
            role="owner",
        )
        
        return HouseholdSetupResponse(
            success=True,
            household_id=household.id,
            user_id=owner.id,
            message="Household and owner created successfully",
        )
    except Exception as e:
        logger.error(f"Error setting up household: {e}", exc_info=True)
        try:
            db.rollback()
        except Exception:
            pass  # Ignore rollback errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to setup household: {str(e)}",
        )


@router.post("/complete", response_model=SetupCompleteResponse)
def mark_setup_complete(db: Session = Depends(get_db)) -> SetupCompleteResponse:
    """
    Mark setup as complete.
    
    Updates DeviceConfig to mark setup as completed.
    Ensures default gateway config when missing so the wizard can skip the gateway step.
    """
    try:
        # Mark setup complete via config_store
        config_store_set_setup_completed(db, True)

        # Ensure default gateway config when missing (so user did not have to set gateway)
        _ensure_default_gateway_config(db)

        # If WiFi credentials were provided but not yet applied, apply now so the
        # device can switch to the touchscreen dashboard after onboarding.
        wifi_apply_error = None
        try:
            device_config = DeviceConfigRepository.get_or_create(db)
            wifi_cfg = config_store_get_wifi_config(db)
            if wifi_cfg and wifi_cfg.get("ssid") and not device_config.wifi_configured:
                ssid = wifi_cfg.get("ssid", "")
                password = wifi_cfg.get("password", "")
                success = False
                message = None
                for attempt in range(1, 4):
                    success, message = WiFiService.configure_wifi(ssid, password)
                    if success:
                        break
                    wifi_apply_error = message or "Could not join network."
                    logger.warning("WiFi connect attempt %s/3 failed: %s", attempt, wifi_apply_error)
                    if attempt < 3:
                        time.sleep(2)
                if success:
                    config_store_set_wifi_configured(db, True)
                    try:
                        NetworkManager.stop_softap()
                    except Exception as e:
                        logger.warning("Could not switch to normal mode after WiFi connect: %s", e)
                else:
                    wifi_apply_error = message or "Could not join network."
        except Exception as e:
            wifi_apply_error = str(e)

        # Get setup status
        status_response = get_setup_status(db)
        
        missing_steps = []
        if not status_response.steps.get("wifi", False):
            missing_steps.append("wifi")
        if not status_response.steps.get("llm", False):
            missing_steps.append("llm")
        if not status_response.steps.get("household", False):
            missing_steps.append("household")
        if wifi_apply_error and "wifi" not in missing_steps:
            missing_steps.append("wifi")
            logger.warning("WiFi apply failed at setup completion: %s", wifi_apply_error)

        # Start Neuroion Agent (Neuroion) now that setup is complete
        try:
            from neuroion.core.services import neuroion_adapter
            if neuroion_adapter.is_available() and status_response.is_complete:
                from pathlib import Path
                device = config_store_get_device_config(db)
                state_dir = Path(app_settings.database_path).parent / "neuroion"
                neuroion_adapter.write_config(device, state_dir)
                env_extra = neuroion_adapter.build_env_extra_from_db(db)
                neuroion_adapter.stop()
                neuroion_adapter.start(config_dir=state_dir, env_extra=env_extra)
        except Exception as agent_error:
            logger.warning("Could not start Neuroion Agent after setup: %s", agent_error)
        
        return SetupCompleteResponse(
            is_complete=status_response.is_complete,
            missing_steps=missing_steps,
        )
    except Exception as e:
        logger.error(f"Error marking setup complete: {e}", exc_info=True)
        try:
            db.rollback()
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mark setup complete: {str(e)}",
        )


# All SQLite tables to wipe in one transaction (order irrelevant with foreign_keys=OFF)
_FACTORY_RESET_TABLES = (
    "join_tokens",
    "login_codes",
    "dashboard_links",
    "user_integrations",
    "daily_request_counts",
    "cron_runs",
    "cron_jobs",
    "preferences",
    "context_snapshots",
    "audit_logs",
    "chat_messages",
    "users",
    "households",
    "system_config",
    "device_config",
)


def _do_factory_reset(db: Session) -> FactoryResetResponse:
    """Run factory reset in a single DB session (call from thread; session is thread-local)."""
    try:
        # 1. Single transaction: raw SQL DELETE FROM each table (fast in SQLite)
        db.execute(text("PRAGMA foreign_keys = OFF"))
        for table in _FACTORY_RESET_TABLES:
            db.execute(text(f"DELETE FROM {table}"))
        db.execute(text("PRAGMA foreign_keys = ON"))
        db.commit()
        db.expire_all()  # clear session cache so repos see empty DB

        # 2. Re-create default device_config and reset marker so setup wizard runs
        DeviceConfigRepository.get_or_create(db)
        DeviceConfigRepository.update(
            db, setup_completed=False, wifi_configured=False, hostname="Neuroion Core"
        )
        SystemConfigRepository.set(
            db, "setup_reset_at", datetime.utcnow().isoformat(), category="setup"
        )

        # 3. Clear setup secret so a new one is generated
        setup_secret_clear()
        return FactoryResetResponse(success=True, message="Factory reset complete")
    except Exception as e:
        logger.error(f"Factory reset failed: {e}", exc_info=True)
        try:
            db.rollback()
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Factory reset failed: {str(e)}",
        )


def _run_factory_reset_sync() -> FactoryResetResponse:
    """Obtain a DB session in this thread and run factory reset (for run_in_threadpool)."""
    with db_session() as db:
        return _do_factory_reset(db)


@router.post("/factory-reset", response_model=FactoryResetResponse)
async def factory_reset() -> FactoryResetResponse:
    """
    Factory reset: empty all SQLite tables in one fast transaction, then re-create
    device_config and setup_reset_at so onboarding can start again.
    (Also handled in middleware for reliability; this route is a fallback.)
    """
    return await run_in_threadpool(_run_factory_reset_sync)


@router.get("/complete", response_model=SetupCompleteResponse)
def check_setup_complete(db: Session = Depends(get_db)) -> SetupCompleteResponse:
    """
    Check if all setup steps are complete.
    
    Returns list of missing steps if incomplete.
    """
    status_response = get_setup_status(db)
    
    missing_steps = []
    if not status_response.steps.get("wifi", False):
        missing_steps.append("wifi")
    if not status_response.steps.get("llm", False):
        missing_steps.append("llm")
    if not status_response.steps.get("household", False):
        missing_steps.append("household")
    
    return SetupCompleteResponse(
        is_complete=status_response.is_complete,
        missing_steps=missing_steps,
    )


@router.get("/device-config", response_model=DeviceConfigResponse)
def get_device_config(db: Session = Depends(get_db)) -> DeviceConfigResponse:
    """Get device configuration."""
    config = DeviceConfigRepository.get_or_create(db)
    return DeviceConfigResponse(
        wifi_configured=config.wifi_configured,
        hostname=config.hostname,
        setup_completed=config.setup_completed,
        retention_policy=config.retention_policy,
    )


@router.post("/device", response_model=DeviceSetupResponse)
def setup_device(
    request: DeviceSetupRequest,
    db: Session = Depends(get_db),
) -> DeviceSetupResponse:
    """Store device name (hostname) and timezone."""
    try:
        name = (request.device_name or "Neuroion Core").strip() or "Neuroion Core"
        config_store_set_device(db, device_name=name, timezone=request.timezone)
        # Prepare Neuroion config early (agent identity) without starting the agent yet.
        try:
            from neuroion.core.services import neuroion_adapter
            if neuroion_adapter.is_available():
                from pathlib import Path
                device = config_store_get_device_config(db)
                state_dir = Path(app_settings.database_path).parent / "neuroion"
                neuroion_adapter.write_config(device, state_dir)
        except Exception as agent_error:
            logger.warning("Could not write Neuroion config after device setup: %s", agent_error)
        return DeviceSetupResponse(success=True, message="Device settings saved")
    except Exception as e:
        logger.error(f"Error saving device settings: {e}", exc_info=True)
        return DeviceSetupResponse(success=False, message=str(e))


@router.post("/agent-name", response_model=AgentNameResponse)
def setup_agent_name(
    request: AgentNameRequest,
    db: Session = Depends(get_db),
) -> AgentNameResponse:
    """Store the Neuroion agent display name (used in prompts and SOUL context)."""
    try:
        name = (request.name or "ion").strip() or "ion"
        SystemConfigRepository.set(db, "agent_name", name, category="setup")
        return AgentNameResponse(success=True, message="Agent name saved")
    except Exception as e:
        logger.error(f"Error saving agent name: {e}", exc_info=True)
        return AgentNameResponse(success=False, message=str(e))


@router.post("/validate", response_model=ValidateResponse)
def validate_setup(db: Session = Depends(get_db)) -> ValidateResponse:
    """
    Check network (and optionally model). Used before marking setup complete.
    Does not apply WiFi; use /setup/wifi/apply for that.
    """
    network_ok = False
    model_ok = False
    error = None
    try:
        connected, msg = WiFiService.test_connection()
        network_ok = connected
        if not connected:
            error = msg or "No internet connection"
    except Exception as e:
        error = str(e)
    try:
        llm_client = get_llm_client_from_config(db)
        test_messages = [{"role": "user", "content": "test"}]
        llm_client.chat(test_messages, temperature=0.7, max_tokens=1)
        model_ok = True
    except Exception:
        if not error:
            error = "Model check failed"
    return ValidateResponse(network_ok=network_ok, model_ok=model_ok, error=error)


@router.post("/owner", response_model=OwnerSetupResponse)
def setup_owner(
    request: OwnerSetupRequest,
    db: Session = Depends(get_db),
) -> OwnerSetupResponse:
    """
    Create or update owner profile.
    
    This is called during setup to configure the owner's profile.
    """
    try:
        # Get first household (should exist after household setup)
        households = HouseholdRepository.get_all(db)
        if not households:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Household must be created first",
            )
        
        household = households[0]
        
        # Find or create owner
        users = UserRepository.get_by_household(db, household.id)
        owner = next((u for u in users if u.role == "owner"), None)
        
        if not owner:
            # Create owner
            owner = UserRepository.create(
                db=db,
                household_id=household.id,
                name=request.name,
                role="owner",
                device_type="web",
            )
        
        # Update owner profile
        owner.language = request.language
        owner.timezone = request.timezone
        if request.style_prefs:
            owner.style_prefs_json = request.style_prefs
        if request.preferences:
            owner.preferences_json = request.preferences
        if request.consent:
            owner.consent_json = request.consent
        
        db.commit()
        db.refresh(owner)
        
        return OwnerSetupResponse(
            success=True,
            member_id=owner.id,
            message="Owner profile created successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting up owner: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to setup owner: {str(e)}",
        )


@router.post("/owner-context", response_model=OwnerContextResponse)
def setup_owner_context(
    request: OwnerContextRequest,
    db: Session = Depends(get_db),
) -> OwnerContextResponse:
    """
    Save initial context for the first user (owner) for the Neuroion Agent (ion).
    Called during the personal profile wizard step. No auth required (setup phase).
    """
    try:
        households = HouseholdRepository.get_all(db)
        if not households:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Household must be created first",
            )
        users = UserRepository.get_by_household(db, households[0].id)
        owner = next((u for u in users if u.role == "owner"), None)
        if not owner:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Owner must be created first",
            )
        summary = (request.summary or "").strip()
        if not summary:
            return OwnerContextResponse(success=True, message="No context to save")
        ContextSnapshotRepository.create(
            db=db,
            household_id=households[0].id,
            event_type="note",
            summary=summary,
            context_metadata=None,
            user_id=owner.id,
        )
        return OwnerContextResponse(success=True, message="Context saved for Neuroion Agent")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving owner context: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save context: {str(e)}",
        )


@router.post("/model", response_model=ModelPresetResponse)
def setup_model_preset(
    request: ModelPresetRequest,
    db: Session = Depends(get_db),
) -> ModelPresetResponse:
    """
    Select LLM: local (free), custom (own OpenAI key), or neuroion_agent (currently unavailable).
    """
    try:
        if request.choice not in ("local", "openai", "custom", "neuroion_agent"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Invalid choice. Must be "local", "openai", "custom", or "neuroion_agent"',
            )

        if request.choice == "neuroion_agent":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Neuroion Agent subscription is currently unavailable.",
            )

        if request.choice == "local":
            model_name = request.model_name or "qwen2:7b-instruct"
            SystemConfigRepository.set(
                db=db,
                key="llm_provider",
                value={"provider": "local"},
                category="llm",
            )
            SystemConfigRepository.set(
                db=db,
                key="llm_ollama",
                value={
                    "base_url": "http://localhost:11434",
                    "model": model_name,
                    "timeout": 120,
                },
                category="llm",
            )
        elif request.choice == "openai":
            api_key = (request.api_key or "").strip()
            existing_openai = SystemConfigRepository.get(db, "llm_openai")
            existing_config = existing_openai.value if (existing_openai and isinstance(existing_openai.value, dict)) else {}
            if not api_key and not existing_config.get("api_key"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="API key is required when using your OpenAI account.",
                )
            model_name = request.model or existing_config.get("model") or "gpt-4o-mini"
            base_url = (request.base_url or "").strip() or existing_config.get("base_url") or "https://api.openai.com/v1"
            SystemConfigRepository.set(
                db=db,
                key="llm_provider",
                value={"provider": "openai"},
                category="llm",
            )
            if api_key:
                SystemConfigRepository.set(
                    db=db,
                    key="llm_openai",
                    value={
                        "api_key": api_key,
                        "base_url": base_url,
                        "model": model_name,
                        "timeout": 120,
                    },
                    category="llm",
                )
            else:
                SystemConfigRepository.set(
                    db=db,
                    key="llm_openai",
                    value={
                        "api_key": existing_config.get("api_key", ""),
                        "base_url": base_url,
                        "model": model_name,
                        "timeout": 120,
                    },
                    category="llm",
                )
        else:
            # custom: OpenAI-compatible API (or keep existing if not provided)
            api_key = (request.api_key or "").strip()
            existing_custom = SystemConfigRepository.get(db, "llm_custom")
            existing_config = existing_custom.value if (existing_custom and isinstance(existing_custom.value, dict)) else {}
            if not api_key and not existing_config.get("api_key"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="API key is required when using a custom OpenAI-compatible API.",
                )
            model_name = request.model or existing_config.get("model") or "gpt-4o-mini"
            base_url = (request.base_url or "").strip() or existing_config.get("base_url") or "https://api.openai.com/v1"
            SystemConfigRepository.set(
                db=db,
                key="llm_provider",
                value={"provider": "custom"},
                category="llm",
            )
            if api_key:
                SystemConfigRepository.set(
                    db=db,
                    key="llm_custom",
                    value={
                        "api_key": api_key,
                        "base_url": base_url,
                        "model": model_name,
                        "timeout": 120,
                    },
                    category="llm",
                )
            else:
                # Keep existing key; only update model if provided
                SystemConfigRepository.set(
                    db=db,
                    key="llm_custom",
                    value={
                        "api_key": existing_config.get("api_key", ""),
                        "base_url": base_url,
                        "model": model_name,
                        "timeout": 120,
                    },
                    category="llm",
                )

        # Test model availability (non-blocking: config is always saved)
        test_result = None
        try:
            llm_client = get_llm_client_from_config(db)
            test_messages = [{"role": "user", "content": "Hello"}]
            llm_client.chat(test_messages, temperature=0.7, max_tokens=10)
            test_result = "Model available and responding"
        except Exception as test_error:
            logger.warning(f"Model test failed: {test_error}")
            err_str = str(test_error)
            if request.choice == "local" and ("404" in err_str or "Connection" in err_str or "11434" in err_str):
                test_result = "Config opgeslagen. Ollama was niet bereikbaar – start Ollama voor lokaal model."
            else:
                test_result = f"Config opgeslagen. Test mislukt: {err_str[:80]}{'…' if len(err_str) > 80 else ''}"

        return ModelPresetResponse(
            success=True,
            choice=request.choice,
            model_name=model_name,
            message=test_result or "Configuration saved",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting up model: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to setup model: {str(e)}",
        )


@status_router.get("/setup/summary", response_model=SetupSummaryResponse)
def get_setup_summary(db: Session = Depends(get_db)) -> SetupSummaryResponse:
    """
    Get onboarding/setup summary for Core dashboard: device, network, household, model, privacy.
    Safe to display; no secrets.
    """
    device_config = DeviceConfigRepository.get_or_create(db)
    device_name = device_config.hostname or "Neuroion Core"
    timezone_config = SystemConfigRepository.get(db, "timezone")
    timezone = "Europe/Amsterdam"
    if timezone_config is not None and isinstance(timezone_config.value, str):
        timezone = timezone_config.value
    wifi_ssid = WiFiService.get_current_ssid()
    wifi_configured = device_config.wifi_configured
    household_name = "Not configured"
    members: List[SetupSummaryMember] = []
    households = HouseholdRepository.get_all(db)
    if households:
        household = households[0]
        household_name = household.name
        users = UserRepository.get_by_household(db, household.id)
        members = [SetupSummaryMember(name=u.name or "—", role=u.role or "member") for u in users]
    llm_provider_config = SystemConfigRepository.get(db, "llm_provider")
    llm_ollama_config = SystemConfigRepository.get(db, "llm_ollama")
    llm_neuroion_config = SystemConfigRepository.get(db, "llm_neuroion_agent")
    llm_openai_config = SystemConfigRepository.get(db, "llm_openai")
    llm_custom_config = SystemConfigRepository.get(db, "llm_custom")
    llm_preset = "local"
    llm_model = "qwen2:7b-instruct"
    if llm_provider_config and isinstance(llm_provider_config.value, dict):
        llm_preset = llm_provider_config.value.get("provider", "local")
        if llm_preset == "local" and llm_ollama_config and isinstance(llm_ollama_config.value, dict):
            llm_model = llm_ollama_config.value.get("model", "qwen2:7b-instruct")
        elif llm_preset == "neuroion_agent" and llm_neuroion_config and isinstance(llm_neuroion_config.value, dict):
            llm_model = llm_neuroion_config.value.get("model", "gpt-4o")
        elif llm_preset == "openai" and llm_openai_config and isinstance(llm_openai_config.value, dict):
            llm_model = llm_openai_config.value.get("model", "gpt-4o-mini")
        elif llm_preset == "custom" and llm_custom_config and isinstance(llm_custom_config.value, dict):
            llm_model = llm_custom_config.value.get("model", "gpt-4o-mini")
    retention_policy = getattr(device_config, "retention_policy", None)
    return SetupSummaryResponse(
        device_name=device_name,
        timezone=timezone,
        wifi_ssid=wifi_ssid or None,
        wifi_configured=wifi_configured,
        household_name=household_name,
        members=members,
        llm_preset=llm_preset,
        llm_model=llm_model,
        retention_policy=retention_policy,
    )


# Status endpoint (separate router for /api/status)
@status_router.get("/status", response_model=StatusResponse)
def get_status(db: Session = Depends(get_db)) -> StatusResponse:
    """
    Get system status: network, model, uptime, household.
    
    Returns comprehensive system status for dashboard and touchscreen UI.
    """
    try:
        # Get device config
        device_config = DeviceConfigRepository.get_or_create(db)
        
        # Get network info
        current_ssid = WiFiService.get_current_ssid()
        wifi_configured = device_config.wifi_configured
        
        lan_ip = NetworkManager.get_lan_ip() or "—"
        
        network_info = {
            "mode": "lan" if wifi_configured else "setup",
            "wifi_configured": wifi_configured,
            "ssid": current_ssid or "Not connected",
            "ip": lan_ip,
            "hostname": device_config.hostname or "neuroion.local",
        }
        
        # Get LLM model info
        llm_provider_config = SystemConfigRepository.get(db, "llm_provider")
        llm_ollama_config = SystemConfigRepository.get(db, "llm_ollama")
        llm_neuroion_config = SystemConfigRepository.get(db, "llm_neuroion_agent")
        llm_openai_config = SystemConfigRepository.get(db, "llm_openai")
        llm_custom_config = SystemConfigRepository.get(db, "llm_custom")
        
        model_choice = "local"
        model_name = "qwen2:7b-instruct"
        model_status = "idle"
        model_health = "unknown"
        
        if llm_provider_config and isinstance(llm_provider_config.value, dict):
            provider = llm_provider_config.value.get("provider", "local")
            model_choice = provider
            if provider == "local" and llm_ollama_config and isinstance(llm_ollama_config.value, dict):
                model_name = llm_ollama_config.value.get("model", "qwen2:7b-instruct")
            elif provider == "neuroion_agent" and llm_neuroion_config and isinstance(llm_neuroion_config.value, dict):
                model_name = llm_neuroion_config.value.get("model", "gpt-4o")
            elif provider == "openai" and llm_openai_config and isinstance(llm_openai_config.value, dict):
                model_name = llm_openai_config.value.get("model", "gpt-4o-mini")
            elif provider == "custom" and llm_custom_config and isinstance(llm_custom_config.value, dict):
                model_name = llm_custom_config.value.get("model", "gpt-4o-mini")
            
            # Test LLM health
            try:
                llm_client = get_llm_client_from_config(db)
                test_messages = [{"role": "user", "content": "test"}]
                llm_client.chat(test_messages, temperature=0.7, max_tokens=1)
                model_status = "running"
                model_health = "ok"
            except Exception:
                model_status = "idle"
                model_health = "error"
        
        model_info = {
            "choice": model_choice,
            "preset": model_choice,
            "name": model_name,
            "status": model_status,
            "health": model_health,
        }

        # Optional resource check: degraded message when memory is low
        degraded_message = None
        try:
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    if line.startswith("MemAvailable:"):
                        kb = int(line.split()[1])
                        if kb < 500 * 1024:  # < 500 MB
                            degraded_message = "Low memory; responses may be slow."
                        break
        except (FileNotFoundError, ValueError, OSError):
            pass

        # Storage (disk free)
        storage_info = None
        try:
            import shutil
            total, used, free = shutil.disk_usage("/")
            storage_info = {"free_gb": round(free / (1024**3), 1), "total_gb": round(total / (1024**3), 1)}
        except (OSError, Exception):
            pass

        # Agent (Neuroion Agent / Neuroion)
        agent_info = None
        try:
            from neuroion.core.services import neuroion_adapter
            agent_info = {"name": "Neuroion Agent", "status": "running" if neuroion_adapter.is_running() else "stopped"}
        except Exception:
            agent_info = {"name": "Neuroion Agent", "status": "stopped"}

        # Calculate uptime
        uptime_seconds = int(time.time() - _startup_time)
        
        # Get household info
        households = HouseholdRepository.get_all(db)
        household_name = "Not configured"
        member_count = 0
        
        if households:
            household = households[0]
            household_name = household.name
            members = UserRepository.get_by_household(db, household.id)
            member_count = len(members)
        
        household_info = {
            "name": household_name,
            "member_count": member_count,
        }
        
        dashboard_url = get_dashboard_base_url(app_settings.dashboard_ui_port)
        setup_ui_url = NetworkManager.get_setup_ui_base_url(
            getattr(app_settings, "setup_ui_port", 3000)
        )
        neuroion_host = lan_ip if lan_ip and lan_ip != "—" else "127.0.0.1"
        neuroion_ui_url = f"http://{neuroion_host}:3141/neuroion/"
        telegram_connected = bool(getattr(app_settings, "telegram_bot_token", None))
        agent_running = agent_info.get("status") == "running" if agent_info else False

        return StatusResponse(
            network=network_info,
            model=model_info,
            uptime=uptime_seconds,
            household=household_info,
            degraded_message=degraded_message,
            storage=storage_info,
            agent=agent_info,
            dashboard_url=dashboard_url,
            setup_ui_url=setup_ui_url,
            telegram_connected=telegram_connected,
            agent_running=agent_running,
            neuroion_ui_url=neuroion_ui_url,
        )
    except Exception as e:
        logger.error(f"Error getting status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get status: {str(e)}",
        )
