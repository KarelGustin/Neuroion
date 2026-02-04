"""
Telegram bot service for Neuroion.

Handles Telegram messages and forwards them to the Homebase API.
"""
import asyncio
import logging
import json
import os
from pathlib import Path

import httpx
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from telegram.config import config

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Persistent token storage file
TOKEN_STORAGE_FILE = Path.home() / ".neuroion" / "telegram_tokens.json"

# Store user tokens (device_id -> token)
user_tokens: dict[str, str] = {}


def load_tokens() -> dict[str, str]:
    """Load tokens from persistent storage."""
    if TOKEN_STORAGE_FILE.exists():
        try:
            with open(TOKEN_STORAGE_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading tokens: {e}")
    return {}


def save_tokens(tokens: dict[str, str]) -> None:
    """Save tokens to persistent storage."""
    TOKEN_STORAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(TOKEN_STORAGE_FILE, 'w') as f:
            json.dump(tokens, f)
    except Exception as e:
        logger.error(f"Error saving tokens: {e}")


# Load tokens on startup
user_tokens = load_tokens()


def get_homebase_url(endpoint: str) -> str:
    """Get full Homebase API URL."""
    return f"{config.homebase_url}{endpoint}"


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command. Accepts pairing code as parameter."""
    user = update.effective_user
    device_id = f"telegram_{user.id}"
    
    logger.info(
        "Received /start from user_id=%s username=%s args=%s",
        user.id,
        getattr(user, "username", None),
        context.args,
    )
    
    # Check if already paired
    token = user_tokens.get(device_id)
    if token:
        await update.message.reply_text(
            f"Welcome back, {user.first_name}!\n\n"
            "You're already paired with Neuroion. Just send me a message to chat!"
        )
        return
    
    # Check if pairing code is provided as parameter
    if context.args and len(context.args) > 0:
        pairing_code = context.args[0]
        
        try:
            # Confirm pairing with Homebase (async HTTP)
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    get_homebase_url("/pair/confirm"),
                    json={
                        "pairing_code": pairing_code,
                        "device_id": device_id,
                        "device_type": "telegram",
                    },
                )
            response.raise_for_status()
            data = response.json()
            
            # Store token
            user_tokens[device_id] = data["token"]
            save_tokens(user_tokens)
            
            await update.message.reply_text(
                f"✅ Successfully paired with Neuroion!\n\n"
                f"Household ID: {data['household_id']}\n"
                f"You can now chat with me. Just send me a message!"
            )
            return
        except httpx.HTTPStatusError as e:
            error_detail = ""
            if e.response is not None:
                try:
                    error_data = e.response.json()
                    error_detail = error_data.get("detail", str(e))
                except Exception:
                    error_detail = e.response.text or str(e)
            else:
                error_detail = str(e)
            
            logger.error(f"Pairing HTTP error: {error_detail}")
            await update.message.reply_text(
                f"❌ Pairing failed: {error_detail}\n\n"
                "Make sure the pairing code is correct and not expired.\n"
                "You can also use /pair <code> to try again."
            )
            return
        except httpx.RequestError as e:
            logger.error(f"Pairing error: {e}", exc_info=True)
            await update.message.reply_text(
                f"❌ Pairing failed: {str(e)}\n\n"
                "Make sure the pairing code is correct and not expired.\n"
                "You can also use /pair <code> to try again."
            )
            return
    
    # No pairing code provided, show welcome message
    await update.message.reply_text(
        f"Welcome to Neuroion, {user.first_name}!\n\n"
        "To get started, you need to pair this device with your Homebase.\n\n"
        "Option 1: Scan the QR code from your Neuroion setup UI\n"
        "Option 2: Use /pair <pairing_code> with a code from your setup UI."
    )


async def pair_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /pair command."""
    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "Usage: /pair <pairing_code>\n\n"
            "Get the pairing code from your Neuroion setup UI."
        )
        return
    
    pairing_code = context.args[0]
    user = update.effective_user
    device_id = f"telegram_{user.id}"
    
    logger.info(
        "Received /pair from user_id=%s username=%s code=%s",
        user.id,
        getattr(user, "username", None),
        pairing_code,
    )
    
    try:
        # Confirm pairing with Homebase (async HTTP)
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                get_homebase_url("/pair/confirm"),
                json={
                    "pairing_code": pairing_code,
                    "device_id": device_id,
                    "device_type": "telegram",
                },
            )
        response.raise_for_status()
        data = response.json()
        
        # Store token
        user_tokens[device_id] = data["token"]
        save_tokens(user_tokens)
        
        await update.message.reply_text(
            f"✅ Successfully paired!\n\n"
            f"Household ID: {data['household_id']}\n"
            f"You can now chat with Neuroion."
        )
    except httpx.HTTPStatusError as e:
        error_detail = ""
        if e.response is not None:
            try:
                error_data = e.response.json()
                error_detail = error_data.get("detail", str(e))
            except Exception:
                error_detail = e.response.text or str(e)
        else:
            error_detail = str(e)
        
        logger.error(f"Pairing HTTP error: {error_detail}")
        await update.message.reply_text(
            f"❌ Pairing failed: {error_detail}\n\n"
            "Make sure the pairing code is correct and not expired."
        )
    except httpx.RequestError as e:
        logger.error(f"Pairing error: {e}", exc_info=True)
        await update.message.reply_text(
            f"❌ Pairing failed: {str(e)}\n\n"
            "Make sure the pairing code is correct and not expired."
        )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle regular text messages."""
    user = update.effective_user
    device_id = f"telegram_{user.id}"
    
    # Check if paired
    token = user_tokens.get(device_id)
    if not token:
        await update.message.reply_text(
            "⚠️ You need to pair first. Use /pair <code> to pair with your Homebase."
        )
        return
    
    message_text = update.message.text
    
    logger.info(
        "Received message from user_id=%s username=%s paired=%s text=%r",
        user.id,
        getattr(user, "username", None),
        bool(token),
        message_text,
    )
    
    try:
        # Send message to Homebase (history is auto-fetched by backend) via async HTTP
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                get_homebase_url("/chat"),
                json={"message": message_text},
                headers={"Authorization": f"Bearer {token}"},
            )
        response.raise_for_status()
        data = response.json()
        
        # Send response back to user
        reply_text = data.get("message", "No response")
        
        # If there are actions, mention them
        actions = data.get("actions", [])
        if actions:
            reply_text += "\n\n"
            for action in actions:
                reply_text += f"\n💡 Suggested action: {action.get('name')}\n"
                reply_text += f"   {action.get('reasoning', '')}\n"
                reply_text += f"   Use /execute {action.get('id')} to confirm\n"
        
        await update.message.reply_text(reply_text)
        
    except httpx.RequestError as e:
        logger.error(f"Chat error: {e}")
        await update.message.reply_text(
            f"❌ Error communicating with Homebase: {str(e)}"
        )


async def execute_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /execute command for action confirmation."""
    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "Usage: /execute <action_id>\n\n"
            "Execute a suggested action by its ID."
        )
        return
    
    action_id = int(context.args[0])
    user = update.effective_user
    device_id = f"telegram_{user.id}"
    
    token = user_tokens.get(device_id)
    if not token:
        await update.message.reply_text(
            "⚠️ You need to pair first."
        )
        return
    
    logger.info(
        "Received /execute from user_id=%s username=%s action_id=%s",
        user.id,
        getattr(user, "username", None),
        action_id,
    )
    
    try:
        # Execute action via async HTTP
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                get_homebase_url("/chat/actions/execute"),
                json={"action_id": action_id},
                headers={"Authorization": f"Bearer {token}"},
            )
        response.raise_for_status()
        data = response.json()
        
        if data.get("success"):
            await update.message.reply_text(
                f"✅ Action executed successfully!\n\n"
                f"{str(data.get('result', ''))}"
            )
        else:
            await update.message.reply_text(
                f"❌ Action failed: {data.get('error', 'Unknown error')}"
            )
    except httpx.RequestError as e:
        logger.error(f"Execute error: {e}")
        await update.message.reply_text(
            f"❌ Error executing action: {str(e)}"
        )


def main():
    """Start the Telegram bot."""
    config.validate()
    
    # Create application
    application = Application.builder().token(config.bot_token).build()
    
    # Register handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("pair", pair_command))
    application.add_handler(CommandHandler("execute", execute_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Start bot
    if config.polling:
        logger.info("Starting bot in polling mode...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    else:
        logger.info("Bot configured for webhook mode")
        # Webhook setup would go here


if __name__ == "__main__":
    main()
