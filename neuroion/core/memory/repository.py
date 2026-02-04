"""
Repository layer for database operations.

Provides high-level CRUD operations and query helpers for all entities.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_

from neuroion.core.memory.models import (
    Household, User, Preference, ContextSnapshot, AuditLog, ChatMessage, SystemConfig,
    DailyRequestCount, UserIntegration, DashboardLink
)


class HouseholdRepository:
    """Repository for household operations."""
    
    @staticmethod
    def create(db: Session, name: str) -> Household:
        """Create a new household."""
        household = Household(name=name)
        db.add(household)
        db.commit()
        db.refresh(household)
        return household
    
    @staticmethod
    def get_by_id(db: Session, household_id: int) -> Optional[Household]:
        """Get household by ID."""
        return db.query(Household).filter(Household.id == household_id).first()
    
    @staticmethod
    def get_all(db: Session) -> List[Household]:
        """Get all households."""
        return db.query(Household).all()


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
        db.commit()
        db.refresh(user)
        return user
    
    @staticmethod
    def get_by_id(db: Session, user_id: int) -> Optional[User]:
        """Get user by ID."""
        return db.query(User).filter(User.id == user_id).first()
    
    @staticmethod
    def get_by_device_id(db: Session, device_id: str) -> Optional[User]:
        """Get user by device ID (for pairing)."""
        return db.query(User).filter(User.device_id == device_id).first()
    
    @staticmethod
    def get_by_household(db: Session, household_id: int) -> List[User]:
        """Get all users in a household."""
        return db.query(User).filter(User.household_id == household_id).all()
    
    @staticmethod
    def update_last_seen(db: Session, user_id: int) -> None:
        """Update user's last seen timestamp."""
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.last_seen_at = datetime.utcnow()
            db.commit()


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
        """Set a preference (creates or updates)."""
        import json
        
        # Check if exists
        query = db.query(Preference).filter(
            Preference.household_id == household_id,
            Preference.key == key,
        )
        if user_id:
            query = query.filter(Preference.user_id == user_id)
        else:
            query = query.filter(Preference.user_id.is_(None))
        
        pref = query.first()
        
        # Always serialize non-string values to JSON
        if isinstance(value, str):
            try:
                json.loads(value)  # Validate it's valid JSON
                serialized_value = value  # Already valid JSON string
            except (json.JSONDecodeError, TypeError):
                serialized_value = value  # Plain string, keep as-is
        else:
            # For dict, list, or other types, always serialize to JSON
            serialized_value = json.dumps(value)
        
        if pref:
            pref.value = serialized_value
            pref.category = category or pref.category
            pref.updated_at = datetime.utcnow()
        else:
            pref = Preference(
                household_id=household_id,
                user_id=user_id,
                key=key,
                value=serialized_value,
                category=category,
            )
            db.add(pref)
        
        db.commit()
        db.refresh(pref)
        return pref
    
    @staticmethod
    def get(
        db: Session,
        household_id: int,
        key: str,
        user_id: Optional[int] = None,
    ) -> Optional[Preference]:
        """Get a preference."""
        import json
        
        query = db.query(Preference).filter(
            Preference.household_id == household_id,
            Preference.key == key,
        )
        if user_id:
            query = query.filter(Preference.user_id == user_id)
        else:
            query = query.filter(Preference.user_id.is_(None))
        
        pref = query.first()
        if pref:
            try:
                pref.value = json.loads(pref.value)
            except (json.JSONDecodeError, TypeError):
                pass
        return pref
    
    @staticmethod
    def get_all(
        db: Session,
        household_id: int,
        user_id: Optional[int] = None,
        category: Optional[str] = None,
    ) -> List[Preference]:
        """Get all preferences matching criteria."""
        import json
        
        query = db.query(Preference).filter(Preference.household_id == household_id)
        if user_id:
            query = query.filter(Preference.user_id == user_id)
        if category:
            query = query.filter(Preference.category == category)
        
        prefs = query.all()
        for pref in prefs:
            try:
                pref.value = json.loads(pref.value)
            except (json.JSONDecodeError, TypeError):
                pass
        return prefs


