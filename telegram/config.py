"""
Configuration for Telegram bot service.
"""
import os
from pathlib import Path
from typing import Optional


class TelegramConfig:
    """Telegram bot configuration."""
    
    bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    bot_username: str = os.getenv("TELEGRAM_BOT_USERNAME", "")  # Bot username without @
    homebase_url: str = os.getenv("HOMEBASE_URL", "http://localhost:8000")
    polling: bool = os.getenv("TELEGRAM_POLLING", "true").lower() == "true"
    telegram_polling_interval: int = int(os.getenv("TELEGRAM_POLLING_INTERVAL", "30"))
    webhook_url: Optional[str] = os.getenv("TELEGRAM_WEBHOOK_URL", None)
    
    @classmethod
    def validate(cls) -> bool:
        """
        
        Validate configuration.
        
        Returns:
            True if valid, False if token is missing (allows graceful degradation)
        """
        if not cls.bot_token:
            return False
        return True


# Global config instance
config = TelegramConfig()
