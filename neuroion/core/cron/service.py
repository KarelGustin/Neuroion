"""
Cron business logic: add/update/remove/list/run_job_now/get_runs with validation and persistence.
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from neuroion.core.config import settings
from neuroion.core.cron.models import (
    AtSchedule,
    CronJob,
    CronSchedule,
    EverySchedule,
    IsolatedPayload,
    MainPayload,
    job_from_dict,
    job_to_dict,
)
from neuroion.core.cron import storage
from neuroion.core.cron.validation import (
    CronValidationError,
    validate_at_timezone,
    validate_cron_expression,
    validate_every_ms,
    validate_jobs_per_user_per_day,
    validate_session_target_and_payload,
)


def _allowlist_expressions() -> List[str]:
    """Parse CRON_ALLOW_EVERY_MINUTE: comma-separated list of cron exprs, or 'true' for any."""
    raw = (settings.cron_allow_every_minute or "").strip().lower()
    if raw == "true" or raw == "1":
        return ["* * * * *"]  # allow the canonical every-minute expr
    return [x.strip() for x in raw.split(",") if x.strip()]


def _validate_schedule(schedule: dict) -> None:
    kind = schedule.get("kind")
    if kind == "at":
        at = schedule.get("at")
        if at is None:
            raise CronValidationError("schedule.at required for kind 'at'")
        validate_at_timezone(str(at))
    elif kind == "every":
        every_ms = schedule.get("everyMs")
        if every_ms is None:
            raise CronValidationError("schedule.everyMs required for kind 'every'")
        validate_every_ms(int(every_ms))
    elif kind == "cron":
        expr = schedule.get("expr")
        if expr is None:
            raise CronValidationError("schedule.expr required for kind 'cron'")
        allow = "true" in (settings.cron_allow_every_minute or "").lower() or "* * * * *" in _allowlist_expressions()
        validate_cron_expression(
            expr,
            allow_every_minute=allow,
            allowlist_expressions=_allowlist_expressions(),
        )
    else:
        raise CronValidationError(f"Unknown schedule kind: {kind}")


class CronService:
    """Service for managing cron jobs and runs."""

    def __init__(self, run_callback=None):
        """
        run_callback: optional callable(job: CronJob) called when a job is executed (for scheduler).
        """
        self._run_callback = run_callback

    def add_job(self, user_id: str, spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a new cron job. Validates and enforces 20 jobs per user per day.
        spec: schedule, sessionTarget, payload, wakeMode, optional label.
        Returns: {"jobId": "...", "job": {...}}
        """
        user_id = str(user_id)
        validate_session_target_and_payload(
            spec.get("sessionTarget", ""),
            spec.get("payload") or {},
        )
        schedule = spec.get("schedule")
        if not schedule:
            raise CronValidationError("schedule is required")
        _validate_schedule(schedule)

        count = storage.count_jobs_created_today_by_user(user_id)
        limit = getattr(settings, "cron_jobs_per_user_per_day", 20)
        validate_jobs_per_user_per_day(count, limit)

        job_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        job = CronJob(
            id=job_id,
            userId=user_id,
            schedule=_parse_schedule(schedule),
            sessionTarget=spec["sessionTarget"],
            payload=_parse_payload(spec["sessionTarget"], spec["payload"]),
            wakeMode=spec.get("wakeMode", "next-heartbeat"),
            label=spec.get("label"),
            createdAt=now,
        )
        jobs = storage.load_jobs()
        jobs.append(job)
        storage.save_jobs(jobs)
        return {"jobId": job_id, "job": job_to_dict(job)}

    def update_job(
        self,
        job_id: str,
        user_id: str,
        patch: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update an existing job. Only provided fields are updated. Returns {"job": {...}}."""
        user_id = str(user_id)
        jobs = storage.load_jobs()
        idx = next((i for i, j in enumerate(jobs) if j.id == job_id and j.userId == user_id), None)
        if idx is None:
            raise CronValidationError("Job not found or not owned by user")
        job = jobs[idx]

        if "schedule" in patch:
            _validate_schedule(patch["schedule"])
            job = job.model_copy(update={"schedule": _parse_schedule(patch["schedule"])})
        if "sessionTarget" in patch or "payload" in patch:
            st = patch.get("sessionTarget", job.sessionTarget)
            pl = patch.get("payload", job.payload)
            if isinstance(pl, dict):
                validate_session_target_and_payload(st, pl)
                job = job.model_copy(
                    update={
                        "sessionTarget": st,
                        "payload": _parse_payload(st, pl),
                    }
                )
        if "wakeMode" in patch:
            job = job.model_copy(update={"wakeMode": patch["wakeMode"]})
        if "label" in patch:
            job = job.model_copy(update={"label": patch["label"]})

        jobs[idx] = job
        storage.save_jobs(jobs)
        return {"job": job_to_dict(job)}

    def remove_job(self, job_id: str, user_id: str) -> Dict[str, Any]:
        """Remove a job. Returns {"success": true}."""
        user_id = str(user_id)
        jobs = storage.load_jobs()
        original_count = len(jobs)
        jobs = [j for j in jobs if not (j.id == job_id and j.userId == user_id)]
        if len(jobs) == original_count:
            raise CronValidationError("Job not found or not owned by user")
        storage.save_jobs(jobs)
        return {"success": True}

    def list_jobs(self, user_id: str) -> Dict[str, Any]:
        """List jobs for user. Returns {"jobs": [...]}."""
        user_id = str(user_id)
        jobs = storage.load_jobs()
        user_jobs = [j for j in jobs if j.userId == user_id]
        return {"jobs": [job_to_dict(j) for j in user_jobs]}

    def run_job_now(self, job_id: str, user_id: str) -> Dict[str, Any]:
        """Run a job once immediately and append to runs. Returns {"success": true, "run": {...}}."""
        user_id = str(user_id)
        jobs = storage.load_jobs()
        job = next((j for j in jobs if j.id == job_id and j.userId == user_id), None)
        if not job:
            raise CronValidationError("Job not found or not owned by user")
        return self._execute_job(job)

    def get_runs(self, job_id: str, user_id: str, limit: int = 100) -> Dict[str, Any]:
        """Get run history for a job. Returns {"runs": [...]}."""
        user_id = str(user_id)
        jobs = storage.load_jobs()
        job = next((j for j in jobs if j.id == job_id and j.userId == user_id), None)
        if not job:
            raise CronValidationError("Job not found or not owned by user")
        runs = storage.load_runs(job_id, limit=limit)
        return {"runs": runs}

    def _execute_job(self, job: CronJob) -> Dict[str, Any]:
        """Execute a job: run then append one run record."""
        from neuroion.core.cron.runner import execute_job
        try:
            execute_job(job)
            record = {"timestamp": datetime.now(timezone.utc).isoformat(), "status": "ok"}
        except Exception as e:
            record = {"timestamp": datetime.now(timezone.utc).isoformat(), "status": "error", "error": str(e)}
        storage.append_run(job.id, record)
        if self._run_callback:
            try:
                self._run_callback(job)
            except Exception:
                pass
        return {"success": True, "run": record}

    def get_job(self, job_id: str, user_id: str) -> Optional[CronJob]:
        """Return job if found and owned by user."""
        user_id = str(user_id)
        jobs = storage.load_jobs()
        return next((j for j in jobs if j.id == job_id and j.userId == user_id), None)


def _parse_schedule(schedule: dict):
    kind = schedule.get("kind")
    if kind == "at":
        return AtSchedule(at=schedule["at"])
    if kind == "every":
        return EverySchedule(everyMs=schedule["everyMs"])
    if kind == "cron":
        return CronSchedule(expr=schedule["expr"], tz=schedule.get("tz", "Europe/Amsterdam"))
    raise CronValidationError(f"Unknown schedule kind: {kind}")


def _parse_payload(session_target: str, payload: dict):
    if session_target == "main":
        return MainPayload(kind="systemEvent", text=payload.get("text", ""))
    return IsolatedPayload(
        kind="agentTurn",
        message=payload.get("message", ""),
        delivery=payload.get("delivery"),
    )
