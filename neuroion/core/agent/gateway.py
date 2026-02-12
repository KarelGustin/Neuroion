"""
Agent gateway: orchestrate agentic loop (plan → act → observe → reflect) and final response.

Uses JSON at every step; turn trace (log) is fed to the LLM as observation.
Full SOUL + system prompt only for the final user-facing message.
"""
import json
import logging
from typing import Dict, Any, List, Optional

from neuroion.core.agent.agentic import (
    MAX_AGENT_ITERATIONS,
    TurnTrace,
    parse_plan_action_response,
    parse_reflect_response,
    parse_final_response,
)
from neuroion.core.agent.cron_tools_schema import get_cron_tools_for_llm
from neuroion.core.agent.prompts import (
    build_chat_messages_from_input,
    build_agent_final_messages,
    get_agent_loop_system_prompt,
    get_agent_plan_action_instruction,
    get_agent_reflect_instruction,
    build_structured_tool_messages,
    build_tool_result_messages,
)
from neuroion.core.agent.tool_protocol import parse_llm_output, format_tool_result_for_llm
from neuroion.core.agent.tool_router import get_tool_router
from neuroion.core.agent.tool_registry import get_tool_registry
from neuroion.core.agent.types import AgentInput, RunContext
from neuroion.core.llm.base import LLMClient
from neuroion.core.observability.metrics import record_tool_call

logger = logging.getLogger(__name__)


def _tool_category(name: str) -> str:
    """Return category label for grouping tools in the plan prompt."""
    if not name:
        return "Other"
    if name.startswith("codebase."):
        return "Codebase"
    if name.startswith("cron."):
        return "Reminders/Scheduling"
    if name.startswith("web."):
        return "Web/Research"
    if name in ("get_dashboard_link",):
        return "Dashboard"
    if name in ("generate_week_menu", "create_grocery_list", "summarize_family_preferences"):
        return "Meals/Preferences"
    return "Other"


def _format_tool_params(parameters: Any) -> str:
    """Format JSON schema parameters as compact 'name, req, opt?' for agent context."""
    if not parameters or not isinstance(parameters, dict):
        return ""
    props = parameters.get("properties") or {}
    required = set(parameters.get("required") or [])
    if not props:
        return ""
    parts = []
    for key in props:
        parts.append(f"{key}?" if key not in required else key)
    return ", ".join(parts)


def _tools_list_text_for_agent(tool_router, allowed_tools: Optional[set] = None) -> str:
    """Build 'name(params): description' lines for agent loop prompt, grouped by category.
    Includes exact parameter names so the model uses correct keys in arguments.
    If allowed_tools is set, only include those tools (e.g. exclude codebase for web research)."""
    tools = tool_router.get_all_tools_for_llm()
    by_category: Dict[str, List[str]] = {}
    for t in tools:
        fn = t.get("function") or t
        name = fn.get("name") or t.get("name") or ""
        if not name:
            continue
        if allowed_tools is not None and name not in allowed_tools:
            continue
        desc = (fn.get("description") or t.get("description") or "")[:120]
        params_str = _format_tool_params(fn.get("parameters"))
        if params_str:
            line = f"- {name}({params_str}): {desc}"
        else:
            line = f"- {name}: {desc}"
        cat = _tool_category(name)
        by_category.setdefault(cat, []).append(line)
    order = ("Codebase", "Web/Research", "Reminders/Scheduling", "Dashboard", "Meals/Preferences", "Other")
    sections = []
    for cat in order:
        if cat in by_category and by_category[cat]:
            sections.append(f"{cat}:\n" + "\n".join(by_category[cat]))
    for cat, lines in by_category.items():
        if cat not in order:
            sections.append(f"{cat}:\n" + "\n".join(lines))
    return "\n\n".join(sections) if sections else "No tools."


# Max chars for web search result summary in trace (so final LLM can answer with actual findings)
_WEB_SEARCH_SUMMARY_MAX = 2800


