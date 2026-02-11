"""
Structured output protocol for local LLM: parse JSON tool_call / need_info / final.
Includes JSON repair and duplicate-intent detection.
"""
import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Set

# Keywords that suggest "intention" without a tool call (loop risk)
INTENTION_KEYWORDS = ("ik zal", "i will", "i'll", "i am going to", "let me", "i'm going to", "we zullen", "we will")


@dataclass
class ParsedToolCall:
    type: str = "tool_call"
    tool: str = ""
    args: Dict[str, Any] = None

    def __post_init__(self):
        if self.args is None:
            self.args = {}


@dataclass
class ParsedNeedInfo:
    type: str = "need_info"
    questions: List[str] = None

    def __post_init__(self):
        if self.questions is None:
            self.questions = []


@dataclass
class ParsedFinal:
    type: str = "final"
    message: str = ""


Parsed = Tuple[str, Any]  # (kind, payload) where kind in ("tool_call", "need_info", "final")


def _extract_json_object(text: str) -> Optional[str]:
    """Try to extract a single JSON object from text (first { ... } or code block)."""
    text = text.strip()
    # Try whole string
    if text.startswith("{") and text.endswith("}"):
        return text
    # Code block ```json ... ``` or ``` ... ```
    code = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text, re.IGNORECASE)
    if code:
        return code.group(1).strip()
    # First balanced { ... }
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


def _parse_json(raw: str) -> Optional[Dict[str, Any]]:
    """Parse raw string as JSON; try repair by extracting object."""
    for candidate in (raw.strip(), _extract_json_object(raw)):
        if not candidate:
            continue
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    return None


def _looks_like_intention(text: str) -> bool:
    """True if text looks like 'I will do X' without being valid JSON tool_call/final."""
    if not text or len(text) > 2000:
        return False
    lower = text.lower().strip()
    for kw in INTENTION_KEYWORDS:
        if kw in lower:
            return True
    return False


def parse_llm_output(
    raw: str,
    last_assistant_output: Optional[str] = None,
    allowed_tools: Optional[Set[str]] = None,
) -> Tuple[str, Any]:
    """
    Parse LLM output into one of: tool_call, need_info, final.
    Returns (kind, payload). payload is ParsedToolCall, ParsedNeedInfo, ParsedFinal, or None on error.
    If duplicate-intent detected (intention-like again after intention-like), returns ("need_info", ParsedNeedInfo(questions=["Output only JSON: type tool_call or final."])).
    """
    data = _parse_json(raw)
    if data and isinstance(data, dict):
        kind = (data.get("type") or "").strip().lower()
        if kind == "tool_call":
            tool = (data.get("tool") or "").strip()
            args = data.get("args")
            if isinstance(args, dict) and tool:
                if allowed_tools is not None and tool not in allowed_tools:
                    return ("invalid", None)
                return ("tool_call", ParsedToolCall(tool=tool, args=args))
        if kind == "need_info":
            q = data.get("questions")
            if isinstance(q, list):
                questions = [str(x) for x in q]
            elif q is not None:
                questions = [str(q)]
            else:
                questions = []
            return ("need_info", ParsedNeedInfo(questions=questions))
        if kind == "final":
            msg = data.get("message")
            return ("final", ParsedFinal(message=msg if msg is not None else ""))
    # Duplicate-intent: last output was intention-like and current is also intention-like
    if last_assistant_output and _looks_like_intention(last_assistant_output) and _looks_like_intention(raw):
        return (
            "need_info",
            ParsedNeedInfo(questions=["Please respond with only a JSON object: {\"type\":\"tool_call\",\"tool\":\"cron.add\",\"args\":{...}} or {\"type\":\"final\",\"message\":\"...\"}. No other text."]),
        )
    return ("invalid", None)


def format_tool_result_for_llm(result: Dict[str, Any]) -> str:
    """Format tool execution result as string for optional follow-up LLM turn."""
    return json.dumps(result, ensure_ascii=False, default=str)
