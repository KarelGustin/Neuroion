"""
Database connection and session management.

Handles SQLite database initialization, connection pooling, and session factory.

All sessions must be created via `get_db()` or `db_session()` and are single-owner:
they may only be used in the thread that created them and within their scope.
"""
import logging
import os
import threading
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool

from neuroion.core.config import get_database_url, settings
from neuroion.core.memory.models import Base


logger = logging.getLogger(__name__)


# Create engine with SQLite-specific configuration.
# Use NullPool so each thread gets its own connection. Sessions must only be used
# in the thread that created them; do not use a session after request scope or
# pass it to another thread (use db_session() in that thread instead).
engine = create_engine(
    get_database_url(),
    connect_args={
        "timeout": 30,  # 30 second timeout for database operations
    },
    poolclass=NullPool,  # New connection per session; no sharing across threads
    pool_pre_ping=False,  # Not needed with NullPool
    echo=settings.database_echo,
)

# Simple debug flag for DB session lifecycle logging
DB_DEBUG_LOG = (
    settings.database_echo
    or os.getenv("DB_DEBUG_LOG", "0").lower() in ("1", "true", "yes")
)

# Session factory – one Session instance per unit of work (request, job).
# We intentionally avoid scoped_session here and rely on explicit lifetime
# via get_db()/db_session() combined with thread-ownership checks.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Global lock to ensure only one thread initializes/migrates the database at a time.
_init_lock = threading.Lock()


def init_db() -> None:
    """Initialize database schema (create tables)."""
    # Use a lock to ensure only one thread initializes the database
    with _init_lock:
        try:
            # Create all tables (this only creates missing tables, doesn't modify existing ones)
            Base.metadata.create_all(bind=engine)
            logger.info("Database schema initialized")

            # For development: try to add missing columns to existing tables
            # This is a simple migration approach - in production, use Alembic
            # Only run migrations if tables exist (to avoid errors on fresh installs)
            try:
                from sqlalchemy import inspect, text as sa_text

                inspector = inspect(engine)
                existing_tables = inspector.get_table_names()

                # Check if User table exists and add missing columns
                if "users" in existing_tables:
                    columns = [col["name"] for col in inspector.get_columns("users")]
                    columns_to_add = []

                    if "language" not in columns:
                        columns_to_add.append(("language", "VARCHAR(10)"))
                    if "timezone" not in columns:
                        columns_to_add.append(("timezone", "VARCHAR(50)"))
                    if "style_prefs_json" not in columns:
                        columns_to_add.append(("style_prefs_json", "TEXT"))
                    if "preferences_json" not in columns:
                        columns_to_add.append(("preferences_json", "TEXT"))
                    if "consent_json" not in columns:
                        columns_to_add.append(("consent_json", "TEXT"))
                    if "page_name" not in columns:
                        columns_to_add.append(("page_name", "VARCHAR(64)"))
                    if "passcode_hash" not in columns:
                        columns_to_add.append(("passcode_hash", "VARCHAR(255)"))
                    if "setup_token" not in columns:
                        columns_to_add.append(("setup_token", "VARCHAR(64)"))
                    if "setup_token_expires_at" not in columns:
                        columns_to_add.append(("setup_token_expires_at", "DATETIME"))

                    if columns_to_add:
                        # Use the main engine with a connection
                        with engine.connect() as conn:
                            with conn.begin():  # Start a transaction
                                for col_name, col_type in columns_to_add:
                                    try:
                                        conn.execute(
                                            sa_text(
                                                f"ALTER TABLE users ADD COLUMN {col_name} {col_type}"
                                            )
                                        )
                                        logger.info(
                                            "Added column %s to users table", col_name
                                        )
                                    except Exception as col_error:
                                        # Column might already exist (race condition)
                                        logger.debug(
                                            "Could not add column %s: %s",
                                            col_name,
                                            col_error,
                                        )
                        logger.info("User table columns updated")

                # Add expires_at to dashboard_links if missing
                if "dashboard_links" in existing_tables:
                    dl_columns = [col["name"] for col in inspector.get_columns("dashboard_links")]
                    if "expires_at" not in dl_columns:
                        with engine.connect() as conn:
                            with conn.begin():
                                try:
                                    conn.execute(sa_text("ALTER TABLE dashboard_links ADD COLUMN expires_at DATETIME"))
                                    logger.info("Added column expires_at to dashboard_links table")
                                except Exception as col_error:
                                    logger.debug("Could not add expires_at to dashboard_links: %s", col_error)

                # Add used_at to login_codes if missing
                if "login_codes" in existing_tables:
                    lc_columns = [col["name"] for col in inspector.get_columns("login_codes")]
                    if "used_at" not in lc_columns:
                        with engine.connect() as conn:
                            with conn.begin():
                                try:
                                    conn.execute(sa_text("ALTER TABLE login_codes ADD COLUMN used_at DATETIME"))
                                    logger.info("Added column used_at to login_codes table")
                                except Exception as col_error:
                                    logger.debug("Could not add used_at to login_codes: %s", col_error)

                # Ensure new tables exist (device_config, join_tokens)
                Base.metadata.create_all(bind=engine)

            except Exception as migration_error:
                logger.warning(
                    "Migration check failed (this is OK for new databases): %s",
                    migration_error,
                )

        except Exception as e:
            logger.error("Failed to initialize database: %s", e, exc_info=True)
            raise


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for FastAPI to get database session.
    
    Usage:
        @app.get("/endpoint")
        def endpoint(db: Session = Depends(get_db)):
            ...
    
    Note: Session is single-owner for DB operations, but FastAPI may construct
    the dependency in a different thread than the one that ultimately performs
    the queries. Do not pass the session beyond the request scope.
    """
    db = SessionLocal()
    if DB_DEBUG_LOG:
        logger.debug(
            "DB session created id=%s thread_id=%s",
            id(db),
            threading.get_ident(),
        )
    try:
        yield db
    except Exception:
        # Rollback on any exception
        try:
            if db.is_active:
                db.rollback()
        except Exception:
            pass  # Ignore rollback errors
        raise
    finally:
        # Close the session.
        # Note: Repositories handle their own commits, so we don't commit here.
        try:
            if DB_DEBUG_LOG:
                logger.debug(
                    "DB session closing id=%s current_thread_id=%s",
                    id(db),
                    threading.get_ident(),
                )
            # Only close if session is still bound
            if db.is_active:
                db.close()
        except Exception:
            pass  # Ignore errors when closing


@contextmanager
def db_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.
    
    Use only in the thread that calls this; do not pass the yielded session
    to another thread. Call from the same thread for the whole with block.
    """
    db = SessionLocal()
    if DB_DEBUG_LOG:
        logger.debug(
            "DB session (context) created id=%s thread_id=%s",
            id(db),
            threading.get_ident(),
        )
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        try:
            if DB_DEBUG_LOG:
                logger.debug(
                    "DB session (context) closing id=%s current_thread_id=%s",
                    id(db),
                    threading.get_ident(),
                )
            if db.is_active:
                db.close()
        except Exception:
            pass


