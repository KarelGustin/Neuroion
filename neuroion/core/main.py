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
from neuroion.core.memory.db import init_db
from neuroion.core.api import health, pairing, chat, events, admin, setup, dashboard, integrations
from neuroion.core.services.telegram_service import start_telegram_bot, stop_telegram_bot

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
    
    # Start Telegram bot if configured
    telegram_app = await start_telegram_bot()
    
    yield
    
    # Shutdown
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
app.include_router(pairing.router)
app.include_router(chat.router)
app.include_router(events.router)
app.include_router(admin.router)
app.include_router(dashboard.router)
app.include_router(integrations.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "neuroion.core.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
    )
