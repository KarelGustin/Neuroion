"""
Hard validation rules for cron jobs.

- main <-> systemEvent, isolated <-> agentTurn
- delivery only allowed for isolated
- everyMs >= 60000 (enforced in model)
- Reject cron expr that runs every minute unless allowlisted
- schedule.kind=at must include explicit timezone (+01:00, +02:00, or Z)
- Max 20 jobs per user per day (caller passes current count; validation raises if over limit)
"""
import re
from typing import List, Optional

from neuroion.core.cron.models import (
    AtSchedule,
    CronSchedule,
    EverySchedule,
    IsolatedPayload,
    MainPayload,
)


class CronValidationError(ValueError):
    """Raised when cron job validation fails."""
    pass


def validate_session_target_and_payload(
    session_target: str,
    payload: dict,
) -> None:
    """
    Enforce: main <-> systemEvent, isolated <-> agentTurn; delivery only for isolated.
    """
    if session_target not in ("main", "isolated"):
        raise CronValidationError(f"sessionTarget must be 'main' or 'isolated', got {session_target!r}")

    kind = payload.get("kind")
    if kind not in ("systemEvent", "agentTurn"):
        raise CronValidationError(f"payload.kind must be 'systemEvent' or 'agentTurn', got {kind!r}")

    if session_target == "main":
        if kind != "systemEvent":
            raise CronValidationError("sessionTarget 'main' requires payload.kind 'systemEvent'")
        if "text" not in payload:
            raise CronValidationError("payload for main must include 'text'")
        if payload.get("delivery") is not None:
            raise CronValidationError("delivery is only allowed for sessionTarget 'isolated'")

    if session_target == "isolated":
        if kind != "agentTurn":
            raise CronValidationError("sessionTarget 'isolated' requires payload.kind 'agentTurn'")
        if "message" not in payload:
            raise CronValidationError("payload for isolated must include 'message'")


def validate_every_ms(every_ms: int) -> None:
    """everyMs >= 60000."""
    if every_ms < 60000:
        raise CronValidationError("everyMs must be >= 60000 (1 minute)")


# ISO8601 with explicit timezone: ends with Z or +HH:MM / -HH:MM
_AT_TZ_PATTERN = re.compile(
    r"^.+(Z|([+-]\d{2}:\d{2}))$",
    re.ASCII,
)


def validate_at_timezone(at: str) -> None:
    """schedule.kind=at must include explicit timezone (+01:00, +02:00, or Z)."""
    if not at or not at.strip():
        raise CronValidationError("schedule.at must be non-empty")
    if not _AT_TZ_PATTERN.search(at.strip()):
        raise CronValidationError(
            "schedule.at must be ISO8601 with explicit timezone (e.g. +01:00, +02:00, or Z)"
        )


def _cron_runs_every_minute(expr: str) -> bool:
    """True if the 5-field cron expression runs every minute (e.g. * * * * *)."""
    parts = expr.strip().split()
    if len(parts) != 5:
        return False
    # Standard order: minute hour day month weekday
    return parts[0].strip() == "*"


def validate_cron_expression(
    expr: str,
    allow_every_minute: bool = False,
    allowlist_expressions: Optional[List[str]] = None,
) -> None:
    """
    Reject cron expr that runs every minute unless allowlisted.

    allow_every_minute: if True, allow * * * * *.
    allowlist_expressions: list of normalized expressions (e.g. "* * * * *") that are allowed.
    """
    parts = expr.strip().split()
    if len(parts) != 5:
        raise CronValidationError("cron expr must be 5-field: minute hour day month weekday")

    if not _cron_runs_every_minute(expr):
        return

    if allow_every_minute:
        return
    normalized = " ".join(p.strip() for p in parts)
    if allowlist_expressions and normalized in allowlist_expressions:
        return
    raise CronValidationError(
        "cron expression runs every minute; not allowed unless in CRON_ALLOW_EVERY_MINUTE allowlist"
    )


def validate_jobs_per_user_per_day(current_count: int, limit: int) -> None:
    """Reject if current_count >= limit (used before adding a new job)."""
    if current_count >= limit:
        raise CronValidationError(
            f"max {limit} jobs per user per day; current count is {current_count}"
        )
