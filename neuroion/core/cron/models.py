"""
Cron job and schedule models.

Contract:
- schedule: at (ISO8601+tz) | every (everyMs) | cron (5-field, tz default Europe/Amsterdam)
- sessionTarget: "main" | "isolated"
- payload: main -> kind=systemEvent + text; isolated -> kind=agentTurn + message + optional delivery
- wakeMode: "now" | "next-heartbeat"
"""
from datetime import datetime
from typing import Any, Literal, Optional, Union
from pydantic import BaseModel, Field


# --- Schedule kinds ---

class AtSchedule(BaseModel):
    """Run once at a specific ISO8601 time (must include explicit timezone)."""
    kind: Literal["at"] = "at"
    at: str  # ISO8601 with explicit timezone (+01:00, +02:00, or Z)


class EverySchedule(BaseModel):
    """Run every N milliseconds (everyMs >= 60000)."""
    kind: Literal["every"] = "every"
    everyMs: int = Field(..., ge=60000)


class CronSchedule(BaseModel):
    """5-field cron expression with IANA timezone."""
    kind: Literal["cron"] = "cron"
    expr: str  # 5-field: min hour day month weekday
    tz: str = "Europe/Amsterdam"  # IANA timezone


Schedule = Union[AtSchedule, EverySchedule, CronSchedule]


# --- Payload: main <-> systemEvent, isolated <-> agentTurn ---

class MainPayload(BaseModel):
    """For sessionTarget=main: system event with text."""
    kind: Literal["systemEvent"] = "systemEvent"
    text: str


class IsolatedPayload(BaseModel):
    """For sessionTarget=isolated: agent turn with message and optional delivery."""
    kind: Literal["agentTurn"] = "agentTurn"
    message: str
    delivery: Optional[dict] = None  # only allowed for isolated


Payload = Union[MainPayload, IsolatedPayload]


# --- Cron job ---

class CronJob(BaseModel):
    """Single cron job."""
    id: str
    userId: str
    schedule: Union[AtSchedule, EverySchedule, CronSchedule]
    sessionTarget: Literal["main", "isolated"]
    payload: Union[MainPayload, IsolatedPayload]
    wakeMode: Literal["now", "next-heartbeat"] = "next-heartbeat"
    label: Optional[str] = None
    createdAt: str  # ISO8601
    model_config = {"extra": "forbid"}


def job_to_dict(job: CronJob) -> dict:
    """Serialize job for JSON storage."""
    return job.model_dump(mode="json")


def job_from_dict(data: dict) -> CronJob:
    """Deserialize job from JSON."""
    return CronJob.model_validate(data)
