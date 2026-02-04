"""
Telegram bot service integrated into Homebase.

Handles automatic startup and shutdown of Telegram bot when credentials are configured.
"""
import logging
from typing import Optional
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram import Update
from telegram.ext import ContextTypes

from neuroion.core.config import settings

logger = logging.getLogger(__name__)

_telegram_app: Optional[Application] = None


async def start_telegram_bot() -> Optional[Application]:
    """
    Start Telegram bot if token is configured.
    
    Returns:
        Application instance if started, None otherwise
    """
    global _telegram_app
    
    if not settings.telegram_bot_token:
        logger.info("Telegram bot token not configured, skipping Telegram bot startup")
        return None
    
    try:
        # Import here to avoid circular dependencies
        # Add project root to path to import local telegram module
        import sys
        import os
        from pathlib import Path
        
        # Get project root (parent of neuroion directory)
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent.parent.parent
        project_root_str = str(project_root)
        
        # Add to path if not already there
        if project_root_str not in sys.path:
            sys.path.insert(0, project_root_str)
        
        # Now import the local telegram module
        import importlib.util
        telegram_config_path = project_root / "telegram" / "config.py"
        telegram_bot_path = project_root / "telegram" / "bot.py"
        
        # Load telegram.config module
        spec_config = importlib.util.spec_from_file_location("telegram.config", telegram_config_path)
        telegram_config_module = importlib.util.module_from_spec(spec_config)
        sys.modules["telegram.config"] = telegram_config_module
        spec_config.loader.exec_module(telegram_config_module)
        TelegramConfig = telegram_config_module.TelegramConfig
        
        # Load telegram.bot module
        spec_bot = importlib.util.spec_from_file_location("telegram.bot", telegram_bot_path)
        telegram_bot_module = importlib.util.module_from_spec(spec_bot)
        sys.modules["telegram.bot"] = telegram_bot_module
        spec_bot.loader.exec_module(telegram_bot_module)
        
        start_command = telegram_bot_module.start_command
        pair_command = telegram_bot_module.pair_command
        dashboard_command = telegram_bot_module.dashboard_command
        handle_message = telegram_bot_module.handle_message
        execute_command = telegram_bot_module.execute_command
        
        # Configure TelegramConfig from settings
        TelegramConfig.bot_token = settings.telegram_bot_token
        TelegramConfig.bot_username = settings.telegram_bot_username or ""
        # Use localhost instead of 0.0.0.0 for HTTP requests
        if settings.api_host == "0.0.0.0":
            TelegramConfig.homebase_url = f"http://localhost:{settings.api_port}"
        else:
            TelegramConfig.homebase_url = f"http://{settings.api_host}:{settings.api_port}"
        TelegramConfig.polling = True
        
        # Create application
        app = Application.builder().token(settings.telegram_bot_token).build()
        
        # Register handlers
        app.add_handler(CommandHandler("start", start_command))
        app.add_handler(CommandHandler("pair", pair_command))
        app.add_handler(CommandHandler("dashboard", dashboard_command))
        app.add_handler(CommandHandler("execute", execute_command))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        # Start polling in background
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        
        _telegram_app = app
        logger.info("✅ Telegram bot started successfully")
        return app
        
    except Exception as e:
        logger.error(f"Failed to start Telegram bot: {e}", exc_info=True)
        # Don't crash Homebase if bot fails to start
        return None


async def stop_telegram_bot() -> None:
    """Stop Telegram bot gracefully."""
    global _telegram_app
    
    if _telegram_app:
        try:
            await _telegram_app.updater.stop()
            await _telegram_app.stop()
            await _telegram_app.shutdown()
            logger.info("Telegram bot stopped")
        except Exception as e:
            logger.error(f"Error stopping Telegram bot: {e}", exc_info=True)
        finally:
            _telegram_app = None
