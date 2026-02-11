"""Thin wrappers mapping cron.* tool names to CronService methods."""
from typing import Any, Dict

from neuroion.core.cron.service import CronService
from neuroion.core.cron.validation import CronValidationError


_cron_service = CronService()


def cron_add(user_id: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """cron.add: schedule, sessionTarget, payload, wakeMode?, label?."""
    return _cron_service.add_job(user_id, args)


def cron_update(user_id: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """cron.update: jobId + optional schedule, sessionTarget, payload, wakeMode, label."""
    job_id = args.get("jobId")
    if not job_id:
        return {"success": False, "error": "jobId required"}
    patch = {k: v for k, v in args.items() if k != "jobId"}
    return _cron_service.update_job(job_id, user_id, patch)


def cron_remove(user_id: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """cron.remove: jobId."""
    job_id = args.get("jobId")
    if not job_id:
        return {"success": False, "error": "jobId required"}
    return _cron_service.remove_job(job_id, user_id)


def cron_list(user_id: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """cron.list: no args."""
    return _cron_service.list_jobs(user_id)


def cron_run(user_id: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """cron.run: jobId."""
    job_id = args.get("jobId")
    if not job_id:
        return {"success": False, "error": "jobId required"}
    return _cron_service.run_job_now(job_id, user_id)


def cron_runs(user_id: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """cron.runs: jobId, limit?."""
    job_id = args.get("jobId")
    if not job_id:
        return {"success": False, "error": "jobId required"}
    limit = args.get("limit", 100)
    return _cron_service.get_runs(job_id, user_id, limit=limit)


CRON_HANDLERS = {
    "cron.add": cron_add,
    "cron.update": cron_update,
    "cron.remove": cron_remove,
    "cron.list": cron_list,
    "cron.run": cron_run,
    "cron.runs": cron_runs,
}
