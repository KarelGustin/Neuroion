"""
Neuroion Homebase - Main FastAPI application.

Local-first home intelligence platform core server.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import logging
import traceback

from neuroion.core.config import settings
from neuroion.core.memory.db import init_db, db_session
from neuroion.core.api import health, pairing, chat, events, admin, setup, dashboard, integrations, preferences, join, members, context, agent
from neuroion.core.services.telegram_service import start_telegram_bot, stop_telegram_bot
from neuroion.core.config_store import (
    get_device_config as config_store_get_device_config,
    get_wifi_config as config_store_get_wifi_config,
    set_wifi_configured as config_store_set_wifi_configured,
)
from neuroion.core.services import neuroion_adapter
from neuroion.core.services.wifi_service import WiFiService
from neuroion.core.services.network_manager import NetworkManager

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# Lifespan event handlers
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown."""
    # Startup
    logger.info("Initializing database...")
    init_db()
    logger.info("Database initialized")
    logger.info(f"Neuroion Homebase starting on {settings.api_host}:{settings.api_port}")
    
    # Prefer saved Wi-Fi on boot; fallback to hotspot if needed
    try:
        with db_session() as db:
            wifi_cfg = config_store_get_wifi_config(db)
            if wifi_cfg and wifi_cfg.get("ssid"):
                ssid = wifi_cfg.get("ssid", "")
                password = wifi_cfg.get("password", "")
                logger.info("Attempting to connect to saved Wi-Fi on boot")
                success, message = WiFiService.configure_wifi(ssid, password)
                if success:
                    config_store_set_wifi_configured(db, True)
                    try:
                        NetworkManager.stop_softap()
                    except Exception as e:
                        logger.warning("Could not switch to normal mode after Wi-Fi connect: %s", e)
                    logger.info("Wi-Fi connected on boot: %s", ssid)
                else:
                    config_store_set_wifi_configured(db, False)
                    logger.warning("Wi-Fi connect failed on boot: %s", message)
                    NetworkManager.start_softap()
            else:
                NetworkManager.start_softap()
    except Exception as e:
        logger.warning("Boot Wi-Fi check failed; starting hotspot: %s", e)
        NetworkManager.start_softap()

    # Start Telegram bot if configured
    telegram_app = await start_telegram_bot()

    # Optionally start Neuroion Agent (Neuroion) when setup is complete
    if neuroion_adapter.is_available():
        try:
            with db_session() as db:
                device = config_store_get_device_config(db)
                if device.get("setup_completed"):
                    from pathlib import Path
                    state_dir = Path(settings.database_path).parent / "neuroion"
                    neuroion_adapter.write_config(device, state_dir)
                    env_extra = neuroion_adapter.build_env_extra_from_db(db)
                    if neuroion_adapter.start(config_dir=state_dir, env_extra=env_extra):
                        logger.info("Neuroion Agent (Neuroion) started")
        except Exception as e:
            logger.warning("Could not start Neuroion Agent: %s", e)

    yield

    # Shutdown
    neuroion_adapter.stop()
    if telegram_app:
        await stop_telegram_bot()
    logger.info("Neuroion Homebase shutting down")


# Create FastAPI app
app = FastAPI(
    title="Neuroion Homebase",
    description="Local-first home intelligence platform",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# CSRF-style protection for setup: reject if Origin is from a different host (LAN-only; allow same host and localhost)
@app.middleware("http")
async def setup_csrf_check(request: Request, call_next):
    if request.method in ("POST", "PUT", "PATCH", "DELETE") and request.url.path.startswith("/setup"):
        origin = request.headers.get("origin") or request.headers.get("referer") or ""
        if origin:
            try:
                from urllib.parse import urlparse
                parsed = urlparse(origin)
                origin_host = (parsed.hostname or "").lower()
                request_host = (request.url.hostname or "").lower()
                if origin_host and request_host and origin_host != request_host:
                    if origin_host not in ("localhost", "127.0.0.1") and request_host not in ("localhost", "127.0.0.1"):
                        return JSONResponse(status_code=403, content={"detail": "Origin not allowed for setup"})
            except Exception:
                pass
    return await call_next(request)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests."""
    logger.info(f"{request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"{request.method} {request.url.path} - {response.status_code}")
    return response


# Error handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors(), "body": exc.body},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "error": str(exc) if settings.debug else None,
        },
    )


# Include routers
app.include_router(health.router)
app.include_router(setup.router)
app.include_router(setup.status_router)  # /api/status endpoint
app.include_router(join.router)
app.include_router(members.router)
app.include_router(pairing.router)
app.include_router(chat.router)
app.include_router(events.router)
app.include_router(admin.router)
app.include_router(dashboard.router)
app.include_router(integrations.router)
app.include_router(preferences.router)
app.include_router(context.router)
app.include_router(agent.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "neuroion.core.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
    )