def _result_summary_for_trace(tool_name: str, result: Any) -> str:
    """Summary of tool result for turn trace. For web.search, include titles and URLs so final reply can use them."""
    if not isinstance(result, dict):
        return str(result)[:200] if result else "ok"
    if result.get("success") is False:
        return f"error: {result.get('error', 'unknown')}"[:150]
    # Web search: pass through enough for final LLM to formulate a real answer (titles + URLs)
    if tool_name == "web.search" and "results" in result and isinstance(result["results"], list):
        query = result.get("query") or ""
        lines = [f"Query: {query}"] if query else []
        for i, r in enumerate(result["results"][:10]):
            if not isinstance(r, dict):
                continue
            title = (r.get("title") or r.get("name") or "").strip()[:120]
            url = (r.get("url") or r.get("href") or r.get("link") or "").strip()
            snippet = (r.get("snippet") or r.get("body") or "").strip()[:150]
            if title or url:
                lines.append(f"{i + 1}) {title} | {url}" if url else f"{i + 1}) {title}")
            if snippet and len("\n".join(lines)) < _WEB_SEARCH_SUMMARY_MAX - 180:
                lines.append(f"   {snippet}")
            if len("\n".join(lines)) >= _WEB_SEARCH_SUMMARY_MAX:
                break
        if lines:
            return "\n".join(lines)[:_WEB_SEARCH_SUMMARY_MAX]
        return f"{len(result['results'])} results"
    # Common shapes
    if "content" in result and isinstance(result.get("content"), str):
        preview = result["content"][:100].replace("\n", " ")
        return f"{len(result['content'])} chars" if len(result["content"]) > 100 else preview
    if "path" in result and "entries" in result:
        return f"{len(result['entries'])} entries"
    if "matches" in result:
        return f"{len(result['matches'])} matches"
    if "results" in result and isinstance(result["results"], list):
        return f"{len(result['results'])} results"
    if "menu" in result:
        return "menu generated"
    if "list" in result:
        return "list created"
    if "message" in result:
        return str(result["message"])[:80]
    return "ok"


def _is_web_research_intent(message: str) -> bool:
    """True if the user message clearly asks for web search / product lookup (no codebase)."""
    if not message or not isinstance(message, str):
        return False
    lower = message.strip().lower()
    if not lower:
        return False
    search_phrases = (
        "zoek", "search", "vind", "find", "look up", "opzoeken",
        "prijzen", "producten", "winkels", "bestel", "kopen", "kosten",
        "tegels", "tiles", "garden", "tuin", "voor in",
    )
    return any(p in lower for p in search_phrases)


