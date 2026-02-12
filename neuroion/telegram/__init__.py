"""
Telegram bot for Neuroion.

Can be run standalone (python -m neuroion.telegram.bot) or embedded via
neuroion.core.services.telegram_service when Homebase starts.
"""
from neuroion.telegram.config import TelegramConfig, config
from neuroion.telegram.bot import (
    start_command,
    pair_command,
    dashboard_command,
    handle_message,
    execute_command,
    main,
)

__all__ = [
    "TelegramConfig",
    "config",
    "start_command",
    "pair_command",
    "dashboard_command",
    "handle_message",
    "execute_command",
    "main",
]
