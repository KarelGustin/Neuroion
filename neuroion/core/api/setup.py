"""
Setup endpoints for initial Homebase configuration.

Handles WiFi configuration, LLM provider setup, and household initialization.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any

from neuroion.core.memory.db import get_db
from neuroion.core.memory.repository import (
    SystemConfigRepository,
    HouseholdRepository,
    UserRepository,
)
from neuroion.core.llm import get_llm_client_from_config
from neuroion.core.llm.ollama import OllamaClient
from neuroion.core.llm.cloud import CloudLLMClient
from neuroion.core.llm.openai import OpenAILLMClient

router = APIRouter(prefix="/setup", tags=["setup"])


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
    
    is_complete = wifi_configured and llm_configured and household_configured
    
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
        # Store WiFi config
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to setup household: {str(e)}",
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
