"""
Repository layer for database operations.

Provides high-level methods for CRUD operations on all models.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import logging
import threading
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from neuroion.core.memory.models import (
    Household,
    User,
    Preference,
    ContextSnapshot,
    CronJobRecord,
    CronRunRecord,
    AuditLog,
    ChatMessage,
    SystemConfig,
    DailyRequestCount,
    UserIntegration,
    DashboardLink,
    LoginCode,
    DeviceConfig,
    JoinToken,
)
from neuroion.core.utils.slug import slugify


logger = logging.getLogger(__name__)


def require_active_session(db: Session) -> None:
    """Raise if session is closed; prevents use-after-close."""
    if not db.is_active:
        raise RuntimeError(
            "Session already closed; do not use request session outside request scope "
            "or from another thread."
        )


def safe_refresh(db: Session, obj: Any) -> None:
    """Safely refresh an object, ignoring errors if session is closed."""
    try:
        if db.is_active:
            db.refresh(obj)
    except Exception:
        pass  # Ignore refresh errors - object is already committed


class HouseholdRepository:
    """Repository for household operations."""
    
    @staticmethod
    def create(db: Session, name: str) -> Household:
        """Create a new household."""
        require_active_session(db)
        household = Household(name=name)
        db.add(household)
        try:
            db.commit()
            safe_refresh(db, household)
        except Exception:
            db.rollback()
            raise
        return household
    
    @staticmethod
    def get_by_id(db: Session, household_id: int) -> Optional[Household]:
        """Get household by ID."""
        return db.query(Household).filter(Household.id == household_id).first()
    
    @staticmethod
    def get_all(db: Session) -> List[Household]:
        """Get all households."""
        return db.query(Household).all()
    
    @staticmethod
    def update(db: Session, household_id: int, name: str) -> Optional[Household]:
        """Update household name."""
        require_active_session(db)
        household = HouseholdRepository.get_by_id(db, household_id)
        if household:
            household.name = name
            db.commit()
        return household
    
    @staticmethod
    def delete(db: Session, household_id: int) -> bool:
        """Delete household and all related data."""
        require_active_session(db)
        household = HouseholdRepository.get_by_id(db, household_id)
        if household:
            db.delete(household)
            db.commit()
            return True
        return False


class UserRepository:
    """Repository for user operations."""
    
    @staticmethod
    def create(
        db: Session,
        household_id: int,
        name: str,
        role: str = "member",
        device_id: Optional[str] = None,
        device_type: Optional[str] = None,
        page_name: Optional[str] = None,
    ) -> User:
        """Create a new user. If page_name not provided, generates from name."""
        require_active_session(db)
        user = User(
            household_id=household_id,
            name=name,
            role=role,
            device_id=device_id,
            device_type=device_type,
            page_name=page_name,
        )
        db.add(user)
        try:
            db.commit()
            safe_refresh(db, user)
        except Exception:
            db.rollback()
            raise
        return user
    
    @staticmethod
    def get_by_id(db: Session, user_id: int) -> Optional[User]:
        """Get user by ID."""
        return db.query(User).filter(User.id == user_id).first()
    
    @staticmethod
    def get_by_device_id(db: Session, device_id: str) -> Optional[User]:
        """Get user by device ID."""
        return db.query(User).filter(User.device_id == device_id).first()
    
    @staticmethod
    def get_by_household(db: Session, household_id: int) -> List[User]:
        """Get all users in a household."""
        return db.query(User).filter(User.household_id == household_id).all()

    @staticmethod
    def get_by_page_name(db: Session, page_name: str) -> Optional[User]:
        """Get user by page_name (slug)."""
        if not page_name:
            return None
        return db.query(User).filter(User.page_name == page_name.strip().lower()).first()

    @staticmethod
    def get_by_setup_token(db: Session, setup_token: str) -> Optional[User]:
        """Get user by valid setup_token (for post-join passcode set)."""
        if not setup_token:
            return None
        user = (
            db.query(User)
            .filter(
                User.setup_token == setup_token,
                User.setup_token_expires_at > datetime.utcnow(),
            )
            .first()
        )
        return user

    @staticmethod
    def ensure_unique_page_name(
        db: Session,
        base_slug: str,
        exclude_user_id: Optional[int] = None,
    ) -> str:
        """Return a unique page_name. If base_slug is taken, append 2, 3, ..."""
        require_active_session(db)
        candidate = base_slug
        suffix = 1
        while True:
            q = db.query(User).filter(User.page_name == candidate)
            if exclude_user_id is not None:
                q = q.filter(User.id != exclude_user_id)
            if q.first() is None:
                return candidate
            suffix += 1
            candidate = f"{base_slug}{suffix}"

    @staticmethod
    def set_passcode(db: Session, user_id: int, passcode_hash: str) -> bool:
        """Set passcode hash for user. Returns True on success."""
        require_active_session(db)
        user = UserRepository.get_by_id(db, user_id)
        if not user:
            return False
        user.passcode_hash = passcode_hash
        user.setup_token = None
        user.setup_token_expires_at = None
        try:
            db.commit()
            safe_refresh(db, user)
            return True
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def set_page_name(db: Session, user_id: int, page_name: str) -> bool:
        """Set page_name for user (must be unique). Returns True on success."""
        require_active_session(db)
        user = UserRepository.get_by_id(db, user_id)
        if not user:
            return False
        user.page_name = page_name
        try:
            db.commit()
            safe_refresh(db, user)
            return True
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def set_setup_token(
        db: Session,
        user_id: int,
        setup_token: str,
        expires_in_minutes: int = 10,
    ) -> bool:
        """Set one-time setup_token for user (e.g. after join)."""
        require_active_session(db)
        user = UserRepository.get_by_id(db, user_id)
        if not user:
            return False
        user.setup_token = setup_token
        user.setup_token_expires_at = datetime.utcnow() + timedelta(minutes=expires_in_minutes)
        try:
            db.commit()
            safe_refresh(db, user)
            return True
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def update_last_seen(db: Session, user_id: int) -> None:
        """Update user's last_seen_at timestamp."""
        require_active_session(db)
        user = UserRepository.get_by_id(db, user_id)
        if not user:
            return
        user.last_seen_at = datetime.utcnow()
        try:
            db.commit()
            safe_refresh(db, user)
        except Exception:
            db.rollback()
            raise
    
    @staticmethod
    def update(
        db: Session,
        user_id: int,
        name: Optional[str] = None,
        role: Optional[str] = None,
        language: Optional[str] = None,
        timezone: Optional[str] = None,
        style_prefs_json: Optional[str] = None,
        preferences_json: Optional[str] = None,
        consent_json: Optional[str] = None,
        page_name: Optional[str] = None,
        passcode_hash: Optional[str] = None,
    ) -> Optional[User]:
        """Update user."""
        require_active_session(db)
        user = UserRepository.get_by_id(db, user_id)
        if not user:
            return None

        if name is not None:
            user.name = name
        if role is not None:
            user.role = role
        if language is not None:
            user.language = language
        if timezone is not None:
            user.timezone = timezone
        if style_prefs_json is not None:
            user.style_prefs_json = style_prefs_json
        if preferences_json is not None:
            user.preferences_json = preferences_json
        if consent_json is not None:
            user.consent_json = consent_json
        if page_name is not None:
            user.page_name = page_name
        if passcode_hash is not None:
            user.passcode_hash = passcode_hash
            user.setup_token = None
            user.setup_token_expires_at = None

        try:
            db.commit()
            safe_refresh(db, user)
            return user
        except Exception:
            db.rollback()
            raise
    
    @staticmethod
    def delete(db: Session, user_id: int) -> bool:
        """Delete user (caller must have already deleted or nulled related rows)."""
        require_active_session(db)
        user = UserRepository.get_by_id(db, user_id)
        if user:
            db.delete(user)
            db.commit()
            return True
        return False

    @staticmethod
    def delete_user_and_all_data(db: Session, user_id: int) -> bool:
        """
        Delete user and all data associated with them.
        Deletes: preferences, context_snapshots, audit_logs, chat_messages,
        user_integrations, login_codes, dashboard_links, join_tokens (created_by).
        """
        require_active_session(db)
        user = UserRepository.get_by_id(db, user_id)
        if not user:
            return False
        # Delete in order (child tables first due to FKs)
        db.query(Preference).filter(Preference.user_id == user_id).delete()
        db.query(ContextSnapshot).filter(ContextSnapshot.user_id == user_id).delete()
        db.query(AuditLog).filter(AuditLog.user_id == user_id).delete()
        db.query(ChatMessage).filter(ChatMessage.user_id == user_id).delete()
        db.query(UserIntegration).filter(UserIntegration.user_id == user_id).delete()
        db.query(LoginCode).filter(LoginCode.user_id == user_id).delete()
        db.query(DashboardLink).filter(DashboardLink.user_id == user_id).delete()
        db.query(JoinToken).filter(JoinToken.created_by_member_id == user_id).delete()
        db.delete(user)
        try:
            db.commit()
            return True
        except Exception:
            db.rollback()
            raise


