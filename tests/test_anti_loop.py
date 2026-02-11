"""Loop regression: repeated intention without tool_call triggers anti-loop guard."""
from neuroion.core.agent.tool_protocol import parse_llm_output


def test_repeated_intention_returns_need_info():
    last = "I will create a reminder in 20 minutes."
    current = "I will set that up for you now."
    kind, payload = parse_llm_output(current, last_assistant_output=last)
    assert kind == "need_info"
    assert payload is not None
    assert len(payload.questions) > 0
    assert "JSON" in payload.questions[0] or "tool_call" in payload.questions[0]


def test_first_intention_then_invalid_no_false_positive():
    last = None
    current = "Sure, I can do that."
    kind, payload = parse_llm_output(current, last_assistant_output=last)
    assert kind == "invalid"
    assert payload is None
