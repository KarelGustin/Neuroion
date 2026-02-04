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
    Base.metadata.create_all(bind=engine)


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
    finally:
        # #region agent log
        try:
            with open('/Users/karelgustin/Neuroion/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"db.py:64","message":"get_db finally - before remove","data":{"thread_id":thread_id,"session_id":id(db)},"timestamp":int(__import__('time').time()*1000)})+'\n')
        except: pass
        # #endregion
        # Remove the session from the thread-local registry
        SessionLocal.remove()
        # #region agent log
        try:
            with open('/Users/karelgustin/Neuroion/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"db.py:67","message":"get_db finally - after remove","data":{"thread_id":thread_id},"timestamp":int(__import__('time').time()*1000)})+'\n')
        except: pass
        # #endregion


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
