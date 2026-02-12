"""
Agentic loop: turn trace (observation log), JSON schemas, and parse helpers.

Every step uses JSON so we can reliably parse tool calls and minimize errors.
The LLM observes via the turn trace (log of actions and results).
"""
import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

MAX_AGENT_ITERATIONS = 8


@dataclass
class TurnTraceEvent:
    """One entry in the observation log: tool call and result."""
    event: str  # "tool_call"
    tool: str = ""
    arguments: Dict[str, Any] = field(default_factory=dict)
    success: bool = False
    result_summary: str = ""  # Short summary for context (e.g. "150 lines returned")
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event": self.event,
            "tool": self.tool,
            "arguments": self.arguments,
            "success": self.success,
            "result_summary": self.result_summary,
            "error": self.error,
        }


class TurnTrace:
    """Structured log of tool calls and results for one turn. The LLM observes this."""
    def __init__(self) -> None:
        self._events: List[TurnTraceEvent] = []

    def append_tool_call(
        self,
        tool: str,
        arguments: Dict[str, Any],
        success: bool,
        result_summary: str = "",
        error: Optional[str] = None,
    ) -> None:
        self._events.append(
            TurnTraceEvent(
                event="tool_call",
                tool=tool,
                arguments=arguments,
                success=success,
                result_summary=result_summary,
                error=error,
            )
        )
        logger.info(
            "agent_tool %s %s success=%s summary=%s",
            tool,
            arguments,
            success,
            result_summary[:80] if result_summary else "",
        )

    def to_observation_json(self) -> str:
        """Serialize trace for LLM observation (JSON string)."""
        return json.dumps(
            [e.to_dict() for e in self._events],
            ensure_ascii=False,
            indent=0,
        )

    def to_summary_for_final(self) -> str:
        """Short summary for the final response prompt."""
        lines = []
        for e in self._events:
            if e.success:
                lines.append(f"- {e.tool}: {e.result_summary or 'ok'}")
            else:
                lines.append(f"- {e.tool}: error {e.error or 'unknown'}")
        return "\n".join(lines) if lines else "No tools used."


def extract_json_from_response(raw: str) -> Optional[Dict[str, Any]]:
    """Extract a single JSON object from LLM output. Handles markdown code blocks."""
    if not raw or not isinstance(raw, str):
        return None
    text = raw.strip()
    # Try raw first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Try ```json ... ```
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass
    # Try first { ... }
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return None


def parse_plan_action_response(
    raw: str,
    allowed_tools: Optional[List[str]] = None,
) -> Tuple[Optional[str], Optional[List[str]], Optional[List[Dict[str, Any]]]]:
    """
    Parse first agent step JSON: goal, plan, tool_calls.
    Returns (goal, plan_steps, tool_calls) or (None, None, None) on failure.
    tool_calls is list of {"name": str, "arguments": dict}.
    """
    obj = extract_json_from_response(raw)
    if not obj or not isinstance(obj, dict):
        return None, None, None
    goal = obj.get("goal") or obj.get("goal_summary")
    if isinstance(goal, str):
        goal = goal.strip()
    else:
        goal = None
    plan = obj.get("plan")
    if isinstance(plan, list):
        plan = [str(p).strip() for p in plan if str(p).strip()]
    else:
        plan = None
    raw_calls = obj.get("tool_calls")
    if raw_calls is None:
        return goal, plan, []
    if not isinstance(raw_calls, list):
        return goal, plan, []
    tool_calls = []
    for item in raw_calls:
        if not isinstance(item, dict):
            continue
        name = item.get("name") or item.get("tool")
        args = item.get("arguments") or item.get("args") or {}
        if not name or not isinstance(name, str):
            continue
        if allowed_tools and name not in allowed_tools:
            logger.warning("Agent requested disallowed tool %s", name)
            continue
        tool_calls.append({"name": name.strip(), "arguments": args if isinstance(args, dict) else {}})
    return goal, plan, tool_calls


def parse_reflect_response(
    raw: str,
    allowed_tools: Optional[List[str]] = None,
) -> Tuple[Optional[str], Optional[List[Dict[str, Any]]]]:
    """
    Parse reflect step JSON: reflection, tool_calls (or null = done).
    Returns (reflection_text, tool_calls). tool_calls empty or None means final.
    """
    obj = extract_json_from_response(raw)
    if not obj or not isinstance(obj, dict):
        return None, []
    reflection = obj.get("reflection") or obj.get("observation_summary")
    if isinstance(reflection, str):
        reflection = reflection.strip()
    else:
        reflection = None
    raw_calls = obj.get("tool_calls")
    if raw_calls is None:
        return reflection, []
    if not isinstance(raw_calls, list):
        return reflection, []
    tool_calls = []
    for item in raw_calls:
        if not isinstance(item, dict):
            continue
        name = item.get("name") or item.get("tool")
        args = item.get("arguments") or item.get("args") or {}
        if not name or not isinstance(name, str):
            continue
        if allowed_tools and name not in allowed_tools:
            continue
        tool_calls.append({"name": name.strip(), "arguments": args if isinstance(args, dict) else {}})
    return reflection, tool_calls


def parse_final_response(raw: str) -> str:
    """Extract final message to user. Accepts JSON {"message": "..."} or plain text."""
    if not raw or not isinstance(raw, str):
        return ""
    text = raw.strip()
    obj = extract_json_from_response(text)
    if obj and isinstance(obj, dict) and "message" in obj:
        msg = obj.get("message")
        if isinstance(msg, str):
            return msg.strip()
    return text
