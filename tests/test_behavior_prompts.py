"""Assert that expected JSON payloads for the 10 behavior prompts parse correctly."""
import pytest
from neuroion.core.agent.tool_protocol import parse_llm_output

from tests.behavior_prompts.cases import BEHAVIOR_CASES


def _make_tool_call_json(tool: str, args: dict) -> str:
    import json
    return json.dumps({"type": "tool_call", "tool": tool, "args": args})


def _make_final_json(message: str) -> str:
    import json
    return json.dumps({"type": "final", "message": message})


@pytest.mark.parametrize("case", BEHAVIOR_CASES, ids=[str(c["id"]) for c in BEHAVIOR_CASES])
def test_expected_json_shape_parses(case):
    if case["expected_type"] == "tool_call":
        args = {}
        if "jobId" in (case.get("expected_args_keys") or []):
            args["jobId"] = "test-job-id"
        if case.get("expected_tool") == "cron.add":
            args.setdefault("schedule", {"kind": case.get("schedule_kind", "every"), "everyMs": 120000})
            args.setdefault("sessionTarget", "isolated")
            args.setdefault("payload", {"kind": "agentTurn", "message": "Reminder"})
            if case.get("schedule_kind") == "at":
                args["schedule"] = {"kind": "at", "at": "2026-02-12T15:00:00+01:00"}
            elif case.get("schedule_kind") == "cron":
                args["schedule"] = {"kind": "cron", "expr": "0 8 * * *", "tz": "Europe/Amsterdam"}
        if case.get("expected_tool") == "cron.update":
            args["jobId"] = "abc"
            args["schedule"] = {"kind": "every", "everyMs": 7200000}
        raw = _make_tool_call_json(case["expected_tool"], args)
    else:
        raw = _make_final_json("Ik heb geen weerinformatie.")
    kind, payload = parse_llm_output(raw)
    assert kind == case["expected_type"]
    if case["expected_type"] == "tool_call":
        assert payload.tool == case["expected_tool"]
        for key in case.get("expected_args_keys", []):
            assert key in payload.args or key in str(payload.args)
