"""
Cron persistence backed by SQLite.

Legacy JSON files are auto-migrated on first access:
~/.neuroion/cron/jobs.json and runs/<jobId>.jsonl
"""
import json
import os
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from neuroion.core.config import settings
from neuroion.core.cron.models import CronJob, job_from_dict, job_to_dict
from neuroion.core.memory.db import db_session
from neuroion.core.memory.repository import (
    CronJobRepository,
    CronRunRepository,
    SystemConfigRepository,
)

logger = logging.getLogger(__name__)

_migration_checked = False


def _cron_dir() -> Path:
    base = os.environ.get("CRON_DATA_DIR")
    if base:
        return Path(base)
    return Path(settings.database_path).parent / "cron"


def _jobs_path() -> Path:
    return _cron_dir() / "jobs.json"


def _runs_dir() -> Path:
    return _cron_dir() / "runs"


def _run_file_path(job_id: str) -> Path:
    return _runs_dir() / f"{job_id}.jsonl"


def _parse_iso(value: str) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    raw = value.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(raw)
    except Exception:
        return datetime.now(timezone.utc)


def _legacy_load_jobs() -> List[CronJob]:
    path = _jobs_path()
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, TypeError):
        return []
    if not isinstance(data, list):
        return []
    jobs = []
    for item in data:
        if not isinstance(item, dict):
            continue
        try:
            jobs.append(job_from_dict(item))
        except Exception:
            continue
    return jobs


def _legacy_load_runs(job_id: str, limit: int = 100) -> List[dict]:
    path = _run_file_path(job_id)
    if not path.exists():
        return []
    lines = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                lines.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return lines[-limit:] if limit else lines


def _truthy(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes")
    return False


def _ensure_migrated() -> None:
    global _migration_checked
    if _migration_checked:
        return
    with db_session() as db:
        flag = SystemConfigRepository.get(db, "cron_sqlite_migrated")
        if flag and _truthy(flag.value):
            _migration_checked = True
            return
        existing = CronJobRepository.list_all(db)
        if existing:
            SystemConfigRepository.set(db, "cron_sqlite_migrated", True, category="cron")
            _migration_checked = True
            return
        legacy_jobs = _legacy_load_jobs()
        if legacy_jobs:
            for job in legacy_jobs:
                created_at = _parse_iso(getattr(job, "createdAt", "") or "")
                CronJobRepository.upsert(
                    db,
                    job_id=job.id,
                    user_id=str(job.userId),
                    created_at=created_at,
                    job_json=job_to_dict(job),
                )
            for job in legacy_jobs:
                runs = _legacy_load_runs(job.id, limit=0)
                for run in runs:
                    ts = _parse_iso(str(run.get("timestamp") or ""))
                    CronRunRepository.append_run(db, job.id, ts, run)
            logger.info("Migrated %s cron jobs to SQLite", len(legacy_jobs))
        SystemConfigRepository.set(db, "cron_sqlite_migrated", True, category="cron")
        _migration_checked = True


def load_jobs() -> List[CronJob]:
    """Load all jobs from SQLite."""
    _ensure_migrated()
    with db_session() as db:
        records = CronJobRepository.list_all(db)
        jobs: List[CronJob] = []
        for rec in records:
            try:
                jobs.append(job_from_dict(rec.job_json))
            except Exception:
                continue
        return jobs


def save_jobs(jobs: List[CronJob]) -> None:
    """Upsert all jobs and remove missing ones."""
    _ensure_migrated()
    with db_session() as db:
        ids = []
        for job in jobs:
            ids.append(job.id)
            created_at = _parse_iso(getattr(job, "createdAt", "") or "")
            CronJobRepository.upsert(
                db,
                job_id=job.id,
                user_id=str(job.userId),
                created_at=created_at,
                job_json=job_to_dict(job),
            )
        CronJobRepository.delete_missing(db, ids)


def append_run(job_id: str, record: dict) -> None:
    """Append one run record to SQLite."""
    _ensure_migrated()
    ts = _parse_iso(str(record.get("timestamp") or ""))
    with db_session() as db:
        CronRunRepository.append_run(db, job_id, ts, record)


def load_runs(job_id: str, limit: int = 100) -> List[dict]:
    """Load last `limit` run records for a job (oldest to newest)."""
    _ensure_migrated()
    with db_session() as db:
        records = CronRunRepository.list_runs(db, job_id, limit=limit)
        return [r.run_json for r in records]


def count_jobs_created_today_by_user(user_id: str) -> int:
    """Count jobs created today (UTC) for a user."""
    _ensure_migrated()
    with db_session() as db:
        return CronJobRepository.count_jobs_created_today_by_user(db, user_id)


def get_cron_storage():
    """Return a simple namespace with load_jobs, save_jobs, append_run, load_runs, count_jobs_created_today_by_user."""
    class Storage:
        load_jobs = staticmethod(load_jobs)
        save_jobs = staticmethod(save_jobs)
        append_run = staticmethod(append_run)
        load_runs = staticmethod(load_runs)
        count_jobs_created_today_by_user = staticmethod(count_jobs_created_today_by_user)
    return Storage()
