"""
Daily request counting service.

Tracks chat requests per household and resets at midnight.
"""
import logging
from datetime import datetime, date, timedelta
from typing import Optional
from sqlalchemy.orm import Session

from neuroion.core.memory.repository import DailyRequestCountRepository

logger = logging.getLogger(__name__)


class RequestCounter:
    """Service for tracking and managing daily request counts."""
    
    @staticmethod
    def increment(db: Session, household_id: int) -> int:
        """
        Increment today's request count for a household.
        
        Args:
            db: Database session
            household_id: Household ID
            
        Returns:
            New count after increment
        """
        count = DailyRequestCountRepository.increment(db, household_id)
        return count.count
    
    @staticmethod
    def get_today_count(db: Session, household_id: int) -> int:
        """
        Get today's request count for a household.
        
        Args:
            db: Database session
            household_id: Household ID
            
        Returns:
            Today's request count
        """
        return DailyRequestCountRepository.get_today_count(db, household_id)
    
    @staticmethod
    def cleanup_old_counts(db: Session, days_to_keep: int = 30) -> int:
        """
        Clean up old request count records (older than specified days).
        
        Args:
            db: Database session
            days_to_keep: Number of days to keep records
            
        Returns:
            Number of records deleted
        """
        from neuroion.core.memory.models import DailyRequestCount
        
        cutoff_date = datetime.combine(
            date.today() - timedelta(days=days_to_keep),
            datetime.min.time()
        )
        
        deleted = db.query(DailyRequestCount).filter(
            DailyRequestCount.date < cutoff_date
        ).delete()
        
        db.commit()
        logger.info(f"Cleaned up {deleted} old request count records")
        return deleted