class PreferenceRepository:
    """Repository for preference operations."""
    
    @staticmethod
    def set(
        db: Session,
        household_id: int,
        key: str,
        value: Any,
        user_id: Optional[int] = None,
        category: Optional[str] = None,
    ) -> Preference:
        """Set a preference value."""
        require_active_session(db)
        # Check if preference exists
        query = db.query(Preference).filter(
            Preference.household_id == household_id,
            Preference.key == key,
        )
        if user_id is not None:
            query = query.filter(Preference.user_id == user_id)
        else:
            query = query.filter(Preference.user_id.is_(None))
        
        pref = query.first()
        
        # Serialize value to JSON if it's not already a string
        import json
        if not isinstance(value, str):
            value_str = json.dumps(value)
        else:
            # If it's already a string, validate it's valid JSON
            try:
                json.loads(value)
                value_str = value
            except (json.JSONDecodeError, TypeError):
                # If it's not valid JSON, wrap it as a string value
                value_str = json.dumps(value)
        
        if pref:
            pref.value = value_str
            # Optionally update category
            if category is not None and pref.category != category:
                pref.category = category
        else:
            pref = Preference(
                household_id=household_id,
                user_id=user_id,
                key=key,
                value=value_str,
                category=category,
            )
            db.add(pref)
        
        db.commit()
        safe_refresh(db, pref)
        return pref
    
    @staticmethod
    def get(
        db: Session,
        household_id: int,
        key: str,
        user_id: Optional[int] = None,
    ) -> Optional[Preference]:
        """Get a preference value."""
        query = db.query(Preference).filter(
            Preference.household_id == household_id,
            Preference.key == key,
        )
        if user_id is not None:
            query = query.filter(Preference.user_id == user_id)
        else:
            query = query.filter(Preference.user_id.is_(None))
        
        return query.first()
    
    @staticmethod
    def get_all(
        db: Session,
        household_id: int,
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get all preferences as a dictionary."""
        import json
        query = db.query(Preference).filter(
            Preference.household_id == household_id,
        )
        if user_id is not None:
            query = query.filter(Preference.user_id == user_id)
        else:
            # For household-level preferences, user_id must be NULL
            query = query.filter(Preference.user_id.is_(None))
        prefs = query.all()
        result = {}
        for pref in prefs:
            try:
                value = json.loads(pref.value)
            except (json.JSONDecodeError, TypeError):
                value = pref.value
            result[pref.key] = value
        return result
    
    @staticmethod
    def delete(
        db: Session,
        household_id: int,
        key: str,
        user_id: Optional[int] = None,
    ) -> bool:
        """Delete a preference."""
        require_active_session(db)
        query = db.query(Preference).filter(
            Preference.household_id == household_id,
            Preference.key == key,
        )
        if user_id is not None:
            query = query.filter(Preference.user_id == user_id)
        else:
            query = query.filter(Preference.user_id.is_(None))
        
        pref = query.first()
        if pref:
            db.delete(pref)
            db.commit()
            return True
        return False

    _ONBOARDING_KEYS = (
        "first_name",
        "communication_style",
        "interests",
        "daily_schedule",
        "communication_preferences",
        "assistance_preferences",
        "household_context",
        "home_context",
        "notification_preferences",
        "additional_info",
        "onboarding_question_index",
        "onboarding_completed",
    )

    @classmethod
    def delete_onboarding_preferences(
        cls,
        db: Session,
        household_id: int,
        user_id: int,
    ) -> None:
        """Remove all onboarding-related preferences for this household+user."""
        require_active_session(db)
        for key in cls._ONBOARDING_KEYS:
            cls.delete(db, household_id, key, user_id=user_id)


class ContextSnapshotRepository:
    """Repository for context snapshot operations."""
    
    @staticmethod
    def create(
        db: Session,
        household_id: int,
        event_type: str,
        summary: str,
        context_metadata: Optional[Dict[str, Any]] = None,
        user_id: Optional[int] = None,
    ) -> ContextSnapshot:
        """Create a new context snapshot."""
        require_active_session(db)
        import json
        snapshot = ContextSnapshot(
            household_id=household_id,
            user_id=user_id,
            event_type=event_type,
            summary=summary,
            context_metadata=json.dumps(context_metadata) if context_metadata else None,
        )
        db.add(snapshot)
        db.commit()
        safe_refresh(db, snapshot)
        return snapshot
    
    @staticmethod
    def get_recent(
        db: Session,
        household_id: int,
        limit: int = 10,
        user_id: Optional[int] = None,
    ) -> List[ContextSnapshot]:
        """Get recent context snapshots."""
        query = db.query(ContextSnapshot).filter(
            ContextSnapshot.household_id == household_id,
        )
        if user_id is not None:
            query = query.filter(ContextSnapshot.user_id == user_id)
        
        return query.order_by(ContextSnapshot.timestamp.desc()).limit(limit).all()

    @staticmethod
    def get_by_id(db: Session, snapshot_id: int) -> Optional[ContextSnapshot]:
        """Get a context snapshot by id."""
        return db.query(ContextSnapshot).filter(ContextSnapshot.id == snapshot_id).first()

    @staticmethod
    def delete(db: Session, snapshot_id: int, user_id: int) -> bool:
        """Delete a context snapshot if it belongs to the given user. Returns True if deleted."""
        snapshot = ContextSnapshotRepository.get_by_id(db, snapshot_id)
        if not snapshot or snapshot.user_id != user_id:
            return False
        db.delete(snapshot)
        db.commit()
        return True


class CronJobRepository:
    """Repository for cron job records."""

    @staticmethod
    def upsert(db: Session, job_id: str, user_id: str, created_at: datetime, job_json: Dict[str, Any]) -> CronJobRecord:
        """Insert or update a cron job by id."""
        require_active_session(db)
        record = db.query(CronJobRecord).filter(CronJobRecord.id == job_id).first()
        if record:
            record.user_id = user_id
            record.created_at = created_at
            record.job_json = job_json
        else:
            record = CronJobRecord(
                id=job_id,
                user_id=user_id,
                created_at=created_at,
                job_json=job_json,
            )
            db.add(record)
        db.commit()
        safe_refresh(db, record)
        return record

    @staticmethod
    def delete_missing(db: Session, keep_ids: List[str]) -> int:
        """Delete jobs not in keep_ids. Returns number deleted."""
        require_active_session(db)
        keep_set = set(keep_ids)
        q = db.query(CronJobRecord)
        if keep_set:
            q = q.filter(CronJobRecord.id.notin_(keep_set))
        deleted = q.delete(synchronize_session=False)
        db.commit()
        return deleted or 0

    @staticmethod
    def list_all(db: Session) -> List[CronJobRecord]:
        """Return all cron jobs."""
        return db.query(CronJobRecord).all()

    @staticmethod
    def list_by_user(db: Session, user_id: str) -> List[CronJobRecord]:
        """Return cron jobs for a user."""
        return db.query(CronJobRecord).filter(CronJobRecord.user_id == user_id).all()

    @staticmethod
    def get_by_id(db: Session, job_id: str) -> Optional[CronJobRecord]:
        """Return a cron job by id."""
        return db.query(CronJobRecord).filter(CronJobRecord.id == job_id).first()

    @staticmethod
    def count_jobs_created_today_by_user(db: Session, user_id: str) -> int:
        """Count jobs created today (UTC) for a user."""
        require_active_session(db)
        today = datetime.utcnow().date()
        start = datetime.combine(today, datetime.min.time())
        end = datetime.combine(today, datetime.max.time())
        return (
            db.query(func.count(CronJobRecord.id))
            .filter(
                CronJobRecord.user_id == user_id,
                CronJobRecord.created_at >= start,
                CronJobRecord.created_at <= end,
            )
            .scalar()
            or 0
        )


class CronRunRepository:
    """Repository for cron run records."""

    @staticmethod
    def append_run(db: Session, job_id: str, timestamp: datetime, run_json: Dict[str, Any]) -> CronRunRecord:
        """Append a run record for a job."""
        require_active_session(db)
        record = CronRunRecord(
            job_id=job_id,
            timestamp=timestamp,
            run_json=run_json,
        )
        db.add(record)
        db.commit()
        safe_refresh(db, record)
        return record

    @staticmethod
    def list_runs(db: Session, job_id: str, limit: int = 100) -> List[CronRunRecord]:
        """List run records for a job, oldest to newest."""
        q = db.query(CronRunRecord).filter(CronRunRecord.job_id == job_id).order_by(CronRunRecord.timestamp.desc())
        if limit:
            q = q.limit(limit)
        records = q.all()
        return list(reversed(records))

class AuditLogRepository:
    """Repository for audit log operations."""
    
    @staticmethod
    def create(
        db: Session,
        household_id: int,
        user_id: Optional[int],
        action: str,
        resource_type: str,
        resource_id: Optional[int],
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """Create a new audit log entry."""
        require_active_session(db)
        import json
        log = AuditLog(
            household_id=household_id,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=json.dumps(details) if details else None,
        )
        db.add(log)
        db.commit()
        safe_refresh(db, log)
        return log
    
    @staticmethod
    def get_recent(
        db: Session,
        household_id: int,
        limit: int = 50,
        user_id: Optional[int] = None,
    ) -> List[AuditLog]:
        """Get recent audit log entries."""
        query = db.query(AuditLog).filter(
            AuditLog.household_id == household_id,
        )
        if user_id is not None:
            query = query.filter(AuditLog.user_id == user_id)
        
        return query.order_by(AuditLog.timestamp.desc()).limit(limit).all()
    
    @staticmethod
    def get_by_resource(
        db: Session,
        household_id: int,
        resource_type: str,
        resource_id: int,
    ) -> List[AuditLog]:
        """Get audit logs for a specific resource."""
        return (
            db.query(AuditLog)
            .filter(
                AuditLog.household_id == household_id,
                AuditLog.resource_type == resource_type,
                AuditLog.resource_id == resource_id,
            )
            .order_by(AuditLog.timestamp.desc())
            .all()
        )


class ChatMessageRepository:
    """Repository for chat message operations."""
    
    @staticmethod
    def create(
        db: Session,
        household_id: int,
        user_id: Optional[int],
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ChatMessage:
        """Create a new chat message."""
        require_active_session(db)
        message = ChatMessage(
            household_id=household_id,
            user_id=user_id,
            role=role,
            content=content,
            message_metadata=metadata,
        )
        db.add(message)
        db.commit()
        safe_refresh(db, message)
        return message
    
    @staticmethod
    def get_recent(
        db: Session,
        household_id: int,
        limit: int = 50,
        user_id: Optional[int] = None,
    ) -> List[ChatMessage]:
        """Get recent chat messages."""
        query = db.query(ChatMessage).filter(
            ChatMessage.household_id == household_id,
        )
        if user_id is not None:
            query = query.filter(ChatMessage.user_id == user_id)
        
        return query.order_by(ChatMessage.created_at.desc()).limit(limit).all()
    
    @staticmethod
    def get_conversation_history(
        db: Session,
        household_id: int,
        user_id: Optional[int],
        limit: int = 50,
    ) -> List[Dict[str, str]]:
        """
        Get recent messages as a simple role/content history for the agent.
        Returned in chronological order (oldest first).
        """
        require_active_session(db)
        query = db.query(ChatMessage).filter(
            ChatMessage.household_id == household_id,
        )
        if user_id is not None:
            query = query.filter(ChatMessage.user_id == user_id)
        
        messages = (
            query.order_by(ChatMessage.created_at.asc())
            .limit(limit)
            .all()
        )
        history: List[Dict[str, str]] = []
        for msg in messages:
            history.append(
                {
                    "role": msg.role,
                    "content": msg.content,
                }
            )
        return history


class SystemConfigRepository:
    """Repository for system configuration operations."""
    
    @staticmethod
    def get(db: Session, key: str) -> Optional[SystemConfig]:
        """Get system config by key."""
        return db.query(SystemConfig).filter(SystemConfig.key == key).first()
    
    @staticmethod
    def set(db: Session, key: str, value: Any, category: str = "general") -> SystemConfig:
        """Set system config value. category is used for new records (e.g. wifi, llm, device, privacy)."""
        import json
        config = SystemConfigRepository.get(db, key)
        
        # Serialize value to JSON if it's not already a string
        if not isinstance(value, str):
            value_str = json.dumps(value)
        else:
            # If it's already a string, validate it's valid JSON
            try:
                json.loads(value)
                value_str = value
            except (json.JSONDecodeError, TypeError):
                # If it's not valid JSON, wrap it as a string value
                value_str = json.dumps(value)
        
        if config:
            config.value = value_str
            if category != "general":
                config.category = category
        else:
            config = SystemConfig(key=key, value=value_str, category=category)
            db.add(config)
        
        db.commit()
        safe_refresh(db, config)
        return config
    
    @staticmethod
    def get_all(db: Session) -> Dict[str, Any]:
        """Get all system config as a dictionary."""
        import json
        configs = db.query(SystemConfig).all()
        result = {}
        for config in configs:
            try:
                value = json.loads(config.value)
            except (json.JSONDecodeError, TypeError):
                value = config.value
            result[config.key] = value
        return result
    
    @staticmethod
    def delete(db: Session, key: str) -> bool:
        """Delete system config."""
        require_active_session(db)
        config = SystemConfigRepository.get(db, key)
        if config:
            db.delete(config)
            db.commit()
            return True
        return False


class DailyRequestCountRepository:
    """Repository for daily request count operations."""
    
    @staticmethod
    def increment(db: Session, household_id: int) -> DailyRequestCount:
        """Increment today's request count for a household."""
        require_active_session(db)
        # #region agent log
        try:
            import json as _json, time as _time
            with open('/Users/karelgustin/Neuroion/Neuroion/.cursor/debug.log', 'a') as _f:
                _f.write(_json.dumps({
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "H2",
                    "location": "repository.py:543",
                    "message": "DailyRequestCountRepository.increment entry",
                    "data": {"household_id": household_id},
                    "timestamp": int(_time.time() * 1000),
                }) + "\n")
        except Exception:
            pass
        # #endregion
        # Use a date-only value at midnight UTC for the 'date' column
        today = datetime.utcnow().date()
        today_start = datetime.combine(today, datetime.min.time())
        
        count = (
            db.query(DailyRequestCount)
            .filter(
                DailyRequestCount.household_id == household_id,
                DailyRequestCount.date == today_start,
            )
            .first()
        )
        
        if count:
            count.count += 1
        else:
            count = DailyRequestCount(
                household_id=household_id,
                date=today_start,
                count=1,
            )
            db.add(count)
            db.commit()
            safe_refresh(db, count)
        
        count.updated_at = datetime.utcnow()
        db.commit()
        safe_refresh(db, count)
        return count
    
    @staticmethod
    def get_today_count(db: Session, household_id: int) -> int:
        """Get today's request count for a household."""
        require_active_session(db)
        today = datetime.utcnow().date()
        today_start = datetime.combine(today, datetime.min.time())
        
        count = (
            db.query(DailyRequestCount)
            .filter(
                DailyRequestCount.household_id == household_id,
                DailyRequestCount.date == today_start,
            )
            .first()
        )
        return count.count if count else 0


class UserIntegrationRepository:
    """Repository for user integration operations."""
    
    @staticmethod
    def create(
        db: Session,
        user_id: int,
        provider: str,
        access_token: str,
        refresh_token: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        permissions: Optional[Dict[str, Any]] = None,
    ) -> UserIntegration:
        """Create a new user integration."""
        require_active_session(db)
        import json
        integration = UserIntegration(
            user_id=user_id,
            provider=provider,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
            permissions=json.dumps(permissions) if permissions else None,
        )
        db.add(integration)
        db.commit()
        safe_refresh(db, integration)
        return integration
    
    @staticmethod
    def get_by_user_and_provider(
        db: Session,
        user_id: int,
        provider: str,
    ) -> Optional[UserIntegration]:
        """Get integration by user and provider."""
        return (
            db.query(UserIntegration)
            .filter(
                UserIntegration.user_id == user_id,
                UserIntegration.provider == provider,
            )
            .first()
        )
    
    @staticmethod
    def update_tokens(
        db: Session,
        user_id: int,
        provider: str,
        access_token: str,
        refresh_token: Optional[str] = None,
        expires_at: Optional[datetime] = None,
    ) -> bool:
        """Update integration tokens."""
        require_active_session(db)
        integration = UserIntegrationRepository.get_by_user_and_provider(
            db, user_id, provider
        )
        if integration:
            integration.access_token = access_token
            if refresh_token is not None:
                integration.refresh_token = refresh_token
            if expires_at is not None:
                integration.expires_at = expires_at
            db.commit()
            return True
        return False


class DashboardLinkRepository:
    """Repository for dashboard link operations."""
    
    @staticmethod
    def create(
        db: Session,
        user_id: int,
        token: str,
        expires_at: datetime,
    ) -> DashboardLink:
        """Create a new dashboard link."""
        require_active_session(db)
        link = DashboardLink(
            user_id=user_id,
            token=token,
            expires_at=expires_at,
        )
        db.add(link)
        db.commit()
        safe_refresh(db, link)
        return link
    
    @staticmethod
    def get_by_token(db: Session, token: str) -> Optional[DashboardLink]:
        """Get dashboard link by token (valid if expires_at is null or in future)."""
        from sqlalchemy import or_
        return (
            db.query(DashboardLink)
            .filter(
                DashboardLink.token == token,
                or_(
                    DashboardLink.expires_at.is_(None),
                    DashboardLink.expires_at > datetime.utcnow(),
                ),
            )
            .first()
        )

    @staticmethod
    def get_or_create(db: Session, user_id: int) -> DashboardLink:
        """Get existing dashboard link for user or create one (long-lived token)."""
        require_active_session(db)
        link = db.query(DashboardLink).filter(DashboardLink.user_id == user_id).first()
        if link:
            return link
        import secrets
        token = secrets.token_urlsafe(32)
        # Long-lived: 1 year
        expires_at = datetime.utcnow() + timedelta(days=365)
        return DashboardLinkRepository.create(db, user_id, token, expires_at)
    
    @staticmethod
    def update_last_accessed(db: Session, token: str) -> Optional[DashboardLink]:
        """Update last accessed timestamp."""
        require_active_session(db)
        link = DashboardLinkRepository.get_by_token(db, token)
        if link:
            link.last_accessed_at = datetime.utcnow()
            db.commit()
            safe_refresh(db, link)
        return link


class LoginCodeRepository:
    """Repository for login code operations."""

    @staticmethod
    def create_for_user(
        db: Session,
        user_id: int,
        expires_in_seconds: int = 60,
    ) -> LoginCode:
        """Create a new login code (4-6 digits) for the user. Returns the LoginCode."""
        import secrets
        code = f"{secrets.randbelow(10**6):06d}"  # 6-digit code
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in_seconds)
        return LoginCodeRepository.create(db, user_id, code, expires_at)

    @staticmethod
    def create(
        db: Session,
        user_id: int,
        code: str,
        expires_at: datetime,
    ) -> LoginCode:
        """Create a new login code."""
        require_active_session(db)
        login_code = LoginCode(
            user_id=user_id,
            code=code,
            expires_at=expires_at,
        )
        db.add(login_code)
        db.commit()
        safe_refresh(db, login_code)
        return login_code

    @staticmethod
    def verify(db: Session, code: str) -> Optional[int]:
        """Verify code, mark as used, and return user_id. Returns None if invalid/expired."""
        return LoginCodeRepository.mark_used(db, code)

    @staticmethod
    def get_by_code(db: Session, code: str) -> Optional[LoginCode]:
        """Get login code by code string."""
        return (
            db.query(LoginCode)
            .filter(
                LoginCode.code == code,
                LoginCode.expires_at > datetime.utcnow(),
                LoginCode.used_at.is_(None),
            )
            .first()
        )
    
    @staticmethod
    def mark_used(db: Session, code: str) -> Optional[int]:
        """Mark login code as used and return user_id."""
        require_active_session(db)
        login_code = LoginCodeRepository.get_by_code(db, code)
        if login_code:
            login_code.used_at = datetime.utcnow()
            db.commit()
            return login_code.user_id
        return None
    
    @staticmethod
    def cleanup_expired(db: Session) -> int:
        """Delete expired login codes."""
        require_active_session(db)
        deleted = (
            db.query(LoginCode)
            .filter(LoginCode.expires_at < datetime.utcnow())
            .delete()
        )
        db.commit()
        return deleted


