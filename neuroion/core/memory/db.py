"""
Database connection and session management.

Handles SQLite database initialization, connection pooling, and session factory.
"""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session, scoped_session
from sqlalchemy.pool import NullPool
from contextlib import contextmanager
from typing import Generator
import threading

from neuroion.core.config import get_database_url, settings
from neuroion.core.memory.models import Base


# Create engine with SQLite-specific configuration
# Use NullPool to ensure each thread gets its own connection
# This prevents SQLite threading issues (StaticPool shares one connection)
engine = create_engine(
    get_database_url(),
    connect_args={
        "check_same_thread": False,  # SQLite requirement for FastAPI
        "timeout": 30,  # 30 second timeout for database operations
    },
    poolclass=NullPool,  # NullPool creates new connection for each request (thread-safe)
    pool_pre_ping=False,  # Not needed with NullPool
    echo=settings.database_echo,
)

# Use scoped_session for thread-local sessions
# This ensures each thread gets its own database session
SessionLocal = scoped_session(
    sessionmaker(autocommit=False, autoflush=False, bind=engine),
    scopefunc=threading.get_ident
)


def init_db() -> None:
    """Initialize database schema (create tables)."""
    import logging
    import threading
    
    logger = logging.getLogger(__name__)
    
    # Use a lock to ensure only one thread initializes the database
    _init_lock = threading.Lock()
    
    with _init_lock:
        try:
            # Create all tables (this only creates missing tables, doesn't modify existing ones)
            Base.metadata.create_all(bind=engine)
            logger.info("Database schema initialized")
            
            # For development: try to add missing columns to existing tables
            # This is a simple migration approach - in production, use Alembic
            # Only run migrations if tables exist (to avoid errors on fresh installs)
            try:
                from sqlalchemy import inspect, text
                
                inspector = inspect(engine)
                existing_tables = inspector.get_table_names()
                
                # Check if User table exists and add missing columns
                if 'users' in existing_tables:
                    columns = [col['name'] for col in inspector.get_columns('users')]
                    columns_to_add = []
                    
                    if 'language' not in columns:
                        columns_to_add.append(('language', 'VARCHAR(10)'))
                    if 'timezone' not in columns:
                        columns_to_add.append(('timezone', 'VARCHAR(50)'))
                    if 'style_prefs_json' not in columns:
                        columns_to_add.append(('style_prefs_json', 'TEXT'))
                    if 'preferences_json' not in columns:
                        columns_to_add.append(('preferences_json', 'TEXT'))
                    if 'consent_json' not in columns:
                        columns_to_add.append(('consent_json', 'TEXT'))
                    
                    if columns_to_add:
                        # Use the main engine with a connection
                        with engine.connect() as conn:
                            with conn.begin():  # Start a transaction
                                for col_name, col_type in columns_to_add:
                                    try:
                                        conn.execute(text(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}"))
                                        logger.info(f"Added column {col_name} to users table")
                                    except Exception as col_error:
                                        # Column might already exist (race condition)
                                        logger.debug(f"Could not add column {col_name}: {col_error}")
                        logger.info("User table columns updated")
                
                # Ensure new tables exist (device_config, join_tokens)
                Base.metadata.create_all(bind=engine)
                
            except Exception as migration_error:
                logger.warning(f"Migration check failed (this is OK for new databases): {migration_error}")
                
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}", exc_info=True)
            raise


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for FastAPI to get database session.
    
    Usage:
        @app.get("/endpoint")
        def endpoint(db: Session = Depends(get_db)):
            ...
    
    Note: Uses scoped_session for thread safety. Each thread gets its own session.
    """
    import json
    import threading
    thread_id = threading.get_ident()
    # #region agent log
    try:
        with open('/Users/karelgustin/Neuroion/.cursor/debug.log', 'a') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"db.py:55","message":"get_db entry","data":{"thread_id":thread_id},"timestamp":int(__import__('time').time()*1000)})+'\n')
    except: pass
    # #endregion
    db = SessionLocal()
    # #region agent log
    try:
        with open('/Users/karelgustin/Neuroion/.cursor/debug.log', 'a') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"db.py:58","message":"SessionLocal created","data":{"thread_id":thread_id,"session_id":id(db)},"timestamp":int(__import__('time').time()*1000)})+'\n')
    except: pass
    # #endregion
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
        # Close the session and remove from thread-local registry
        # Note: Repositories handle their own commits, so we don't commit here
        try:
            # Only close if session is still bound
            if db.is_active:
                db.close()
        except Exception:
            pass  # Ignore errors when closing
        finally:
            try:
                SessionLocal.remove()
            except Exception:
                pass  # Ignore errors when removing


@contextmanager
def db_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.
    
    Note: Uses scoped_session for thread safety. Each thread gets its own session.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        # Remove the session from the thread-local registry
        SessionLocal.remove()


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
