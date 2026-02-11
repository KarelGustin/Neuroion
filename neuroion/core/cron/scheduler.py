"""
In-process cron scheduler: periodically load jobs, compute due jobs, execute and append runs.
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Optional

from neuroion.core.cron import storage
from neuroion.core.cron.models import CronJob, AtSchedule, EverySchedule, CronSchedule
from neuroion.core.cron.runner import execute_job

logger = logging.getLogger(__name__)

# How often we check for due jobs (seconds)
TICK_INTERVAL = 30


def _parse_iso8601(s: str) -> Optional[datetime]:
    """Parse ISO8601 string to datetime (timezone-aware)."""
    if not s:
        return None
    s = s.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def _last_run_time(job_id: str) -> Optional[datetime]:
    """Get timestamp of last run for job from runs file."""
    runs = storage.load_runs(job_id, limit=1)
    if not runs:
        return None
    ts = runs[-1].get("timestamp")
    if not ts:
        return None
    return _parse_iso8601(ts)


def _next_run_at(job: CronJob, now: datetime) -> Optional[datetime]:
    """
    Compute next run time for job from now. Returns None if not applicable (e.g. one-shot 'at' already passed).
    """
    schedule = job.schedule
    if isinstance(schedule, AtSchedule):
        t = _parse_iso8601(schedule.at)
        if t is None:
            return None
        return t
    if isinstance(schedule, EverySchedule):
        last = _last_run_time(job.id)
        base = last or _parse_iso8601(job.createdAt) or now
        delta_ms = schedule.everyMs
        from datetime import timedelta
        next_t = base + timedelta(milliseconds=delta_ms)
        return next_t if next_t > now else next_t + timedelta(milliseconds=delta_ms)
    if isinstance(schedule, CronSchedule):
        try:
            from croniter import croniter
            from zoneinfo import ZoneInfo
            tz = ZoneInfo(schedule.tz) if schedule.tz else ZoneInfo("Europe/Amsterdam")
            local_now = now.astimezone(tz)
            it = croniter(schedule.expr, local_now)
            next_dt = it.get_next(datetime)
            if next_dt.tzinfo is None:
                next_dt = next_dt.replace(tzinfo=tz)
            return next_dt.astimezone(timezone.utc)
        except Exception as e:
            logger.warning("cron next_run for job %s: %s", job.id, e)
            return None
    return None


def _is_due(job: CronJob, now: datetime) -> bool:
    """True if job should run at or before now. 'at' jobs run only once."""
    if isinstance(job.schedule, AtSchedule):
        # One-shot: run once when now >= at; do not run again if already run
        next_run = _next_run_at(job, now)
        if next_run is None:
            return False
        if next_run > now:
            return False
        runs = storage.load_runs(job.id, limit=1)
        if runs:
            return False  # already ran
        return True
    next_run = _next_run_at(job, now)
    if next_run is None:
        return False
    return next_run <= now


def _tick() -> None:
    """Load jobs, find due ones, execute and append run."""
    now = datetime.now(timezone.utc)
    jobs = storage.load_jobs()
    for job in jobs:
        try:
            if not _is_due(job, now):
                continue
            execute_job(job)
            record = {"timestamp": now.isoformat(), "status": "ok"}
            storage.append_run(job.id, record)
        except Exception as e:
            logger.exception("cron job %s failed: %s", job.id, e)
            record = {"timestamp": now.isoformat(), "status": "error", "error": str(e)}
            storage.append_run(job.id, record)


async def run_scheduler_loop() -> None:
    """Async loop: every TICK_INTERVAL seconds run _tick()."""
    while True:
        try:
            _tick()
        except Exception as e:
            logger.exception("cron scheduler tick failed: %s", e)
        await asyncio.sleep(TICK_INTERVAL)


_scheduler_task: Optional[asyncio.Task] = None


async def start_scheduler() -> None:
    """Start the cron scheduler as a background task."""
    global _scheduler_task
    if _scheduler_task is not None:
        return
    _scheduler_task = asyncio.create_task(run_scheduler_loop())
    logger.info("Cron scheduler started (tick every %ss)", TICK_INTERVAL)


async def stop_scheduler() -> None:
    """Cancel the cron scheduler task."""
    global _scheduler_task
    if _scheduler_task is None:
        return
    _scheduler_task.cancel()
    try:
        await _scheduler_task
    except asyncio.CancelledError:
        pass
    _scheduler_task = None
    logger.info("Cron scheduler stopped")