# Enable foreign key constraints and WAL mode for SQLite
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """Enable foreign key constraints and WAL mode in SQLite."""
    cursor = dbapi_conn.cursor()
    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys=ON")
    # Enable WAL mode for better concurrency (allows concurrent reads)
    cursor.execute("PRAGMA journal_mode=WAL")
    # Set busy timeout to handle locks (30 seconds)
    cursor.execute("PRAGMA busy_timeout=30000")
    cursor.close()


# Auto-serialize SystemConfig values before flush
@event.listens_for(Session, "before_flush")
def serialize_system_config_values(session, flush_context, instances):
    """Automatically serialize SystemConfig.value if it's a dict/list before saving."""
    import json
    from neuroion.core.memory.models import SystemConfig
    
    # Check both dirty (modified) and new objects
    for obj in list(session.dirty) + list(session.new):
        if isinstance(obj, SystemConfig):
            # If value is a dict or list, serialize it to JSON
            if isinstance(obj.value, (dict, list)):
                obj.value = json.dumps(obj.value)
            # If value is already a string, it should already be JSON or plain string
            # No need to modify it


@event.listens_for(Session, "before_flush")
def validate_session_owner_thread(session, flush_context, instances):
    """
    Safety check to catch cross-thread session usage early.

    If an owner_thread_id is recorded on the session and the current thread
    is different, we raise a RuntimeError instead of letting SQLite crash
    with a segmentation fault.
    """
    owner_thread_id = session.info.get("owner_thread_id")
    current_thread_id = threading.get_ident()
    if owner_thread_id is None:
        # First flush: record owning thread.
        session.info["owner_thread_id"] = current_thread_id
        if DB_DEBUG_LOG:
            logger.debug(
                "Session %s owner_thread_id set to %s on first flush",
                id(session),
                current_thread_id,
            )
        return

    if owner_thread_id != current_thread_id:
        msg = (
            f"Session {id(session)} used from wrong thread: "
            f"owner_thread_id={owner_thread_id}, current_thread_id={current_thread_id}. "
            "Do not pass sessions or ORM objects across threads or use them after their scope."
        )
        logger.error(msg)
        raise RuntimeError(msg)
