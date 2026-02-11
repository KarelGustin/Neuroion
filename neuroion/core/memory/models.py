"""
SQLAlchemy models for Neuroion database.

Defines the schema for households, users, preferences, context snapshots, and audit logs.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean,
    DateTime, ForeignKey, JSON, Index
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class Household(Base):
    """Represents a home/household unit."""
    __tablename__ = "households"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    users = relationship("User", back_populates="household", cascade="all, delete-orphan")
    preferences = relationship("Preference", back_populates="household", cascade="all, delete-orphan")
    context_snapshots = relationship("ContextSnapshot", back_populates="household", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="household", cascade="all, delete-orphan")
    chat_messages = relationship("ChatMessage", back_populates="household", cascade="all, delete-orphan")


class User(Base):
    """Represents a user/member within a household."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    household_id = Column(Integer, ForeignKey("households.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    role = Column(String(50), default="member", nullable=False)  # owner, admin, member
    device_id = Column(String(255), unique=True, nullable=True, index=True)  # For iOS/Telegram pairing
    device_type = Column(String(50), nullable=True)  # ios, telegram, web
    created_at = Column(DateTime, default=func.now(), nullable=False)
    last_seen_at = Column(DateTime, nullable=True)
    
    # Member profile fields (for onboarding)
    language = Column(String(10), nullable=True)  # e.g., "nl", "en"
    timezone = Column(String(50), nullable=True)  # e.g., "Europe/Amsterdam"
    style_prefs_json = Column(JSON, nullable=True)  # Communication style preferences
    preferences_json = Column(JSON, nullable=True)  # General preferences (diet, routines, interests)
    consent_json = Column(JSON, nullable=True)  # Privacy consent settings
    
    # Personal page and passcode (for /p/{page_name} and unlock)
    page_name = Column(String(64), unique=True, nullable=True, index=True)  # slug e.g. "karelgustin"
    passcode_hash = Column(String(255), nullable=True)  # bcrypt hash of 4-6 digit passcode
    setup_token = Column(String(64), nullable=True, index=True)  # one-time token to set passcode after join
    setup_token_expires_at = Column(DateTime, nullable=True)  # expiry for setup_token
    
    # Relationships
    household = relationship("Household", back_populates="users")
    audit_logs = relationship("AuditLog", back_populates="user")


