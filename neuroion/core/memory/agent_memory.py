"""
Agent memory abstraction: short-term (run context) and long-term (retrieve) for the agentic loop.
Thin layer over ContextSnapshotRepository and PreferenceRepository.
"""
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from neuroion.core.memory.repository import ContextSnapshotRepository, PreferenceRepository


@dataclass
class ShortTermMemory:
    """Run context: current conversation and optional task state (from task_manager)."""
    conversation_history: Optional[List[Dict[str, str]]] = None
    task: Optional[Dict[str, Any]] = None

    def format_conversation_for_prompt(self, max_exchanges: int = 10) -> str:
        """Format recent conversation as text for prompt (optional use)."""
        if not self.conversation_history:
            return ""
        lines = []
        for msg in self.conversation_history[-max_exchanges:]:
            role = msg.get("role", "user")
            content = msg.get("content", msg.get("message", ""))
            lines.append(f"{role}: {content}")
        return "\n".join(lines) if lines else ""


class AgentMemory:
    """
    Long-term: retrieve(scope, limit) from preferences + context snapshots.
    Short-term: get_short_term(conversation_history, task) for run context.
    """

    @staticmethod
    def retrieve(
        db: Session,
        household_id: int,
        user_id: Optional[int] = None,
        scope: str = "user",
        limit: int = 10,
    ) -> str:
        """
        Retrieve long-term context for the agent prompt.

        scope="user" -> user preferences + recent context for that user.
        scope="household" -> household preferences + household-level context (user_id ignored for context).
        Returns a formatted string suitable for inclusion in the system/user prompt.
        """
        if scope == "household":
            prefs = PreferenceRepository.get_all(db, household_id, user_id=None)
            snapshots = ContextSnapshotRepository.get_recent(
                db, household_id, limit=limit, user_id=None
            )
        else:
            prefs = PreferenceRepository.get_all(db, household_id, user_id=user_id)
            snapshots = ContextSnapshotRepository.get_recent(
                db, household_id, limit=limit, user_id=user_id
            )

        lines = []
        if prefs:
            lines.append("Preferences:")
            for k, v in prefs.items():
                lines.append(f"  {k}: {v}")
        if snapshots:
            lines.append("Recent context:")
            for snap in snapshots:
                ts = getattr(snap, "timestamp", None)
                event_type = getattr(snap, "event_type", "")
                summary = getattr(snap, "summary", "")
                lines.append(f"  - [{str(ts)}] {event_type}: {summary}")
        return "\n".join(lines) if lines else "No long-term context."

    @staticmethod
    def get_short_term(
        conversation_history: Optional[List[Dict[str, str]]] = None,
        task: Optional[Dict[str, Any]] = None,
    ) -> ShortTermMemory:
        """Build short-term memory for the current run (conversation + task state)."""
        return ShortTermMemory(
            conversation_history=conversation_history,
            task=task,
        )