def run_agent_turn(
    *,
    agent_input: AgentInput,
    db: Any,
    household_id: int,
    user_id: Optional[int],
    llm: LLMClient,
) -> str:
    """
    Run agentic turn: plan (JSON) → action (execute tools, log) → observe → reflect (JSON) → repeat or final.
    Final response uses full system prompt + SOUL. Falls back to legacy single-call flow on JSON errors.
    """
    tool_router = get_tool_router()
    tool_registry = get_tool_registry()
    all_tool_names = list(tool_router.get_all_tool_names())
    # For web research / product queries, do not allow codebase tools (prevents hallucinated file reads)
    if _is_web_research_intent(agent_input.user_message or ""):
        allowed_tools = [t for t in all_tool_names if not t.startswith("codebase.")]
    else:
        allowed_tools = all_tool_names
    name = (agent_input.agent_name or "ion").strip() or "ion"
    user_message = agent_input.user_message or ""

    tools_list_text = _tools_list_text_for_agent(tool_router, allowed_tools=set(allowed_tools))
    system_short = get_agent_loop_system_prompt(name, tools_list_text)
    plan_instruction = get_agent_plan_action_instruction()

    # Step 1: Plan + first action (JSON)
    plan_messages = [
        {"role": "system", "content": system_short + "\n\n" + plan_instruction},
        {"role": "user", "content": user_message},
    ]
    try:
        plan_raw = llm.chat(plan_messages, temperature=0.3)
    except Exception as e:
        logger.warning("Agent plan call failed, falling back to legacy: %s", e)
        return _run_legacy_turn(agent_input=agent_input, db=db, household_id=household_id, user_id=user_id, llm=llm)

    goal, plan_steps, tool_calls = parse_plan_action_response(plan_raw, allowed_tools=allowed_tools)
    if goal is None and plan_steps is None and (not tool_calls or len(tool_calls) == 0):
        # No valid JSON or no tools: treat as "answer directly", go to final
        goal = user_message
        plan_steps = []
        tool_calls = []

    trace = TurnTrace()
    context = RunContext(
        db=db,
        household_id=household_id,
        user_id=user_id,
        user_id_str=str(user_id) if user_id is not None else "0",
        allowed_tools=None,
    )

    # Execute initial tool_calls if any
    if tool_calls:
        for tc in tool_calls:
            tname = tc.get("name") or ""
            targs = tc.get("arguments") or {}
            if not tname:
                continue
            result = tool_router.call(tname, targs, context)
            record_tool_call(tname, result.success)
            out = result.output if result.success and result.output else {"success": False, "error": result.error}
            summary = _result_summary_for_trace(tname, out)
            trace.append_tool_call(
                tool=tname,
                arguments=targs,
                success=result.success,
                result_summary=summary,
                error=None if result.success else result.error,
            )

    # No tools used: answer with direct chat (same context as Ollama app, no turn summary)
    observation_json = trace.to_observation_json()
    if not observation_json or observation_json == "[]":
        direct_messages = build_chat_messages_from_input(agent_input)
        try:
            direct_raw = llm.chat(direct_messages, temperature=0.7)
        except Exception as e:
            logger.warning("Direct chat failed: %s", e)
            return "I had trouble answering. Please try again."
        reply = parse_final_response(direct_raw)
        if not reply:
            reply = (direct_raw or "").strip()
        return reply.strip()

    # Loop: reflect → more tool_calls or final
    iterations = 0
    while iterations < MAX_AGENT_ITERATIONS:
        iterations += 1
        observation_json = trace.to_observation_json()
        if not observation_json or observation_json == "[]":
            break
        reflect_instruction = get_agent_reflect_instruction(observation_json)
        reflect_messages = [
            {"role": "system", "content": system_short + "\n\n" + reflect_instruction},
            {"role": "user", "content": "Reflect on the observation above and output JSON with reflection and tool_calls (or null if done)."},
        ]
        try:
            reflect_raw = llm.chat(reflect_messages, temperature=0.3)
        except Exception as e:
            logger.warning("Agent reflect call failed: %s", e)
            break
        _, next_calls = parse_reflect_response(reflect_raw, allowed_tools=allowed_tools)
        if not next_calls:
            break
        for tc in next_calls:
            tname = tc.get("name") or ""
            targs = tc.get("arguments") or {}
            if not tname:
                continue
            result = tool_router.call(tname, targs, context)
            record_tool_call(tname, result.success)
            out = result.output if result.success and result.output else {"success": False, "error": result.error}
            summary = _result_summary_for_trace(tname, out)
            trace.append_tool_call(
                tool=tname,
                arguments=targs,
                success=result.success,
                result_summary=summary,
                error=None if result.success else result.error,
            )

    # Final response: full SOUL + summary
    observation_summary = trace.to_summary_for_final()
    final_goal = goal or user_message
    final_messages = build_agent_final_messages(
        agent_input=agent_input,
        goal=final_goal,
        plan=plan_steps,
        observation_summary=observation_summary,
    )
    try:
        final_raw = llm.chat(final_messages, temperature=0.7)
    except Exception as e:
        logger.warning("Agent final call failed: %s", e)
        return "I had trouble finishing that. Please try again."
    reply = parse_final_response(final_raw)
    if not reply:
        reply = (final_raw or "").strip()
    return reply.strip()