class Preference(Base):
    """Stores household and user preferences."""
    __tablename__ = "preferences"
    
    id = Column(Integer, primary_key=True, index=True)
    household_id = Column(Integer, ForeignKey("households.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)  # None = household-level
    key = Column(String(255), nullable=False, index=True)
    value = Column(Text, nullable=False)  # JSON-encoded value
    category = Column(String(100), nullable=True, index=True)  # e.g., "dietary", "schedule", "home"
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    household = relationship("Household", back_populates="preferences")
    
    __table_args__ = (
        Index("idx_pref_household_key", "household_id", "key"),
        Index("idx_pref_user_key", "user_id", "key"),
    )


class ContextSnapshot(Base):
    """Stores derived context summaries (not raw health data)."""
    __tablename__ = "context_snapshots"
    
    id = Column(Integer, primary_key=True, index=True)
    household_id = Column(Integer, ForeignKey("households.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    
    # Event type
    event_type = Column(String(50), nullable=False, index=True)  # location, health_summary
    event_subtype = Column(String(50), nullable=True)  # arriving_home, leaving_home, sleep_score, etc.
    
    # Derived summaries only (never raw data)
    summary = Column(Text, nullable=False)  # Human-readable summary
    context_metadata = Column(JSON, nullable=True)  # Structured metadata (e.g., {"sleep_score": 85, "recovery_level": "high"})
    
    timestamp = Column(DateTime, default=func.now(), nullable=False, index=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    
    # Relationships
    household = relationship("Household", back_populates="context_snapshots")
    
    __table_args__ = (
        Index("idx_context_household_timestamp", "household_id", "timestamp"),
        Index("idx_context_user_timestamp", "user_id", "timestamp"),
    )


class CronJobRecord(Base):
    """Persisted cron jobs (SQLite-backed)."""
    __tablename__ = "cron_jobs"

    id = Column(String(64), primary_key=True, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, index=True)
    job_json = Column(JSON, nullable=False)

    __table_args__ = (
        Index("idx_cron_user_created", "user_id", "created_at"),
    )


class CronRunRecord(Base):
    """Run records for cron jobs."""
    __tablename__ = "cron_runs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(64), ForeignKey("cron_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    run_json = Column(JSON, nullable=False)

    __table_args__ = (
        Index("idx_cron_run_job_ts", "job_id", "timestamp"),
    )


class AuditLog(Base):
    """Audit log for all suggestions, confirmations, and executed actions."""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    household_id = Column(Integer, ForeignKey("households.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    
    # Action details
    action_type = Column(String(50), nullable=False, index=True)  # suggestion, confirmation, execution, rejection
    action_name = Column(String(255), nullable=False)  # e.g., "generate_week_menu"
    reasoning = Column(Text, nullable=True)  # Why this action was suggested
    
    # Input/output
    input_data = Column(JSON, nullable=True)  # Tool input parameters
    output_data = Column(JSON, nullable=True)  # Tool output
    status = Column(String(50), nullable=False, default="pending")  # pending, confirmed, executed, rejected, failed
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False, index=True)
    confirmed_at = Column(DateTime, nullable=True)
    executed_at = Column(DateTime, nullable=True)
    
    # Relationships
    household = relationship("Household", back_populates="audit_logs")
    user = relationship("User", back_populates="audit_logs")
    
    __table_args__ = (
        Index("idx_audit_household_created", "household_id", "created_at"),
        Index("idx_audit_action_type", "action_type", "created_at"),
    )


class ChatMessage(Base):
    """Stores chat messages for conversation history."""
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    household_id = Column(Integer, ForeignKey("households.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Message content
    role = Column(String(20), nullable=False, index=True)  # user, assistant
    content = Column(Text, nullable=False)
    message_metadata = Column(JSON, nullable=True)  # For actions, tool calls, etc.
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False, index=True)
    
    # Relationships
    household = relationship("Household", back_populates="chat_messages")
    user = relationship("User")
    
    __table_args__ = (
        Index("idx_chat_user_created", "user_id", "created_at"),
        Index("idx_chat_household_created", "household_id", "created_at"),
    )


class SystemConfig(Base):
    """System-wide configuration (WiFi, LLM, etc.)."""
    __tablename__ = "system_config"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(255), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=False)  # JSON-encoded
    category = Column(String(100), nullable=False, index=True)  # wifi, llm, etc.
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    __table_args__ = (
        Index("idx_system_config_category", "category"),
    )


class DailyRequestCount(Base):
    """Tracks daily request counts per household (resets at midnight)."""
    __tablename__ = "daily_request_counts"
    
    id = Column(Integer, primary_key=True, index=True)
    household_id = Column(Integer, ForeignKey("households.id"), nullable=False, index=True)
    date = Column(DateTime, nullable=False, index=True)  # Date only (time set to 00:00:00)
    count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    household = relationship("Household")
    
    __table_args__ = (
        Index("idx_daily_request_household_date", "household_id", "date", unique=True),
    )


class UserIntegration(Base):
    """Stores OAuth tokens and permissions for user integrations (Gmail, etc.)."""
    __tablename__ = "user_integrations"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    integration_type = Column(String(50), nullable=False, index=True)  # gmail, etc.
    access_token = Column(Text, nullable=False)  # Encrypted OAuth access token
    refresh_token = Column(Text, nullable=True)  # Encrypted OAuth refresh token
    token_expires_at = Column(DateTime, nullable=True)  # Token expiration time
    permissions = Column(JSON, nullable=True)  # Granted permissions (read, write, delete, etc.)
    integration_metadata = Column(JSON, nullable=True)  # Additional integration metadata
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User")
    
    __table_args__ = (
        Index("idx_user_integration_user_type", "user_id", "integration_type", unique=True),
    )


class DashboardLink(Base):
    """Stores personal dashboard links for users."""
    __tablename__ = "dashboard_links"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    token = Column(String(255), unique=True, nullable=False, index=True)  # Unique token for dashboard access
    expires_at = Column(DateTime, nullable=True)  # Optional; null = never expires
    created_at = Column(DateTime, default=func.now(), nullable=False)
    last_accessed_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User")


class LoginCode(Base):
    """Stores temporary login codes for personal dashboard access."""
    __tablename__ = "login_codes"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    code = Column(String(6), nullable=False, index=True)  # 4-6 digit code
    expires_at = Column(DateTime, nullable=False, index=True)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User")
    
    __table_args__ = (
        Index("idx_login_code_code", "code"),
    )


class DeviceConfig(Base):
    """Device-level configuration."""
    __tablename__ = "device_config"
    
    id = Column(Integer, primary_key=True, index=True)
    wifi_configured = Column(Boolean, default=False, nullable=False)
    hostname = Column(String(255), default="neuroion", nullable=False)
    setup_completed = Column(Boolean, default=False, nullable=False)
    retention_policy = Column(JSON, nullable=True)  # {"days": 365, "auto_delete": True}
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    __table_args__ = (
        Index("idx_device_config_setup", "setup_completed"),
    )


class JoinToken(Base):
    """Single-use join tokens for adding members."""
    __tablename__ = "join_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(64), unique=True, nullable=False, index=True)
    household_id = Column(Integer, ForeignKey("households.id"), nullable=False, index=True)
    created_by_member_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    
    # Relationships
    household = relationship("Household")
    created_by = relationship("User")
    
    __table_args__ = (
        Index("idx_join_token_expires", "expires_at"),
        Index("idx_join_token_used", "used_at"),
    )