class DeviceConfigRepository:
    """Repository for device configuration operations."""
    
    @staticmethod
    def get_or_create(db: Session) -> DeviceConfig:
        """Get or create device config (singleton)."""
        require_active_session(db)
        config = db.query(DeviceConfig).first()
        if not config:
            config = DeviceConfig()
            db.add(config)
            try:
                # Commit immediately for singleton to avoid threading issues
                db.commit()
                safe_refresh(db, config)
            except Exception:
                db.rollback()
                raise
        return config
    
    @staticmethod
    def update(
        db: Session,
        wifi_configured: Optional[bool] = None,
        hostname: Optional[str] = None,
        setup_completed: Optional[bool] = None,
        retention_policy: Optional[Dict[str, Any]] = None,
    ) -> DeviceConfig:
        """Update device configuration."""
        require_active_session(db)
        config = DeviceConfigRepository.get_or_create(db)
        
        # Check if any changes are needed
        needs_update = False
        if wifi_configured is not None and config.wifi_configured != wifi_configured:
            config.wifi_configured = wifi_configured
            needs_update = True
        if hostname is not None and config.hostname != hostname:
            config.hostname = hostname
            needs_update = True
        if setup_completed is not None and config.setup_completed != setup_completed:
            config.setup_completed = setup_completed
            needs_update = True
        if retention_policy is not None and config.retention_policy != retention_policy:
            config.retention_policy = retention_policy
            needs_update = True
        
        if needs_update:
            config.updated_at = datetime.utcnow()
            try:
                db.commit()
                safe_refresh(db, config)
            except Exception:
                db.rollback()
                raise
        
        return config
    
    @staticmethod
    def get(db: Session) -> Optional[DeviceConfig]:
        """Get device configuration."""
        return db.query(DeviceConfig).first()


