"""
Context loading for the agent.

Loads context snapshots, preferences, session summaries, user memories
and other per-user context used when building agent input.
"""
import json
from typing import Any, Dict, List, Optional, Tuple

from neuroion.core.memory.db import db_session
from neuroion.core.memory.repository import (
    AgendaEventRepository,
    ContextSnapshotRepository,
    DailySummaryRepository,
    PreferenceRepository,
    SessionSummaryRepository,
    SystemConfigRepository,
    UserMemoryRepository,
    UserRepository,
)
from neuroion.core.skills.codebase import get_codebase_overview, get_codebase_root


def load_context_task(
    household_id: int,
    user_id: Optional[int],
) -> Tuple[
    List[Dict[str, Any]],
    Optional[Dict],
    Optional[Dict],
    str,
    Optional[str],
    Optional[str],
    Optional[str],
    Optional[str],
    Optional[str],
    Optional[str],
]:
    """
    Load context for agent input (run in thread).

    Returns:
        (context_dicts, user_preferences, household_preferences, agent_name,
         user_location, session_summaries_text, daily_summaries_text, user_memories_text, agenda_text, codebase_overview_text)
    """
    with db_session() as db:
        context_snapshots = ContextSnapshotRepository.get_recent(
            db, household_id, limit=10, user_id=user_id
        )
        context_dicts = [
            {"timestamp": str(snap.timestamp), "event_type": snap.event_type, "summary": snap.summary}
            for snap in context_snapshots
        ]
        user_preferences = PreferenceRepository.get_all(db, household_id, user_id=user_id)
        household_preferences = PreferenceRepository.get_all(db, household_id, user_id=None)
        agent_name = _get_agent_name(db)
        (
            user_location,
            session_summaries_text,
            daily_summaries_text,
            user_memories_text,
        ) = _get_user_context(db, household_id, user_id)
        agenda_text = _get_agenda_text(db, household_id, user_id)
        # Dynamic codebase overview at request time so the agent always sees current structure
        try:
            root = get_codebase_root(db)
            codebase_overview_text = get_codebase_overview(root, max_depth=2, max_items=250)
        except Exception:
            codebase_overview_text = None

        return (
            context_dicts,
            user_preferences,
            household_preferences,
            agent_name,
            user_location,
            session_summaries_text,
            daily_summaries_text,
            user_memories_text,
            agenda_text,
            codebase_overview_text,
        )


def _get_agent_name(db: Any) -> str:
    """Read agent display name from system config."""
    agent_name = "ion"
    cfg = SystemConfigRepository.get(db, "agent_name")
    if cfg and getattr(cfg, "value", None):
        try:
            v = json.loads(cfg.value) if isinstance(cfg.value, str) else cfg.value
            if isinstance(v, str) and v.strip():
                agent_name = v.strip()
        except (TypeError, ValueError):
            pass
    return agent_name


def _get_user_context(
    db: Any,
    household_id: int,
    user_id: Optional[int],
) -> Tuple[
    Optional[str],
    Optional[str],
    Optional[str],
    Optional[str],
]:
    """Load user-specific context: location, session summaries, daily summaries, memories."""
    user_location: Optional[str] = None
    session_summaries_text: Optional[str] = None
    daily_summaries_text: Optional[str] = None
    user_memories_text: Optional[str] = None

    if user_id is None:
        return user_location, session_summaries_text, daily_summaries_text, user_memories_text

    user = UserRepository.get_by_id(db, user_id)
    if user and getattr(user, "timezone", None):
        tz = (user.timezone or "").strip() or "Europe/Amsterdam"
        user_location = (
            f"Timezone: {tz}. Always take the user's location and time into account "
            "(scheduling, local services, 'here', 'local', etc.)."
        )

    session_summaries = SessionSummaryRepository.get_recent_for_user(
        db, household_id, user_id, limit=5
    )
    if session_summaries:
        lines = [f"- [{s.session_end_at}] {s.summary}" for s in reversed(session_summaries)]
        session_summaries_text = "Recent session context:\n" + "\n".join(lines)

    daily_summaries = DailySummaryRepository.get_recent_days(db, household_id, user_id, days=3)
    if daily_summaries:
        lines = []
        for s in daily_summaries:
            d = s.date.strftime("%Y-%m-%d") if hasattr(s.date, "strftime") else str(s.date)[:10]
            lines.append(f"- {d}: {s.summary}")
        daily_summaries_text = "Summary of the last 3 days:\n" + "\n".join(lines)

    user_memories = UserMemoryRepository.get_all_for_user(db, household_id, user_id, limit=30)
    if user_memories:
        lines = [f"- [{m.memory_type}] {m.summary}" for m in reversed(user_memories)]
        user_memories_text = "What you know about this user (long-term):\n" + "\n".join(lines)

    return user_location, session_summaries_text, daily_summaries_text, user_memories_text


def _get_agenda_text(db: Any, household_id: int, user_id: Optional[int]) -> Optional[str]:
    """Load upcoming agenda events (next 14 days) for the user as formatted text."""
    if user_id is None:
        return None
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    end = now + timedelta(days=14)
    events = AgendaEventRepository.list_for_user(db, household_id, user_id, now, end)
    if not events:
        return None
    lines = []
    for e in events:
        start = e.start_at.strftime("%Y-%m-%d %H:%M") if hasattr(e.start_at, "strftime") else str(e.start_at)[:16]
        end_str = e.end_at.strftime("%H:%M") if hasattr(e.end_at, "strftime") else str(e.end_at)[11:16]
        lines.append(f"- {start}–{end_str}: {e.title}")
    return "Upcoming agenda (next 14 days):\n" + "\n".join(lines)