class ContextSnapshotRepository:
    """Repository for context snapshot operations."""
    
    @staticmethod
    def create(
        db: Session,
        household_id: int,
        event_type: str,
        summary: str,
        user_id: Optional[int] = None,
        event_subtype: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
    ) -> ContextSnapshot:
        """Create a context snapshot."""
        snapshot = ContextSnapshot(
            household_id=household_id,
            user_id=user_id,
            event_type=event_type,
            event_subtype=event_subtype,
            summary=summary,
            context_metadata=metadata,
            timestamp=timestamp or datetime.utcnow(),
        )
        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)
        return snapshot
    
    @staticmethod
    def get_recent(
        db: Session,
        household_id: int,
        limit: int = 50,
        user_id: Optional[int] = None,
        event_type: Optional[str] = None,
    ) -> List[ContextSnapshot]:
        """Get recent context snapshots."""
        query = db.query(ContextSnapshot).filter(
            ContextSnapshot.household_id == household_id
        )
        
        if user_id:
            query = query.filter(ContextSnapshot.user_id == user_id)
        if event_type:
            query = query.filter(ContextSnapshot.event_type == event_type)
        
        return query.order_by(desc(ContextSnapshot.timestamp)).limit(limit).all()


class AuditLogRepository:
    """Repository for audit log operations."""
    
    @staticmethod
    def create(
        db: Session,
        household_id: int,
        action_type: str,
        action_name: str,
        reasoning: Optional[str] = None,
        user_id: Optional[int] = None,
        input_data: Optional[Dict[str, Any]] = None,
        status: str = "pending",
    ) -> AuditLog:
        """Create an audit log entry."""
        log = AuditLog(
            household_id=household_id,
            user_id=user_id,
            action_type=action_type,
            action_name=action_name,
            reasoning=reasoning,
            input_data=input_data,
            status=status,
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        return log
    
    @staticmethod
    def update_status(
        db: Session,
        log_id: int,
        status: str,
        output_data: Optional[Dict[str, Any]] = None,
    ) -> Optional[AuditLog]:
        """Update audit log status."""
        log = db.query(AuditLog).filter(AuditLog.id == log_id).first()
        if not log:
            return None
        
        log.status = status
        if output_data:
            log.output_data = output_data
        
        if status == "confirmed":
            log.confirmed_at = datetime.utcnow()
        elif status == "executed":
            log.executed_at = datetime.utcnow()
        
        db.commit()
        db.refresh(log)
        return log
    
    @staticmethod
    def get_recent(
        db: Session,
        household_id: int,
        limit: int = 100,
        action_type: Optional[str] = None,
    ) -> List[AuditLog]:
        """Get recent audit logs."""
        query = db.query(AuditLog).filter(AuditLog.household_id == household_id)
        
        if action_type:
            query = query.filter(AuditLog.action_type == action_type)
        
        return query.order_by(desc(AuditLog.created_at)).limit(limit).all()


class ChatMessageRepository:
    """Repository for chat message operations."""
    
    @staticmethod
    def create(
        db: Session,
        household_id: int,
        user_id: int,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ChatMessage:
        """Create a chat message."""
        message = ChatMessage(
            household_id=household_id,
            user_id=user_id,
            role=role,
            content=content,
            message_metadata=metadata,
        )
        db.add(message)
        db.commit()
        db.refresh(message)
        return message
    
    @staticmethod
    def get_conversation_history(
        db: Session,
        household_id: int,
        user_id: int,
        limit: int = 20,
    ) -> List[Dict[str, str]]:
        """
        Get conversation history for a user.
        
        Returns:
            List of message dicts with 'role' and 'content' for LLM
        """
        messages = db.query(ChatMessage).filter(
            ChatMessage.household_id == household_id,
            ChatMessage.user_id == user_id,
        ).order_by(desc(ChatMessage.created_at)).limit(limit).all()
        
        # Reverse to get chronological order (oldest first)
        messages.reverse()
        
        return [
            {
                "role": msg.role,
                "content": msg.content,
            }
            for msg in messages
        ]
    
    @staticmethod
    def get_recent(
        db: Session,
        household_id: int,
        limit: int = 50,
        user_id: Optional[int] = None,
    ) -> List[ChatMessage]:
        """Get recent chat messages."""
        query = db.query(ChatMessage).filter(
            ChatMessage.household_id == household_id
        )
        
        if user_id:
            query = query.filter(ChatMessage.user_id == user_id)
        
        return query.order_by(desc(ChatMessage.created_at)).limit(limit).all()


class SystemConfigRepository:
    """Repository for system configuration operations."""
    
    @staticmethod
    def set(
        db: Session,
        key: str,
        value: Any,
        category: str,
    ) -> SystemConfig:
        """Set a system config value (creates or updates)."""
        import json
        
        # Always serialize non-string values to JSON
        # For strings, check if they're already JSON, if not keep as-is
        if isinstance(value, str):
            # If it's already a string, try to parse it to see if it's JSON
            # If it's valid JSON, keep it as-is, otherwise it's a plain string
            try:
                json.loads(value)  # Validate it's valid JSON
                serialized_value = value  # Already valid JSON string
            except (json.JSONDecodeError, TypeError):
                serialized_value = value  # Plain string, keep as-is
        else:
            # For dict, list, or other types, always serialize to JSON
            serialized_value = json.dumps(value)
        
        config = db.query(SystemConfig).filter(SystemConfig.key == key).first()
        
        if config:
            config.value = serialized_value
            config.category = category
            config.updated_at = datetime.utcnow()
        else:
            config = SystemConfig(
                key=key,
                value=serialized_value,
                category=category,
            )
            db.add(config)
        
        db.commit()
        db.refresh(config)
        return config
    
    @staticmethod
    def get(db: Session, key: str) -> Optional[SystemConfig]:
        """Get a system config by key."""
        import json
        
        config = db.query(SystemConfig).filter(SystemConfig.key == key).first()
        if config:
            try:
                config.value = json.loads(config.value)
            except (json.JSONDecodeError, TypeError):
                pass
        return config
    
    @staticmethod
    def get_by_category(db: Session, category: str) -> List[SystemConfig]:
        """Get all configs in a category."""
        import json
        
        configs = db.query(SystemConfig).filter(SystemConfig.category == category).all()
        for config in configs:
            try:
                config.value = json.loads(config.value)
            except (json.JSONDecodeError, TypeError):
                pass
        return configs
    
    @staticmethod
    def get_all(db: Session) -> List[SystemConfig]:
        """Get all system configs."""
        import json
        
        configs = db.query(SystemConfig).all()
        for config in configs:
            try:
                config.value = json.loads(config.value)
            except (json.JSONDecodeError, TypeError):
                pass
        return configs
    
    @staticmethod
    def delete(db: Session, key: str) -> bool:
        """Delete a system config."""
        config = db.query(SystemConfig).filter(SystemConfig.key == key).first()
        if config:
            db.delete(config)
            db.commit()
            return True
        return False


class DailyRequestCountRepository:
    """Repository for daily request count operations."""
    
    @staticmethod
    def get_or_create_today(db: Session, household_id: int) -> DailyRequestCount:
        """Get or create today's request count for a household."""
        from datetime import date
        today = datetime.combine(date.today(), datetime.min.time())
        
        count = db.query(DailyRequestCount).filter(
            DailyRequestCount.household_id == household_id,
            DailyRequestCount.date == today,
        ).first()
        
        if not count:
            count = DailyRequestCount(
                household_id=household_id,
                date=today,
                count=0,
            )
            db.add(count)
            db.commit()
            db.refresh(count)
        
        return count
    
    @staticmethod
    def increment(db: Session, household_id: int) -> DailyRequestCount:
        """Increment today's request count for a household."""
        count = DailyRequestCountRepository.get_or_create_today(db, household_id)
        count.count += 1
        count.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(count)
        return count
    
    @staticmethod
    def get_today_count(db: Session, household_id: int) -> int:
        """Get today's request count for a household."""
        from datetime import date
        today = datetime.combine(date.today(), datetime.min.time())
        
        count = db.query(DailyRequestCount).filter(
            DailyRequestCount.household_id == household_id,
            DailyRequestCount.date == today,
        ).first()
        
        return count.count if count else 0


class UserIntegrationRepository:
    """Repository for user integration operations."""
    
    @staticmethod
    def create_or_update(
        db: Session,
        user_id: int,
        integration_type: str,
        access_token: str,
        refresh_token: Optional[str] = None,
        token_expires_at: Optional[datetime] = None,
        permissions: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> UserIntegration:
        """Create or update a user integration."""
        integration = db.query(UserIntegration).filter(
            UserIntegration.user_id == user_id,
            UserIntegration.integration_type == integration_type,
        ).first()
        
        if integration:
            integration.access_token = access_token
            if refresh_token:
                integration.refresh_token = refresh_token
            if token_expires_at:
                integration.token_expires_at = token_expires_at
            if permissions:
                integration.permissions = permissions
            if metadata:
                integration.metadata = metadata
            integration.updated_at = datetime.utcnow()
        else:
            integration = UserIntegration(
                user_id=user_id,
                integration_type=integration_type,
                access_token=access_token,
                refresh_token=refresh_token,
                token_expires_at=token_expires_at,
                permissions=permissions,
                metadata=metadata,
            )
            db.add(integration)
        
        db.commit()
        db.refresh(integration)
        return integration
    
    @staticmethod
    def get_by_user_and_type(
        db: Session,
        user_id: int,
        integration_type: str,
    ) -> Optional[UserIntegration]:
        """Get integration by user and type."""
        return db.query(UserIntegration).filter(
            UserIntegration.user_id == user_id,
            UserIntegration.integration_type == integration_type,
        ).first()
    
    @staticmethod
    def get_by_user(db: Session, user_id: int) -> List[UserIntegration]:
        """Get all integrations for a user."""
        return db.query(UserIntegration).filter(
            UserIntegration.user_id == user_id,
        ).all()
    
    @staticmethod
    def delete(db: Session, user_id: int, integration_type: str) -> bool:
        """Delete a user integration."""
        integration = db.query(UserIntegration).filter(
            UserIntegration.user_id == user_id,
            UserIntegration.integration_type == integration_type,
        ).first()
        
        if integration:
            db.delete(integration)
            db.commit()
            return True
        return False


class DashboardLinkRepository:
    """Repository for dashboard link operations."""
    
    @staticmethod
    def get_or_create(db: Session, user_id: int) -> DashboardLink:
        """Get or create a dashboard link for a user."""
        import secrets
        
        link = db.query(DashboardLink).filter(
            DashboardLink.user_id == user_id,
        ).first()
        
        if not link:
            # Generate unique token
            token = secrets.token_urlsafe(32)
            link = DashboardLink(
                user_id=user_id,
                token=token,
            )
            db.add(link)
            db.commit()
            db.refresh(link)
        
        return link
    
    @staticmethod
    def get_by_token(db: Session, token: str) -> Optional[DashboardLink]:
        """Get dashboard link by token."""
        link = db.query(DashboardLink).filter(
            DashboardLink.token == token,
        ).first()
        
        if link:
            link.last_accessed_at = datetime.utcnow()
            db.commit()
            db.refresh(link)
        
        return link
    
    @staticmethod
    def get_by_user(db: Session, user_id: int) -> Optional[DashboardLink]:
        """Get dashboard link by user ID."""
        return db.query(DashboardLink).filter(
            DashboardLink.user_id == user_id,
        ).first()