class JoinTokenRepository:
    """Repository for join token operations."""
    
    @staticmethod
    def create(
        db: Session,
        token: str,
        household_id: int,
        created_by_member_id: int,
        expires_at: datetime,
    ) -> JoinToken:
        """Create a new join token."""
        join_token = JoinToken(
            token=token,
            household_id=household_id,
            created_by_member_id=created_by_member_id,
            expires_at=expires_at,
        )
        db.add(join_token)
        db.commit()
        safe_refresh(db, join_token)
        return join_token
    
    @staticmethod
    def get_by_token(db: Session, token: str) -> Optional[JoinToken]:
        """Get join token by token string."""
        return (
            db.query(JoinToken)
            .filter(
                JoinToken.token == token,
                JoinToken.expires_at > datetime.utcnow(),
                JoinToken.used_at.is_(None),
            )
            .first()
        )
    
    @staticmethod
    def mark_used(db: Session, token: str) -> Optional[JoinToken]:
        """Mark join token as used."""
        require_active_session(db)
        join_token = JoinTokenRepository.get_by_token(db, token)
        if join_token:
            join_token.used_at = datetime.utcnow()
            db.commit()
            safe_refresh(db, join_token)
        return join_token

    @staticmethod
    def consume(db: Session, token: str) -> Optional[JoinToken]:
        """Verify, mark as used, and return the join token. Returns None if invalid."""
        join_token = JoinTokenRepository.get_by_token(db, token)
        if not join_token:
            return None
        join_token.used_at = datetime.utcnow()
        try:
            db.commit()
            safe_refresh(db, join_token)
            return join_token
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def get_active_tokens(
        db: Session,
        household_id: Optional[int] = None,
        created_by_member_id: Optional[int] = None,
    ) -> List[JoinToken]:
        """Get active (unused, not expired) join tokens."""
        q = db.query(JoinToken).filter(
            JoinToken.used_at.is_(None),
            JoinToken.expires_at > datetime.utcnow(),
        )
        if household_id is not None:
            q = q.filter(JoinToken.household_id == household_id)
        if created_by_member_id is not None:
            q = q.filter(JoinToken.created_by_member_id == created_by_member_id)
        return q.all()

    @staticmethod
    def cleanup_expired(db: Session) -> int:
        """Delete expired join tokens."""
        require_active_session(db)
        deleted = (
            db.query(JoinToken)
            .filter(JoinToken.expires_at < datetime.utcnow())
            .delete()
        )
        db.commit()
        return deleted
