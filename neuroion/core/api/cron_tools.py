"""
HTTP tool endpoints for cron: POST/GET /tool/cron.*
User ID from header X-User-Id.
"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Header, HTTPException, Query

from neuroion.core.cron.service import CronService
from neuroion.core.cron.validation import CronValidationError


router = APIRouter(prefix="/tool", tags=["cron-tools"])

_cron_service = CronService()


def _user_id(x_user_id: Optional[str] = Header(None, alias="X-User-Id")) -> str:
    if not x_user_id or not x_user_id.strip():
        raise HTTPException(status_code=400, detail="X-User-Id header is required")
    return x_user_id.strip()


# --- Request/response bodies (flexible dicts for tool contract) ---

@router.post("/cron.add")
def cron_add(
    body: Dict[str, Any],
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
) -> Dict[str, Any]:
    """Add a cron job. Body: schedule, sessionTarget, payload, wakeMode?, label?."""
    try:
        result = _cron_service.add_job(_user_id(x_user_id), body)
        return result
    except CronValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post("/cron.update")
def cron_update(
    body: Dict[str, Any],
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
) -> Dict[str, Any]:
    """Update a cron job. Body: jobId, and optional schedule, sessionTarget, payload, wakeMode, label."""
    job_id = body.get("jobId")
    if not job_id:
        raise HTTPException(status_code=422, detail="jobId is required")
    try:
        patch = {k: v for k, v in body.items() if k != "jobId" and v is not None}
        result = _cron_service.update_job(job_id, _user_id(x_user_id), patch)
        return result
    except CronValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post("/cron.remove")
def cron_remove(
    body: Dict[str, Any],
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
) -> Dict[str, Any]:
    """Remove a cron job. Body: jobId."""
    job_id = body.get("jobId")
    if not job_id:
        raise HTTPException(status_code=422, detail="jobId is required")
    try:
        return _cron_service.remove_job(job_id, _user_id(x_user_id))
    except CronValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/cron.list")
def cron_list(
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
) -> Dict[str, Any]:
    """List cron jobs for the user."""
    try:
        return _cron_service.list_jobs(_user_id(x_user_id))
    except CronValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post("/cron.run")
def cron_run(
    body: Dict[str, Any],
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
) -> Dict[str, Any]:
    """Run a cron job once now. Body: jobId."""
    job_id = body.get("jobId")
    if not job_id:
        raise HTTPException(status_code=422, detail="jobId is required")
    try:
        return _cron_service.run_job_now(job_id, _user_id(x_user_id))
    except CronValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/cron.runs")
def cron_runs(
    jobId: str = Query(..., description="Job ID"),
    limit: int = Query(100, ge=1, le=1000, description="Max runs to return"),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
) -> Dict[str, Any]:
    """Get run history for a job. Query: jobId, limit?"""
    try:
        return _cron_service.get_runs(jobId, _user_id(x_user_id), limit=limit)
    except CronValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
