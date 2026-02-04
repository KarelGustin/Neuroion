"""LLM integration package."""
from typing import Optional
from sqlalchemy.orm import Session

from neuroion.core.llm.base import LLMClient
from neuroion.core.llm.ollama import OllamaClient
from neuroion.core.llm.cloud import CloudLLMClient
from neuroion.core.llm.openai import OpenAILLMClient
from neuroion.core.memory.repository import SystemConfigRepository


def get_llm_client_from_config(db: Session) -> LLMClient:
    """
    Get LLM client based on system configuration.
    
    Reads LLM provider settings from SystemConfig and returns the appropriate client.
    Falls back to local Ollama if no configuration is found.
    
    Args:
        db: Database session
    
    Returns:
        LLMClient instance
    """
    # Get LLM provider config
    provider_config = SystemConfigRepository.get(db, "llm_provider")
    
    if not provider_config:
        # Default to local Ollama
        return OllamaClient()
    
    provider = provider_config.value if isinstance(provider_config.value, str) else provider_config.value.get("provider", "local")
    
    if provider == "local":
        # Local Ollama
        ollama_config = SystemConfigRepository.get(db, "llm_ollama")
        if ollama_config and isinstance(ollama_config.value, dict):
            config = ollama_config.value
            return OllamaClient(
                base_url=config.get("base_url"),
                model=config.get("model"),
                timeout=config.get("timeout"),
            )
        return OllamaClient()
    
    elif provider == "cloud":
        # Free cloud provider (HuggingFace)
        cloud_config = SystemConfigRepository.get(db, "llm_cloud")
        if cloud_config and isinstance(cloud_config.value, dict):
            config = cloud_config.value
            return CloudLLMClient(
                model=config.get("model", "mistralai/Mixtral-8x7B-Instruct-v0.1"),
                api_key=config.get("api_key"),
                base_url=config.get("base_url"),
                timeout=config.get("timeout", 120),
            )
        return CloudLLMClient()
    
    elif provider == "custom":
        # Custom API (OpenAI, Anthropic, etc.)
        custom_config = SystemConfigRepository.get(db, "llm_custom")
        if custom_config and isinstance(custom_config.value, dict):
            config = custom_config.value
            return OpenAILLMClient(
                api_key=config.get("api_key", ""),
                base_url=config.get("base_url", "https://api.openai.com/v1"),
                model=config.get("model", "gpt-3.5-turbo"),
                timeout=config.get("timeout", 120),
            )
        raise ValueError("Custom LLM provider configured but no API credentials found")
    
    else:
        # Unknown provider, fall back to local
        return OllamaClient()