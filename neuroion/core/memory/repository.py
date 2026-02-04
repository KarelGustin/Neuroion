"""
Repository layer for database operations.

Provides high-level methods for CRUD operations on all models.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from neuroion.core.memory.models import (
    Household,
    User,
    Preference,
    ContextSnapshot,
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
        household = HouseholdRepository.get_by_id(db, household_id)
        if household:
            household.name = name
            db.commit()
        return household
    
    @staticmethod
    def delete(db: Session, household_id: int) -> bool:
        """Delete household and all related data."""
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
    ) -> User:
        """Create a new user."""
        user = User(
            household_id=household_id,
            name=name,
            role=role,
            device_id=device_id,
            device_type=device_type,
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
    ) -> Optional[User]:
        """Update user."""
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
        
        db.commit()
        return user
    
    @staticmethod
    def delete(db: Session, user_id: int) -> bool:
        """Delete user."""
        user = UserRepository.get_by_id(db, user_id)
        if user:
            db.delete(user)
            db.commit()
            return True
        return False


class PreferenceRepository:
    """Repository for preference operations."""
    
    @staticmethod
    def set(
        db: Session,
        household_id: int,
        key: str,
        value: Any,
        user_id: Optional[int] = None,
    ) -> Preference:
        """Set a preference value."""
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
        else:
            pref = Preference(
                household_id=household_id,
                user_id=user_id,
                key=key,
                value=value_str,
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
        import threading
        thread_id = threading.get_ident()
        # #region agent log
        try:
            with open('/Users/karelgustin/Neuroion/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"repository.py:179","message":"PreferenceRepository.get_all entry","data":{"thread_id":thread_id,"household_id":household_id,"user_id":user_id},"timestamp":int(__import__('time').time()*1000)})+'\n')
        except: pass
        # #endregion
        
        query = db.query(Preference).filter(
            Preference.household_id == household_id,
        )
        
        if user_id is not None:
            query = query.filter(Preference.user_id == user_id)
        else:
            # For household-level preferences, user_id must be NULL
            query = query.filter(Preference.user_id.is_(None))
        
        # #region agent log
        try:
            with open('/Users/karelgustin/Neuroion/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"repository.py:191","message":"Before query.all()","data":{"thread_id":thread_id,"session_id":id(db)},"timestamp":int(__import__('time').time()*1000)})+'\n')
        except: pass
        # #endregion
        
        prefs = query.all()
        
        # #region agent log
        try:
            with open('/Users/karelgustin/Neuroion/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"repository.py:194","message":"After query.all()","data":{"thread_id":thread_id,"count":len(prefs),"session_id":id(db)},"timestamp":int(__import__('time').time()*1000)})+'\n')
        except: pass
        # #endregion
        
        result = {}
        for i, pref in enumerate(prefs):
            # #region agent log
            try:
                with open('/Users/karelgustin/Neuroion/.cursor/debug.log', 'a') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"repository.py:197","message":"Before JSON parse","data":{"thread_id":thread_id,"index":i,"pref_id":id(pref),"session_id":id(db)},"timestamp":int(__import__('time').time()*1000)})+'\n')
            except: pass
            # #endregion
            try:
                # Try to parse as JSON first
                value = json.loads(pref.value)
            except (json.JSONDecodeError, TypeError):
                # If not valid JSON, use as string
                value = pref.value
            # #region agent log
            try:
                with open('/Users/karelgustin/Neuroion/.cursor/debug.log', 'a') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"repository.py:203","message":"After JSON parse","data":{"thread_id":thread_id,"index":i,"pref_id":id(pref)},"timestamp":int(__import__('time').time()*1000)})+'\n')
            except: pass
            # #endregion
            result[pref.key] = value
        
        # #region agent log
        try:
            with open('/Users/karelgustin/Neuroion/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"repository.py:207","message":"PreferenceRepository.get_all exit","data":{"thread_id":thread_id,"count":len(prefs)},"timestamp":int(__import__('time').time()*1000)})+'\n')
        except: pass
        # #endregion
        
        return result
    
    @staticmethod
    def delete(
        db: Session,
        household_id: int,
        key: str,
        user_id: Optional[int] = None,
    ) -> bool:
        """Delete a preference."""
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
    ) -> ChatMessage:
        """Create a new chat message."""
        message = ChatMessage(
            household_id=household_id,
            user_id=user_id,
            role=role,
            content=content,
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
        
        return query.order_by(ChatMessage.timestamp.desc()).limit(limit).all()


class SystemConfigRepository:
    """Repository for system configuration operations."""
    
    @staticmethod
    def get(db: Session, key: str) -> Optional[SystemConfig]:
        """Get system config by key."""
        return db.query(SystemConfig).filter(SystemConfig.key == key).first()
    
    @staticmethod
    def set(db: Session, key: str, value: Any) -> SystemConfig:
        """Set system config value."""
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
        else:
            config = SystemConfig(key=key, value=value_str)
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
        config = SystemConfigRepository.get(db, key)
        if config:
            db.delete(config)
            db.commit()
            return True
        return False


class DailyRequestCountRepository:
    """Repository for daily request count operations."""
    
    @staticmethod
    def increment(db: Session, date: datetime) -> DailyRequestCount:
        """Increment daily request count."""
        date_str = date.strftime("%Y-%m-%d")
        count = (
            db.query(DailyRequestCount)
            .filter(DailyRequestCount.date == date_str)
            .first()
        )
        
        if count:
            count.count += 1
            count.updated_at = datetime.utcnow()
        else:
            count = DailyRequestCount(date=date_str, count=1)
            db.add(count)
            db.commit()
            safe_refresh(db, count)
        
        count.updated_at = datetime.utcnow()
        db.commit()
        safe_refresh(db, count)
        return count
    
    @staticmethod
    def get_today(db: Session) -> Optional[DailyRequestCount]:
        """Get today's request count."""
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        return (
            db.query(DailyRequestCount)
            .filter(DailyRequestCount.date == date_str)
            .first()
        )


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
        """Get dashboard link by token."""
        return (
            db.query(DashboardLink)
            .filter(
                DashboardLink.token == token,
                DashboardLink.expires_at > datetime.utcnow(),
            )
            .first()
        )
    
    @staticmethod
    def update_last_accessed(db: Session, token: str) -> Optional[DashboardLink]:
        """Update last accessed timestamp."""
        link = DashboardLinkRepository.get_by_token(db, token)
        if link:
            link.last_accessed_at = datetime.utcnow()
            db.commit()
            safe_refresh(db, link)
        return link


class LoginCodeRepository:
    """Repository for login code operations."""
    
    @staticmethod
    def create(
        db: Session,
        user_id: int,
        code: str,
        expires_at: datetime,
    ) -> LoginCode:
        """Create a new login code."""
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
        login_code = LoginCodeRepository.get_by_code(db, code)
        if login_code:
            login_code.used_at = datetime.utcnow()
            db.commit()
            return login_code.user_id
        return None
    
    @staticmethod
    def cleanup_expired(db: Session) -> int:
        """Delete expired login codes."""
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
        join_token = JoinTokenRepository.get_by_token(db, token)
        if join_token:
            join_token.used_at = datetime.utcnow()
            db.commit()
            safe_refresh(db, join_token)
        return join_token
    
    @staticmethod
    def cleanup_expired(db: Session) -> int:
        """Delete expired join tokens."""
        deleted = (
            db.query(JoinToken)
            .filter(JoinToken.expires_at < datetime.utcnow())
            .delete()
        )
        db.commit()
        return deleted
