"""
Setup endpoints for initial Homebase configuration.

Handles WiFi configuration, LLM provider setup, and household initialization.
"""
import logging
import time
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

from neuroion.core.memory.db import get_db
from neuroion.core.memory.repository import (
    SystemConfigRepository,
    HouseholdRepository,
    UserRepository,
    DeviceConfigRepository,
)
from neuroion.core.config_store import (
    set_wifi as config_store_set_wifi,
    set_setup_completed as config_store_set_setup_completed,
    set_device as config_store_set_device,
    get_wifi_config as config_store_get_wifi_config,
    set_wifi_configured as config_store_set_wifi_configured,
)
from neuroion.core.llm import get_llm_client_from_config
from neuroion.core.llm.ollama import OllamaClient
from neuroion.core.llm.cloud import CloudLLMClient
from neuroion.core.llm.openai import OpenAILLMClient
from neuroion.core.services.wifi_service import WiFiService
from neuroion.core.services.network_manager import NetworkManager
from neuroion.core.security.setup_secret import get_or_create as get_setup_secret, clear as setup_secret_clear
from neuroion.core.memory.models import JoinToken, LoginCode, DashboardLink
from neuroion.core.config import settings as app_settings
from neuroion.core.services.network import get_dashboard_base_url

router = APIRouter(prefix="/setup", tags=["setup"])
status_router = APIRouter(prefix="/api", tags=["status"])

# Track startup time for uptime calculation
_startup_time = time.time()


# Request/Response Models

class SetupStatusResponse(BaseModel):
    """Setup status response."""
    is_complete: bool
    steps: Dict[str, bool]  # wifi, llm, household
    message: str


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
    provider: str  # local, cloud, custom
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


class ModelPresetRequest(BaseModel):
    """LLM model choice: local (free), neuroion_agent (unavailable), or custom (own API key)."""
    choice: str  # "local" | "neuroion_agent" | "custom"
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
    telegram_connected: Optional[bool] = None  # True if Telegram bot token is configured
    agent_running: Optional[bool] = None  # True if Neuroion Agent (OpenClaw) is running


class SetupSecretResponse(BaseModel):
    """One-time setup secret (AP password). Shown on kiosk or sticker."""
    setup_secret: str


class DeviceSetupRequest(BaseModel):
    """Device name and timezone."""
    device_name: str
    timezone: str = "Europe/Amsterdam"


class DeviceSetupResponse(BaseModel):
    """Device setup response."""
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


