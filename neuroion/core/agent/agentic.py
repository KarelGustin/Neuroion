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

    def to_facts_list(self) -> List[str]:
        """Facts for Writer: one string per tool result (tool name + summary). No noise."""
        facts = []
        for e in self._events:
            if e.success and (e.result_summary or e.tool):
                facts.append(f"{e.tool}: {e.result_summary or 'ok'}")
            elif not e.success:
                facts.append(f"{e.tool}: error — {e.error or 'unknown'}")
        return facts


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


# next_action: planner/reflect output — exactly one per step
NEXT_ACTION_TOOL = "tool"
NEXT_ACTION_RESPOND = "respond"
NEXT_ACTION_ASK_USER = "ask_user"
NEXT_ACTION_REVISE_PLAN = "revise_plan"
VALID_NEXT_ACTIONS = (NEXT_ACTION_TOOL, NEXT_ACTION_RESPOND, NEXT_ACTION_ASK_USER, NEXT_ACTION_REVISE_PLAN)


def parse_plan_action_response(
    raw: str,
    allowed_tools: Optional[List[str]] = None,
) -> Tuple[
    Optional[str],
    Optional[List[str]],
    Optional[List[Dict[str, Any]]],
    str,
    List[str],
    str,
]:
    """
    Parse first agent step JSON: goal, plan, next_action, tool_calls, response_outline, question_to_user.
    Returns (goal, plan_steps, tool_calls, next_action, response_outline, question_to_user).
    next_action is one of: tool | respond | ask_user | revise_plan.
    """
    obj = extract_json_from_response(raw)
    if not obj or not isinstance(obj, dict):
        return None, None, [], NEXT_ACTION_RESPOND, [], ""

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

    next_action = (obj.get("next_action") or "").strip().lower()
    if next_action not in VALID_NEXT_ACTIONS:
        next_action = NEXT_ACTION_RESPOND

    raw_outline = obj.get("response_outline")
    if isinstance(raw_outline, list):
        response_outline = [str(s).strip() for s in raw_outline if str(s).strip()]
    else:
        response_outline = []

    question_to_user = obj.get("question_to_user") or obj.get("question") or ""
    if isinstance(question_to_user, str):
        question_to_user = question_to_user.strip()
    else:
        question_to_user = ""

    raw_calls = obj.get("tool_calls")
    if raw_calls is None:
        return goal, plan, [], next_action, response_outline, question_to_user
    if not isinstance(raw_calls, list):
        return goal, plan, [], next_action, response_outline, question_to_user

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

    if next_action == NEXT_ACTION_TOOL and not tool_calls:
        next_action = NEXT_ACTION_RESPOND
    return goal, plan, tool_calls, next_action, response_outline, question_to_user


def parse_reflect_response(
    raw: str,
    allowed_tools: Optional[List[str]] = None,
) -> Tuple[
    Optional[str],
    List[Dict[str, Any]],
    str,
    List[str],
    str,
]:
    """
    Parse reflect step JSON: reflection, next_action, tool_calls, response_outline, question_to_user.
    Returns (reflection_text, tool_calls, next_action, response_outline, question_to_user).
    """
    obj = extract_json_from_response(raw)
    if not obj or not isinstance(obj, dict):
        return None, [], NEXT_ACTION_RESPOND, [], ""

    reflection = obj.get("reflection") or obj.get("observation_summary")
    if isinstance(reflection, str):
        reflection = reflection.strip()
    else:
        reflection = None

    next_action = (obj.get("next_action") or "").strip().lower()
    if next_action not in VALID_NEXT_ACTIONS:
        next_action = NEXT_ACTION_RESPOND

    raw_outline = obj.get("response_outline")
    if isinstance(raw_outline, list):
        response_outline = [str(s).strip() for s in raw_outline if str(s).strip()]
    else:
        response_outline = []

    question_to_user = obj.get("question_to_user") or obj.get("question") or ""
    if isinstance(question_to_user, str):
        question_to_user = question_to_user.strip()
    else:
        question_to_user = ""

    raw_calls = obj.get("tool_calls")
    if raw_calls is None:
        return reflection, [], next_action, response_outline, question_to_user
    if not isinstance(raw_calls, list):
        return reflection, [], next_action, response_outline, question_to_user

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

    if next_action == NEXT_ACTION_TOOL and not tool_calls:
        next_action = NEXT_ACTION_RESPOND
    return reflection, tool_calls, next_action, response_outline, question_to_user


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
