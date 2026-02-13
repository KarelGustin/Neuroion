"""
Daily summary compaction: at midnight, summarize each user's session summaries
from the previous day into one DailySummary.
"""
import logging
from datetime import datetime, timedelta
from datetime import date as date_type

from neuroion.core.memory.db import db_session
from neuroion.core.memory.models import Household
from neuroion.core.memory.repository import (
    SessionSummaryRepository,
    DailySummaryRepository,
    UserRepository,
    SystemConfigRepository,
)
from neuroion.core.llm import get_llm_client_from_config
from neuroion.core.agent.prompts import build_daily_summary_messages

logger = logging.getLogger(__name__)


def run_daily_summary_compaction() -> None:
    """
    For each user, collect session summaries from yesterday, summarize via LLM,
    and save as DailySummary. Intended to run once per day (e.g. from scheduler).
    """
    with db_session() as db:
        try:
            llm = get_llm_client_from_config(db)
        except Exception as e:
            logger.warning("Daily compaction: no LLM available: %s", e)
            return

        today = date_type.today()
        yesterday = today - timedelta(days=1)
        day_start = datetime.combine(yesterday, datetime.min.time())
        day_end = datetime.combine(today, datetime.min.time())

        households = db.query(Household).all()
        for household in households:
            users = UserRepository.get_by_household(db, household.id)
            for user in users:
                try:
                    summaries = SessionSummaryRepository.get_for_date(
                        db=db,
                        household_id=household.id,
                        user_id=user.id,
                        day_start=day_start,
                        day_end=day_end,
                    )
                    if not summaries:
                        continue
                    texts = [s.summary for s in summaries]
                    messages = build_daily_summary_messages(texts)
                    if not messages:
                        continue
                    raw = llm.chat(messages, temperature=0.2, max_tokens=400)
                    daily_summary = (raw or "").strip()[:3000] if raw else ""
                    if not daily_summary:
                        continue
                    DailySummaryRepository.create_or_update(
                        db=db,
                        household_id=household.id,
                        user_id=user.id,
                        date=day_start,
                        summary=daily_summary,
                    )
                    logger.info(
                        "Daily summary created for user %s (household %s)",
                        user.id,
                        household.id,
                    )
                except Exception as e:
                    logger.exception(
                        "Daily compaction failed for user %s: %s",
                        getattr(user, "id", None),
                        e,
                    )


def maybe_run_daily_compaction() -> None:
    """
    Run daily compaction only once per calendar day (UTC).
    Call this from the cron scheduler tick.
    """
    with db_session() as db:
        today_str = date_type.today().isoformat()
        last = SystemConfigRepository.get(db, "daily_summary_last_run")
        last_str = None
        if last and getattr(last, "value", None):
            try:
                import json
                v = last.value
                last_str = json.loads(v) if isinstance(v, str) else v
                if isinstance(last_str, dict):
                    last_str = last_str.get("date")
                last_str = str(last_str) if last_str else None
            except Exception:
                last_str = None
        if last_str == today_str:
            return
        SystemConfigRepository.set(
            db, "daily_summary_last_run", {"date": today_str}, category="memory"
        )
    run_daily_summary_compaction()