def _run_legacy_turn(
    *,
    agent_input: AgentInput,
    db: Any,
    household_id: int,
    user_id: Optional[int],
    llm: LLMClient,
) -> str:
    """Legacy single turn: chat_with_tools (one tool round) then tool_choice=none for final. Used as fallback."""
    tool_router = get_tool_router()
    tools = tool_router.get_all_tools_for_llm()
    messages = build_chat_messages_from_input(agent_input)

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
                    "function": {"name": tc.name, "arguments": json.dumps(tc.arguments or {}, ensure_ascii=False)},
                }
                for tc in tool_calls
            ],
        }
        messages.append(assistant_msg)
        context = RunContext(
            db=db,
            household_id=household_id,
            user_id=user_id,
            user_id_str=str(user_id) if user_id is not None else "0",
            allowed_tools=None,
        )
        for tc in tool_calls:
            result = tool_router.call(tc.name, tc.arguments, context)
            record_tool_call(tc.name, result.success)
            result_dict = (
                result.output
                if result.success and result.output
                else {"success": result.success, "error": result.error}
            )
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": format_tool_result_for_llm(result_dict),
            })
        final_content, _ = llm.chat_with_tools(
            messages, tools=tools, temperature=0.7, tool_choice="none"
        )
        return (final_content or "").strip()

    # No native tool calls: try structured JSON fallback (Ollama etc.)
    structured = _try_structured_tool_call(
        agent_input=agent_input,
        llm=llm,
        db=db,
        household_id=household_id,
        user_id=user_id,
        tool_registry=get_tool_registry(),
        agent_name=(agent_input.agent_name or "ion").strip() or "ion",
    )
    if structured is not None:
        return structured

    return (content or "").strip()


def _try_structured_tool_call(
    *,
    agent_input: AgentInput,
    llm: LLMClient,
    db: Any,
    household_id: int,
    user_id: Optional[int],
    tool_registry: Any,
    agent_name: str = "ion",
) -> Optional[str]:
    """Fallback for models without native tool calling: structured JSON tool selection."""
    tools = _build_structured_tool_list(tool_registry)
    messages = build_structured_tool_messages(
        user_message=agent_input.user_message or "",
        tools=tools,
        conversation_history=agent_input.conversation_history,
        agent_name=agent_name,
    )
    try:
        raw = llm.chat(messages, temperature=0.3)
    except Exception:
        return None
    allowed = set(tool_registry.get_tool_names()) | _cron_tool_names()
    kind, payload = parse_llm_output(raw, allowed_tools=allowed)
    if kind == "tool_call" and payload:
        return _run_structured_tool_call(
            agent_input=agent_input,
            tool=payload.tool,
            args=payload.args or {},
            llm=llm,
            db=db,
            household_id=household_id,
            user_id=user_id,
            agent_name=agent_name,
        )
    if kind == "need_info" and payload and payload.questions:
        return " ".join(payload.questions).strip() or "Please provide the requested information."
    if kind == "final" and payload and payload.message:
        return (payload.message or "").strip()
    return None


def _run_structured_tool_call(
    *,
    agent_input: AgentInput,
    tool: str,
    args: Dict[str, Any],
    llm: LLMClient,
    db: Any,
    household_id: int,
    user_id: Optional[int],
    agent_name: str = "ion",
) -> str:
    """Execute one tool (structured path) and ask LLM for final response."""
    context = RunContext(
        db=db,
        household_id=household_id,
        user_id=user_id,
        user_id_str=str(user_id) if user_id is not None else "0",
        allowed_tools=None,
    )
    result = get_tool_router().call(tool, args or {}, context)
    record_tool_call(tool, result.success)
    result_dict = (
        result.output
        if result.success and result.output
        else {"success": False, "error": result.error}
    )
    messages = build_tool_result_messages(
        user_message=agent_input.user_message or "",
        tool_name=tool,
        tool_result=result_dict,
        context_snapshots=agent_input.memory,
        user_preferences=agent_input.user_preferences,
        household_preferences=agent_input.household_preferences,
        conversation_history=agent_input.conversation_history,
        db=db,
        household_id=household_id,
        user_id=user_id,
        agent_name=agent_name,
    )
    try:
        final = llm.chat(messages, temperature=0.3)
    except Exception:
        return str(result_dict.get("error", "Tool executed."))
    return (final or "").strip()


def _build_structured_tool_list(tool_registry: Any) -> List[Dict[str, Any]]:
    """Build tool list for structured JSON prompt (name, description, parameters)."""
    tools = [
        {"name": t.name, "description": t.description, "parameters": t.parameters}
        for t in tool_registry.list_tools()
    ]
    for cron_tool in get_cron_tools_for_llm():
        fn = cron_tool.get("function") or {}
        tools.append({
            "name": fn.get("name", ""),
            "description": fn.get("description", ""),
            "parameters": fn.get("parameters", {}),
        })
    return tools


def _cron_tool_names() -> set:
    return {t.get("function", {}).get("name") for t in get_cron_tools_for_llm() if t.get("function")}
