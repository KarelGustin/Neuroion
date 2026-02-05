"""
Audit logging for actions, suggestions, and confirmations.

Provides utilities to log all agent actions and user interactions.
"""
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from neuralion.core.memory.repository import AuditLogRepository


class AuditLogger:
    """Centralized audit logging."""
    
    @staticmethod
    def log_suggestion(
        db: Session,
        household_id: int,
        action_name: str,
        reasoning: str,
        input_data: Optional[Dict[str, Any]] = None,
        user_id: Optional[int] = None,
    ) -> int:
        """
        Log an action suggestion from the agent.
        
        Returns:
            Audit log entry ID
        """
        log = AuditLogRepository.create(
            db=db,
            household_id=household_id,
            action_type="suggestion",
            action_name=action_name,
            reasoning=reasoning,
            user_id=user_id,
            input_data=input_data,
            status="pending",
        )
        return log.id
    
    @staticmethod
    def log_confirmation(
        db: Session,
        log_id: int,
        user_id: Optional[int] = None,
    ) -> bool:
        """
        Log user confirmation of an action.
        
        Returns:
            True if log entry was found and updated
        """
        log = AuditLogRepository.update_status(
            db=db,
            log_id=log_id,
            status="confirmed",
        )
        return log is not None
    
    @staticmethod
    def log_execution(
        db: Session,
        log_id: int,
        output_data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Log successful execution of an action.
        
        Returns:
            True if log entry was found and updated
        """
        log = AuditLogRepository.update_status(
            db=db,
            log_id=log_id,
            status="executed",
            output_data=output_data,
        )
        return log is not None
    
    @staticmethod
    def log_rejection(
        db: Session,
        log_id: int,
        user_id: Optional[int] = None,
    ) -> bool:
        """
        Log user rejection of an action.
        
        Returns:
            True if log entry was found and updated
        """
        log = AuditLogRepository.update_status(
            db=db,
            log_id=log_id,
            status="rejected",
        )
        return log is not None
    
    @staticmethod
    def log_failure(
        db: Session,
        log_id: int,
        error_message: str,
    ) -> bool:
        """
        Log failed execution of an action.
        
        Returns:
            True if log entry was found and updated
        """
        log = AuditLogRepository.update_status(
            db=db,
            log_id=log_id,
            status="failed",
            output_data={"error": error_message},
        )
        return log is not None
