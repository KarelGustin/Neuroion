"""
Integration tests for cron service and storage.
"""
import os
import tempfile
import pytest

# Set cron data dir to temp so we don't touch ~/.myapp
@pytest.fixture(autouse=True)
def cron_temp_dir(monkeypatch):
    d = tempfile.mkdtemp(prefix="neuroion_cron_test_")
    monkeypatch.setenv("CRON_DATA_DIR", d)
    yield d
    # cleanup optional


def test_add_job_and_list():
    from neuroion.core.cron.service import CronService
    from neuroion.core.cron import storage
    svc = CronService()
    user_id = "test-user-1"
    spec = {
        "schedule": {"kind": "every", "everyMs": 120000},
        "sessionTarget": "main",
        "payload": {"kind": "systemEvent", "text": "Hello"},
        "wakeMode": "next-heartbeat",
    }
    out = svc.add_job(user_id, spec)
    assert "jobId" in out
    assert "job" in out
    assert out["job"]["userId"] == user_id
    assert out["job"]["schedule"]["kind"] == "every"
    assert out["job"]["schedule"]["everyMs"] == 120000
    listed = svc.list_jobs(user_id)
    assert len(listed["jobs"]) == 1
    assert listed["jobs"][0]["id"] == out["jobId"]


def test_run_job_now_appends_run():
    from neuroion.core.cron.service import CronService
    from neuroion.core.cron import storage
    svc = CronService()
    user_id = "test-user-2"
    spec = {
        "schedule": {"kind": "every", "everyMs": 120000},
        "sessionTarget": "main",
        "payload": {"kind": "systemEvent", "text": "Run me"},
    }
    out = svc.add_job(user_id, spec)
    job_id = out["jobId"]
    run_out = svc.run_job_now(job_id, user_id)
    assert run_out.get("success") is True
    runs = svc.get_runs(job_id, user_id, limit=10)
    assert len(runs["runs"]) >= 1
    assert runs["runs"][-1].get("status") in ("ok", "error")


def test_remove_job():
    from neuroion.core.cron.service import CronService
    svc = CronService()
    user_id = "test-user-3"
    spec = {
        "schedule": {"kind": "at", "at": "2026-01-01T12:00:00+01:00"},
        "sessionTarget": "isolated",
        "payload": {"kind": "agentTurn", "message": "Remind"},
    }
    out = svc.add_job(user_id, spec)
    job_id = out["jobId"]
    assert len(svc.list_jobs(user_id)["jobs"]) == 1
    svc.remove_job(job_id, user_id)
    assert len(svc.list_jobs(user_id)["jobs"]) == 0