@router.get("/status", response_model=SetupStatusResponse)
def get_setup_status(db: Session = Depends(get_db)) -> SetupStatusResponse:
    """
    Check if system is fully configured.
    
    Returns status of WiFi, LLM, and household setup.
    """
    # Check WiFi config
    wifi_config = SystemConfigRepository.get(db, "wifi")
    wifi_configured = wifi_config is not None
    
    # Check LLM config
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
    
    return SetupStatusResponse(
        is_complete=is_complete,
        steps=steps,
        message=message,
    )


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
        if request.provider not in ["local", "cloud", "custom"]:
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
                "model": request.config.get("model", "llama3.2"),
                "timeout": request.config.get("timeout", 120),
            }
            SystemConfigRepository.set(
                db=db,
                key="llm_ollama",
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
                "model": request.config.get("model", "gpt-3.5-turbo"),
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
    """
    try:
        # Mark setup complete via config_store
        config_store_set_setup_completed(db, True)

        # Get setup status
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


@router.post("/factory-reset", response_model=FactoryResetResponse)
def factory_reset(db: Session = Depends(get_db)) -> FactoryResetResponse:
    """
    Factory reset: wipe all persisted data and return device to onboarding.
    Deletes join tokens, households (and cascade: users, preferences, chat, etc.),
    system config keys (wifi, llm, etc.), resets device_config, clears setup secret.
    """
    try:
        # 1. Delete join tokens and user-linked rows (FK to users; must go before households)
        db.query(JoinToken).delete(synchronize_session=False)
        db.query(LoginCode).delete(synchronize_session=False)
        db.query(DashboardLink).delete(synchronize_session=False)
        db.commit()
        # 2. Delete all households (cascade removes users, preferences, context_snapshots, audit_logs, chat_messages)
        households = HouseholdRepository.get_all(db)
        for h in households:
            HouseholdRepository.delete(db, h.id)
        # 3. Delete system config keys so wizard is required again
        for key in (
            "wifi", "timezone", "llm_provider", "llm_ollama", "llm_cloud", "llm_custom",
            "llm_neuroion_agent", "neuroion_core", "privacy",
        ):
            SystemConfigRepository.delete(db, key)
        # 4. Reset device config
        DeviceConfigRepository.update(
            db, setup_completed=False, wifi_configured=False, hostname="Neuroion Core"
        )
        db.commit()
        # 5. Clear setup secret so new one is generated
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
        return DeviceSetupResponse(success=True, message="Device settings saved")
    except Exception as e:
        logger.error(f"Error saving device settings: {e}", exc_info=True)
        return DeviceSetupResponse(success=False, message=str(e))


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


@router.post("/model", response_model=ModelPresetResponse)
def setup_model_preset(
    request: ModelPresetRequest,
    db: Session = Depends(get_db),
) -> ModelPresetResponse:
    """
    Select LLM: local (free), custom (own OpenAI key), or neuroion_agent (currently unavailable).
    """
    try:
        if request.choice not in ("local", "neuroion_agent", "custom"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Invalid choice. Must be "local", "custom", or "neuroion_agent"',
            )

        if request.choice == "neuroion_agent":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Neuroion Agent subscription is currently unavailable.",
            )

        if request.choice == "local":
            model_name = request.model_name or "llama3.2:3b"
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
        else:
            # custom: user's own OpenAI API key (or keep existing if not provided)
            api_key = (request.api_key or "").strip()
            existing_custom = SystemConfigRepository.get(db, "llm_custom")
            existing_config = existing_custom.value if (existing_custom and isinstance(existing_custom.value, dict)) else {}
            if not api_key and not existing_config.get("api_key"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="API key is required when using your own OpenAI account.",
                )
            model_name = request.model or existing_config.get("model") or "gpt-3.5-turbo"
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

        # Test model availability
        test_result = None
        try:
            llm_client = get_llm_client_from_config(db)
            test_messages = [{"role": "user", "content": "Hello"}]
            test_response = llm_client.chat(test_messages, temperature=0.7, max_tokens=10)
            test_result = "Model available and responding"
        except Exception as test_error:
            test_result = f"Model test failed: {str(test_error)}"
            logger.warning(f"Model test failed: {test_error}")

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
    llm_custom_config = SystemConfigRepository.get(db, "llm_custom")
    llm_preset = "local"
    llm_model = "llama3.2:3b"
    if llm_provider_config and isinstance(llm_provider_config.value, dict):
        llm_preset = llm_provider_config.value.get("provider", "local")
        if llm_preset == "local" and llm_ollama_config and isinstance(llm_ollama_config.value, dict):
            llm_model = llm_ollama_config.value.get("model", "llama3.2:3b")
        elif llm_preset == "neuroion_agent" and llm_neuroion_config and isinstance(llm_neuroion_config.value, dict):
            llm_model = llm_neuroion_config.value.get("model", "gpt-4o")
        elif llm_preset == "custom" and llm_custom_config and isinstance(llm_custom_config.value, dict):
            llm_model = llm_custom_config.value.get("model", "gpt-3.5-turbo")
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
        llm_custom_config = SystemConfigRepository.get(db, "llm_custom")
        
        model_choice = "local"
        model_name = "llama3.2:3b"
        model_status = "idle"
        model_health = "unknown"
        
        if llm_provider_config and isinstance(llm_provider_config.value, dict):
            provider = llm_provider_config.value.get("provider", "local")
            model_choice = provider
            if provider == "local" and llm_ollama_config and isinstance(llm_ollama_config.value, dict):
                model_name = llm_ollama_config.value.get("model", "llama3.2:3b")
            elif provider == "neuroion_agent" and llm_neuroion_config and isinstance(llm_neuroion_config.value, dict):
                model_name = llm_neuroion_config.value.get("model", "gpt-4o")
            elif provider == "custom" and llm_custom_config and isinstance(llm_custom_config.value, dict):
                model_name = llm_custom_config.value.get("model", "gpt-3.5-turbo")
            
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

        # Agent (Neuroion Agent / OpenClaw)
        agent_info = None
        try:
            from neuroion.core.services import openclaw_adapter
            agent_info = {"name": "Neuroion Agent", "status": "running" if openclaw_adapter.is_running() else "stopped"}
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
            telegram_connected=telegram_connected,
            agent_running=agent_running,
        )
    except Exception as e:
        logger.error(f"Error getting status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get status: {str(e)}",
        )
