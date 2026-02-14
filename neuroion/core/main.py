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
from neuroion.core.api import health, pairing, chat, events, admin, setup, dashboard, integrations, preferences, join, members, context, agent, cron_tools, agenda
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
    logger.info(
        "Neuroion Homebase binding on %s:%s (from config/.env: API_HOST, API_PORT)",
        settings.api_host,
        settings.api_port,
    )
    
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

    # Start cron scheduler (in-process)
    try:
        from neuroion.core.cron.scheduler import start_scheduler
        await start_scheduler()
    except Exception as e:
        logger.warning("Could not start cron scheduler: %s", e)

    # Start proactive service (agenda reminders to connected WebSocket clients)
    try:
        from neuroion.core.services.proactive_service import start_proactive_service
        await start_proactive_service()
    except Exception as e:
        logger.warning("Could not start proactive service: %s", e)

    yield

    # Shutdown
    try:
        from neuroion.core.services.proactive_service import stop_proactive_service
        await stop_proactive_service()
    except Exception as e:
        logger.warning("Proactive service stop: %s", e)
    try:
        from neuroion.core.cron.scheduler import stop_scheduler
        await stop_scheduler()
    except Exception as e:
        logger.warning("Cron scheduler stop: %s", e)
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
    # Handle factory-reset in middleware so we avoid blocking in the rest of the chain (logging, dispatch, etc.)
    if request.method == "POST" and request.url.path == "/setup/factory-reset":
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
        try:
            from starlette.concurrency import run_in_threadpool
            from neuroion.core.api.setup import _run_factory_reset_sync
            from fastapi import HTTPException
            result = await run_in_threadpool(_run_factory_reset_sync)
            return JSONResponse(status_code=200, content=result.model_dump())
        except HTTPException as e:
            return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
        except Exception as e:
            logger.error("Factory reset failed: %s", e, exc_info=True)
            return JSONResponse(status_code=500, content={"detail": str(e)})

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
    """Log all HTTP requests. Status/health endpoints at DEBUG to reduce log spam."""
    path = request.url.path
    skip_info = path in ("/api/status", "/setup/dev-status", "/setup/status")
    level = logger.debug if skip_info else logger.info
    level(f"{request.method} {path}")
    response = await call_next(request)
    level(f"{request.method} {path} - {response.status_code}")
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


# Explicitly register POST /chat/stream so it is always available (avoids 404 if router load order differs)
app.add_api_route("/chat/stream", chat.chat_stream, methods=["POST"])

# WebSocket for chat, heartbeat, proactive messages, agenda sync
from neuroion.core.websocket.routes import websocket_endpoint
app.add_websocket_route("/ws", websocket_endpoint)

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
app.include_router(agenda.router)
app.include_router(agent.router)
app.include_router(cron_tools.router)

# Log chat routes at startup so we can verify POST /chat/stream is registered
for route in app.routes:
    if hasattr(route, "path") and "/chat" in getattr(route, "path", ""):
        methods = getattr(route, "methods", set()) or set()
        logger.info("Route: %s %s", methods, route.path)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "neuroion.core.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
    )
