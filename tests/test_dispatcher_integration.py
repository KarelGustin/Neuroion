"""Integration: fake LLM output (JSON tool_call) -> dispatcher -> CronService."""
import os
import pytest


def test_dispatcher_cron_add_integration(monkeypatch):
    import tempfile
    d = tempfile.mkdtemp(prefix="neuroion_cron_")
    monkeypatch.setenv("CRON_DATA_DIR", d)
    from neuroion.core.agent.tools.dispatcher import execute_tool
    result = execute_tool(
        "cron.add",
        {
            "schedule": {"kind": "every", "everyMs": 120000},
            "sessionTarget": "main",
            "payload": {"kind": "systemEvent", "text": "Test"},
        },
        "test-user-1",
    )
    assert "jobId" in result or "job" in result or result.get("success") is True
    result2 = execute_tool("cron.list", {}, "test-user-1")
    assert "jobs" in result2
    assert len(result2["jobs"]) >= 1


def test_dispatcher_unknown_tool():
    from neuroion.core.agent.tools.dispatcher import execute_tool
    result = execute_tool("unknown.tool", {}, "user")
    assert result.get("success") is False
    assert "Unknown" in result.get("error", "")
