"""Unit tests for tool_protocol: parse JSON, repair, duplicate-intent."""
import pytest
from neuroion.core.agent.tool_protocol import (
    parse_llm_output,
    ParsedToolCall,
    ParsedNeedInfo,
    ParsedFinal,
)


def test_parse_tool_call():
    raw = '{"type":"tool_call","tool":"cron.add","args":{"schedule":{"kind":"every","everyMs":1200000},"sessionTarget":"isolated","payload":{"kind":"agentTurn","message":"Hi"}}}'
    kind, payload = parse_llm_output(raw)
    assert kind == "tool_call"
    assert payload.tool == "cron.add"
    assert payload.args.get("schedule", {}).get("everyMs") == 1200000


def test_parse_need_info():
    raw = '{"type":"need_info","questions":["What time?"]}'
    kind, payload = parse_llm_output(raw)
    assert kind == "need_info"
    assert payload.questions == ["What time?"]


def test_parse_final():
    raw = '{"type":"final","message":"Done."}'
    kind, payload = parse_llm_output(raw)
    assert kind == "final"
    assert payload.message == "Done."


def test_repair_json_in_code_block():
    raw = 'Some text\n```json\n{"type":"final","message":"OK"}\n```'
    kind, payload = parse_llm_output(raw)
    assert kind == "final"
    assert payload.message == "OK"


def test_parse_invalid_returns_invalid():
    raw = "not json at all"
    kind, payload = parse_llm_output(raw)
    assert kind == "invalid"
    assert payload is None


def test_duplicate_intent_returns_need_info():
    last = "I will create a cron job for you in 20 minutes."
    current = "Ik zal een herinnering inplannen over 20 minuten."
    kind, payload = parse_llm_output(current, last_assistant_output=last)
    assert kind == "need_info"
    assert payload is not None
    assert payload.questions


def test_valid_tool_call_no_duplicate_intent():
    last = "I will create a cron job."
    current = '{"type":"tool_call","tool":"cron.list","args":{}}'
    kind, payload = parse_llm_output(current, last_assistant_output=last)
    assert kind == "tool_call"
    assert payload.tool == "cron.list"
