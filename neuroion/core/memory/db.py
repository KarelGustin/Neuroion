"""
Database connection and session management.

Handles SQLite database initialization, connection pooling, and session factory.
"""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from contextlib import contextmanager
from typing import Generator

from neuroion.core.config import get_database_url, settings
from neuroion.core.memory.models import Base


# Create engine with SQLite-specific configuration
engine = create_engine(
    get_database_url(),
    connect_args={
        "check_same_thread": False,  # SQLite requirement for FastAPI
        "timeout": 30,  # 30 second timeout for database operations
    },
    poolclass=StaticPool,  # SQLite doesn't support connection pooling, use StaticPool
    pool_pre_ping=True,  # Verify connections before using
    echo=settings.database_echo,
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


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
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def db_session() -> Generator[Session, None, None]:
    """Context manager for database sessions."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


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
