"""
Agent gateway: orchestrate LLM tool calling and tool execution.

Runs a single agent turn: decide tool vs answer, execute tools (via ToolRouter),
and return a final response message.
"""
import json
from typing import Dict, Any, List, Optional

from neuroion.core.agent.cron_tools_schema import get_cron_tools_for_llm
from neuroion.core.agent.prompts import (
    build_chat_messages,
    build_structured_tool_messages,
    build_tool_result_messages,
)
from neuroion.core.agent.tool_protocol import parse_llm_output, format_tool_result_for_llm
from neuroion.core.agent.tool_router import get_tool_router
from neuroion.core.agent.tool_registry import get_tool_registry
from neuroion.core.agent.types import RunContext
from neuroion.core.llm.base import LLMClient
from neuroion.core.observability.metrics import record_tool_call


def run_agent_turn(
    *,
    db: Any,
    household_id: int,
    user_id: Optional[int],
    message: str,
    conversation_history: Optional[List[Dict[str, str]]],
    llm: LLMClient,
    context_snapshots: Optional[List[Dict[str, Any]]] = None,
    user_preferences: Optional[Dict[str, Any]] = None,
    household_preferences: Optional[Dict[str, Any]] = None,
) -> str:
    """Run a single agent turn and return the final response message."""
    tool_registry = get_tool_registry()
    tool_router = get_tool_router()
    tools = tool_router.get_all_tools_for_llm()
    messages = build_chat_messages(
        user_message=message,
        context_snapshots=context_snapshots or [],
        user_preferences=user_preferences,
        household_preferences=household_preferences,
        conversation_history=conversation_history,
        db=db,
        household_id=household_id,
        user_id=user_id,
    )

    content, tool_calls = llm.chat_with_tools(
        messages, tools=tools, temperature=0.7, tool_choice="auto"
    )

    if tool_calls:
        assistant_msg = {
            "role": "assistant",
            "content": content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.name, "arguments": json_dumps(tc.arguments)},
                }
                for tc in tool_calls
            ],
        }
        messages.append(assistant_msg)
        user_id_str = str(user_id) if user_id is not None else "0"
        context = RunContext(
            db=db,
            household_id=household_id,
            user_id=user_id,
            user_id_str=user_id_str,
            allowed_tools=None,
        )
        for tc in tool_calls:
            tool_result = tool_router.call(tc.name, tc.arguments, context)
            record_tool_call(tc.name, tool_result.success)
            result_dict = (
                tool_result.output
                if tool_result.success and tool_result.output
                else {"success": tool_result.success, "error": tool_result.error}
            )
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": format_tool_result_for_llm(result_dict),
                }
            )
        final_content, _ = llm.chat_with_tools(
            messages, tools=tools, temperature=0.7, tool_choice="none"
        )
        return (final_content or "").strip()

    structured = _try_structured_tool_call(
        message=message,
        conversation_history=conversation_history,
        llm=llm,
        db=db,
        household_id=household_id,
        user_id=user_id,
        context_snapshots=context_snapshots,
        user_preferences=user_preferences,
        household_preferences=household_preferences,
        tool_registry=tool_registry,
    )
    if structured is not None:
        return structured

    return (content or "").strip()


def _try_structured_tool_call(
    *,
    message: str,
    conversation_history: Optional[List[Dict[str, str]]],
    llm: LLMClient,
    db: Any,
    household_id: int,
    user_id: Optional[int],
    context_snapshots: Optional[List[Dict[str, Any]]],
    user_preferences: Optional[Dict[str, Any]],
    household_preferences: Optional[Dict[str, Any]],
    tool_registry,
) -> Optional[str]:
    """Fallback for models without native tool calling."""
    tools = _build_structured_tool_list(tool_registry)
    messages = build_structured_tool_messages(
        user_message=message,
        tools=tools,
        conversation_history=conversation_history,
    )
    raw = llm.chat(messages, temperature=0.3)
    allowed = set(tool_registry.get_tool_names()) | _cron_tool_names()
    kind, payload = parse_llm_output(raw, allowed_tools=allowed)
    if kind == "tool_call" and payload:
        return _run_structured_tool_call(
            message,
            payload.tool,
            payload.args,
            llm,
            db=db,
            household_id=household_id,
            user_id=user_id,
            context_snapshots=context_snapshots,
            user_preferences=user_preferences,
            household_preferences=household_preferences,
        )
    if kind == "need_info" and payload:
        questions = payload.questions or []
        return " ".join(questions).strip() or "Please provide the requested information."
    if kind == "final" and payload:
        return (payload.message or "").strip() or "Done."
    return None


def _run_structured_tool_call(
    message: str,
    tool: str,
    args: Dict[str, Any],
    llm: LLMClient,
    *,
    db: Any,
    household_id: int,
    user_id: Optional[int],
    context_snapshots: Optional[List[Dict[str, Any]]],
    user_preferences: Optional[Dict[str, Any]],
    household_preferences: Optional[Dict[str, Any]],
) -> str:
    """Execute a tool via ToolRouter and ask the LLM for a final response."""
    user_id_str = str(user_id) if user_id is not None else "0"
    context = RunContext(
        db=db,
        household_id=household_id,
        user_id=user_id,
        user_id_str=user_id_str,
        allowed_tools=None,
    )
    tool_result = get_tool_router().call(tool, args, context)
    record_tool_call(tool, tool_result.success)
    result = (
        tool_result.output
        if tool_result.success and tool_result.output
        else {"success": False, "error": tool_result.error}
    )
    followup_messages = build_tool_result_messages(
        user_message=message,
        tool_name=tool,
        tool_result=result,
        context_snapshots=context_snapshots,
        user_preferences=user_preferences,
        household_preferences=household_preferences,
        db=db,
        household_id=household_id,
        user_id=user_id,
    )
    final = llm.chat(followup_messages, temperature=0.3)
    return (final or "").strip()


def json_dumps(data: Dict[str, Any]) -> str:
    """Serialize tool arguments safely."""
    return json.dumps(data or {}, ensure_ascii=False)


def _build_structured_tool_list(tool_registry) -> List[Dict[str, Any]]:
    tools = [
        {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.parameters,
        }
        for tool in tool_registry.list_tools()
    ]
    for cron_tool in get_cron_tools_for_llm():
        fn = cron_tool.get("function") or {}
        tools.append(
            {
                "name": fn.get("name", ""),
                "description": fn.get("description", ""),
                "parameters": fn.get("parameters", {}),
            }
        )
    return tools


def _cron_tool_names() -> set:
    return {t.get("function", {}).get("name") for t in get_cron_tools_for_llm() if t.get("function")}
