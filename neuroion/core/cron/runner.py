"""
Execute a cron job: dispatch by sessionTarget and payload (main vs isolated).

MVP: main -> log + append to events_main.jsonl for future heartbeat consumer;
isolated -> agent turn (stub: log).
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from neuroion.core.cron.models import CronJob
from neuroion.core.config import settings

logger = logging.getLogger(__name__)


def _events_main_path() -> Path:
    """Path for main-session events queue (heartbeat consumer can read)."""
    return Path(settings.database_path).parent / "cron" / "events_main.jsonl"


def execute_job(job: CronJob) -> None:
    """
    Run a single cron job based on sessionTarget and payload.
    - main: payload.kind=systemEvent, payload.text -> log + append to events_main.jsonl
    - isolated: payload.kind=agentTurn, payload.message + optional delivery -> agent turn (stub: log)
    """
    if job.sessionTarget == "main":
        text = job.payload.text if hasattr(job.payload, "text") else getattr(job.payload, "text", "")
        logger.info("cron job %s (main/systemEvent): %s", job.id, text)
        path = _events_main_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            record = {"jobId": job.id, "text": text, "timestamp": datetime.now(timezone.utc).isoformat()}
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except OSError as e:
            logger.warning("Could not append to events_main.jsonl: %s", e)
        return
    if job.sessionTarget == "isolated":
        msg = job.payload.message if hasattr(job.payload, "message") else getattr(job.payload, "message", "")
        logger.info("cron job %s (isolated/agentTurn): %s", job.id, msg)
        # TODO: emit to agent turn / events with optional delivery
        return
    logger.warning("cron job %s unknown sessionTarget %s", job.id, job.sessionTarget)
