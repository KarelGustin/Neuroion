"""
Configuration management for Neuroion Homebase.

Handles environment-based configuration for development and production.
"""
import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Environment
    environment: str = os.getenv("ENVIRONMENT", "development")
    _debug_env = os.getenv("DEBUG", "false").lower()
    debug: bool = _debug_env in ("true", "1", "yes") if _debug_env else False
    
    # API
    api_host: str = os.getenv("API_HOST", "0.0.0.0")
    api_port: int = int(os.getenv("API_PORT", "8000"))
    
    # Ollama LLM
    ollama_url: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3.2")
    ollama_timeout: int = int(os.getenv("OLLAMA_TIMEOUT", "120"))
    
    # Database
    database_path: str = os.getenv("DATABASE_PATH", str(Path.home() / ".neuroion" / "neuroion.db"))
    database_echo: bool = os.getenv("DATABASE_ECHO", "false").lower() == "true"
    
    # Security
    secret_key: str = os.getenv("SECRET_KEY", "change-me-in-production-use-strong-random-key")
    token_algorithm: str = os.getenv("TOKEN_ALGORITHM", "HS256")
    token_expire_hours: int = int(os.getenv("TOKEN_EXPIRE_HOURS", "8760"))  # 1 year
    pairing_code_expire_minutes: int = int(os.getenv("PAIRING_CODE_EXPIRE_MINUTES", "10"))
    
    # CORS
    cors_origins: list[str] = os.getenv("CORS_ORIGINS", "*").split(",")
    
    # Setup UI
    setup_ui_port: int = int(os.getenv("SETUP_UI_PORT", "3000"))
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_database_url() -> str:
    """Get SQLite database URL."""
    # Ensure directory exists
    db_path = Path(settings.database_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{settings.database_path}"
