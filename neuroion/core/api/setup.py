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
from neuroion.core.llm import get_llm_client_from_config
from neuroion.core.llm.ollama import OllamaClient
from neuroion.core.llm.cloud import CloudLLMClient
from neuroion.core.llm.openai import OpenAILLMClient
from neuroion.core.services.wifi_service import WiFiService

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
    """LLM model preset selection request."""
    preset: str  # fast, balanced, quality
    model_name: Optional[str] = None  # Optional override


class ModelPresetResponse(BaseModel):
    """Model preset response."""
    success: bool
    preset: str
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


# Endpoints

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
        # Store WiFi config (repository handles commit internally)
        SystemConfigRepository.set(
            db=db,
            key="wifi",
            value={
                "ssid": request.ssid,
                "password": request.password,
            },
            category="wifi",
        )
        
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
        
        # Test LLM connection
        test_result = None
        try:
            llm_client = get_llm_client_from_config(db)
            test_messages = [{"role": "user", "content": "Hello"}]
            test_response = llm_client.chat(test_messages, temperature=0.7, max_tokens=10)
            test_result = f"Connection successful. Test response: {test_response[:50]}..."
        except Exception as test_error:
            test_result = f"Connection test failed: {str(test_error)}"
        
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
        # Update device config to mark setup as complete
        DeviceConfigRepository.update(
            db=db,
            setup_completed=True,
        )
        
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
    Select LLM model preset (fast/balanced/quality).
    
    Maps preset to specific model and updates LLM configuration.
    """
    try:
        # Map preset to model
        preset_models = {
            "fast": "llama3.2:1b",  # Smaller, faster model
            "balanced": "llama3.2",  # Default balanced model
            "quality": "llama3.2:3b",  # Larger, higher quality model
        }
        
        if request.preset not in preset_models:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid preset: {request.preset}. Must be one of: fast, balanced, quality",
            )
        
        model_name = request.model_name or preset_models[request.preset]
        
        # Update LLM config to use local provider with selected model
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
            preset=request.preset,
            model_name=model_name,
            message=f"Model preset configured: {test_result or 'Configuration saved'}",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting up model preset: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to setup model preset: {str(e)}",
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
        
        # Try to get LAN IP (will be implemented in NetworkManager)
        lan_ip = "192.168.1.100"  # Placeholder, will use NetworkManager.get_lan_ip()
        
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
        
        model_preset = "balanced"
        model_name = "llama3.2"
        model_status = "idle"
        model_health = "unknown"
        
        if llm_provider_config and isinstance(llm_provider_config.value, dict):
            provider = llm_provider_config.value.get("provider", "local")
            
            if provider == "local" and llm_ollama_config and isinstance(llm_ollama_config.value, dict):
                model_name = llm_ollama_config.value.get("model", "llama3.2")
                # Determine preset from model name
                if "1b" in model_name.lower():
                    model_preset = "fast"
                elif "3b" in model_name.lower():
                    model_preset = "quality"
                else:
                    model_preset = "balanced"
                
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
            "preset": model_preset,
            "name": model_name,
            "status": model_status,
            "health": model_health,
        }
        
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
        
        return StatusResponse(
            network=network_info,
            model=model_info,
            uptime=uptime_seconds,
            household=household_info,
        )
    except Exception as e:
        logger.error(f"Error getting status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get status: {str(e)}",
        )
