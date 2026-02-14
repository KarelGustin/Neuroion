"""
Agent gateway: orchestrate agentic loop (plan → act → observe → reflect) and final response.

Uses JSON at every step; turn trace (log) is fed to the LLM as observation.
Full SOUL + system prompt only for the final user-facing message.
"""
import json
import logging
from typing import Dict, Any, List, Optional, Callable

from neuroion.core.agent.agentic import (
    MAX_AGENT_ITERATIONS,
    NEXT_ACTION_ASK_USER,
    NEXT_ACTION_RESPOND,
    NEXT_ACTION_TOOL,
    TurnTrace,
    parse_plan_action_response,
    parse_reflect_response,
    parse_final_response,
)
from neuroion.core.agent.cron_tools_schema import get_cron_tools_for_llm
from neuroion.core.agent.prompts import (
    build_chat_messages_from_input,
    build_writer_messages,
    get_agent_loop_system_prompt,
    get_agent_plan_action_instruction,
    get_agent_reflect_instruction,
    get_soul_prompt,
    build_structured_tool_messages,
    build_tool_result_messages,
)
from neuroion.core.agent.tool_formatters import (
    result_summary_for_trace,
    tools_list_text_for_agent,
)
from neuroion.core.agent.tool_protocol import parse_llm_output, format_tool_result_for_llm
from neuroion.core.agent.tool_router import get_tool_router
from neuroion.core.agent.tool_registry import get_tool_registry
from neuroion.core.agent.types import AgentInput, RunContext
from neuroion.core.llm.base import LLMClient
from neuroion.core.observability.metrics import record_tool_call

logger = logging.getLogger(__name__)

# Max length for step_output content in stream (keeps SSE payloads bounded)
STEP_OUTPUT_PLAN_MAX = 4000
STEP_OUTPUT_TOOL_MAX = 3500
STEP_OUTPUT_REFLECT_MAX = 2000


def _truncate(s: str, max_len: int, suffix: str = "…") -> str:
    if not s or len(s) <= max_len:
        return s or ""
    return s[: max_len - len(suffix)] + suffix


def _emit_step_output(
    progress_callback: Optional[Callable[[Dict[str, Any]], None]],
    phase: str,
    content: str,
    tool: Optional[str] = None,
) -> None:
    """Emit actual AI output for this step so the client can show a dynamic pipeline log."""
    if not progress_callback or not content:
        return
    ev: Dict[str, Any] = {"type": "step_output", "phase": phase, "content": content.strip()}
    if tool:
        ev["tool"] = tool
    progress_callback(ev)


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


# Max tokens for chat-mode reply to keep latency predictable (quality preserved with concise prompts).
CHAT_MODE_MAX_TOKENS = 1024


def run_chat_mode(
    agent_input: AgentInput,
    llm: LLMClient,
    progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> str:
    """
    Chat mode: single LLM call, no plan/reflect, no tools.
    For simple Q&A, conversation, small talk. One turn, low latency.
    When progress_callback is set and the LLM supports stream(), tokens are emitted as {"type": "token", "text": "..."}.
    """
    messages = build_chat_messages_from_input(agent_input)
    use_stream = progress_callback is not None and hasattr(llm, "stream") and callable(getattr(llm, "stream"))
    if use_stream:
        try:
            chunks: List[str] = []
            for chunk in llm.stream(messages, temperature=0.45):
                if chunk:
                    chunks.append(chunk)
                    progress_callback({"type": "token", "text": chunk})
            raw = "".join(chunks)
        except Exception as e:
            logger.warning("Chat mode stream failed, falling back to sync: %s", e)
            use_stream = False
    if not use_stream:
        try:
            raw = llm.chat(messages, temperature=0.45, max_tokens=CHAT_MODE_MAX_TOKENS)
        except Exception as e:
            logger.warning("Chat mode failed: %s", e)
            return "I had trouble answering. Please try again."
    reply = parse_final_response(raw)
    if not reply:
        reply = (raw or "").strip()
    return reply.strip()


def run_reflection_workflow(agent_input: AgentInput, llm: LLMClient) -> str:
    """
    Reflection/QA mode: evaluate last exchange for gaps, risks, what's missing.
    One LLM call; no tool loop unless we extend later.
    """
    history = agent_input.conversation_history or []
    last_user = ""
    last_assistant = ""
    for i in range(len(history) - 1, -1, -1):
        role = (history[i].get("role") or "").strip().lower()
        content = (history[i].get("content") or "").strip()
        if role == "user" and not last_user:
            last_user = content
        elif role == "assistant" and not last_assistant:
            last_assistant = content
        if last_user and last_assistant:
            break
    if not last_assistant:
        return run_chat_mode(agent_input, llm)
    system = (
        "You evaluate an assistant's answer for gaps, risks, and what might be missing. "
        "Reply in 1-2 short paragraphs: what is solid, what could be wrong or incomplete, and what the user might still need. "
        "Use the same language as the user. Be concise."
    )
    user_content = (
        f"User asked:\n{last_user}\n\nAssistant replied:\n{last_assistant}\n\n"
        "Evaluate this answer. What is missing or risky?"
    )
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user_content}]
    try:
        raw = llm.chat(messages, temperature=0.3)
        return (raw or "").strip()
    except Exception as e:
        logger.warning("Reflection workflow failed: %s", e)
        return "I couldn't evaluate that. Please try again."


def _emit(progress_callback: Optional[Callable[[Dict[str, Any]], None]], event: Dict[str, Any]) -> None:
    """Emit a progress event if callback is set."""
    if progress_callback:
        try:
            progress_callback(event)
        except Exception:
            pass


def _writer_llm_call(
    llm: LLMClient,
    messages: List[Dict[str, str]],
    progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> str:
    """Run writer LLM call; stream tokens to callback when possible."""
    use_stream = progress_callback is not None and hasattr(llm, "stream") and callable(getattr(llm, "stream"))
    if use_stream:
        try:
            chunks: List[str] = []
            for chunk in llm.stream(messages, temperature=0.45):
                if chunk:
                    chunks.append(chunk)
                    progress_callback({"type": "token", "text": chunk})
            return "".join(chunks)
        except Exception as e:
            logger.warning("Writer stream failed, falling back to sync: %s", e)
    try:
        return llm.chat(messages, temperature=0.45, max_tokens=1024) or ""
    except Exception as e:
        logger.warning("Writer chat failed: %s", e)
        raise


def run_agent_turn(
    *,
    agent_input: AgentInput,
    db: Any,
    household_id: int,
    user_id: Optional[int],
    llm: LLMClient,
    use_codebase_tools: Optional[bool] = None,
    progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> str:
    """
    Run agentic turn: plan (JSON) → action (execute tools, log) → observe → reflect (JSON) → repeat or final.
    use_codebase_tools: True = allow all tools (coding mode); False = exclude codebase (research); None = infer from message.
    """
    tool_router = get_tool_router()
    tool_registry = get_tool_registry()
    all_tool_names = list(tool_router.get_all_tool_names())
    if use_codebase_tools is True:
        allowed_tools = all_tool_names
    elif use_codebase_tools is False:
        allowed_tools = [t for t in all_tool_names if not t.startswith("codebase.")]
    else:
        if _is_web_research_intent(agent_input.user_message or ""):
            allowed_tools = [t for t in all_tool_names if not t.startswith("codebase.")]
        else:
            allowed_tools = all_tool_names
    name = (agent_input.agent_name or "ion").strip() or "ion"
    user_message = agent_input.user_message or ""

    tools_list_text = tools_list_text_for_agent(tool_router, allowed_tools=set(allowed_tools))
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

    (
        goal,
        plan_steps,
        tool_calls,
        next_action,
        response_outline,
        question_to_user,
    ) = parse_plan_action_response(plan_raw, allowed_tools=allowed_tools)

    if goal is None and plan_steps is None and (not tool_calls or len(tool_calls) == 0):
        goal = user_message
        plan_steps = []
        tool_calls = []
        next_action = NEXT_ACTION_RESPOND

    # ask_user: return question immediately (Planner decided we need user input)
    if next_action == NEXT_ACTION_ASK_USER and question_to_user:
        return question_to_user.strip()

    # Emit actual plan output so client can show what the AI decided
    plan_lines = []
    if goal:
        plan_lines.append(f"Doel: {goal}")
    if plan_steps:
        plan_lines.append("Plan: " + " → ".join(plan_steps[:10]))
    if tool_calls:
        parts = [f"{tc.get('name', '')}({json.dumps(tc.get('arguments') or {}, ensure_ascii=False)[:80]})" for tc in tool_calls[:8]]
        plan_lines.append("Tools: " + ", ".join(parts))
    plan_lines.append(f"Volgende actie: {next_action}")
    if response_outline:
        plan_lines.append("Outline: " + " | ".join(response_outline[:5]))
    _emit_step_output(
        progress_callback,
        "plan",
        _truncate("\n".join(plan_lines), STEP_OUTPUT_PLAN_MAX),
    )

    _emit(progress_callback, {"type": "status", "text": "Plan klaar. Tools uitvoeren…"})
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
            _emit(progress_callback, {"type": "tool_start", "tool": tname})
            result = tool_router.call(tname, targs, context)
            record_tool_call(tname, result.success)
            out = result.output if result.success and result.output else {"success": False, "error": result.error}
            summary = result_summary_for_trace(tname, out)
            _emit_step_output(
                progress_callback,
                "tool_result",
                _truncate(summary, STEP_OUTPUT_TOOL_MAX),
                tool=tname,
            )
            _emit(progress_callback, {"type": "tool_done", "tool": tname})
            trace.append_tool_call(
                tool=tname,
                arguments=targs,
                success=result.success,
                result_summary=summary,
                error=None if result.success else result.error,
            )

    # No tools used and planner said respond → Writer with goal + user message only
    observation_json = trace.to_observation_json()
    if not observation_json or observation_json == "[]":
        _emit(progress_callback, {"type": "status", "text": "Antwoord formuleren…"})
        soul = agent_input.soul if agent_input.soul is not None else get_soul_prompt()
        writer_messages = build_writer_messages(
            agent_name=name,
            soul=soul,
            goal=goal or user_message,
            facts=[],
            response_outline=response_outline,
            user_message=user_message,
            no_tools_used=True,
        )
        try:
            direct_raw = _writer_llm_call(llm, writer_messages, progress_callback)
        except Exception as e:
            logger.warning("Writer (no tools) failed: %s", e)
            return "I had trouble answering. Please try again."
        reply = parse_final_response(direct_raw)
        if not reply:
            reply = (direct_raw or "").strip()
        return reply.strip()

    # State for loop: we have tool results; reflect may ask for more tools or respond
    last_response_outline = response_outline

    # Loop: reflect → next_action (tool | respond | ask_user)
    iterations = 0
    while iterations < MAX_AGENT_ITERATIONS:
        iterations += 1
        observation_json = trace.to_observation_json()
        if not observation_json or observation_json == "[]":
            break
        _emit(progress_callback, {"type": "status", "text": "Resultaten verwerken…"})
        reflect_instruction = get_agent_reflect_instruction(observation_json)
        reflect_messages = [
            {"role": "system", "content": system_short + "\n\n" + reflect_instruction},
            {"role": "user", "content": "Reflect on the observation above and output JSON with next_action and tool_calls (or null if done)."},
        ]
        try:
            reflect_raw = llm.chat(reflect_messages, temperature=0.3)
        except Exception as e:
            logger.warning("Agent reflect call failed: %s", e)
            break
        refl_text, next_calls, refl_next_action, refl_outline, refl_question = parse_reflect_response(
            reflect_raw, allowed_tools=allowed_tools
        )
        # Emit actual reflect output so client can follow the AI's decision
        refl_lines = []
        if refl_text:
            refl_lines.append(refl_text)
        refl_lines.append(f"Volgende actie: {refl_next_action}")
        if next_calls:
            refl_lines.append("Nog tools: " + ", ".join(tc.get("name", "") for tc in next_calls))
        if refl_outline:
            refl_lines.append("Outline: " + " | ".join(refl_outline[:5]))
        _emit_step_output(
            progress_callback,
            "reflect",
            _truncate("\n".join(refl_lines), STEP_OUTPUT_REFLECT_MAX),
        )
        if refl_outline:
            last_response_outline = refl_outline
        if refl_next_action == NEXT_ACTION_ASK_USER and refl_question:
            return refl_question.strip()
        if refl_next_action == NEXT_ACTION_RESPOND:
            break
        if not next_calls:
            break
        for tc in next_calls:
            tname = tc.get("name") or ""
            targs = tc.get("arguments") or {}
            if not tname:
                continue
            _emit(progress_callback, {"type": "tool_start", "tool": tname})
            result = tool_router.call(tname, targs, context)
            record_tool_call(tname, result.success)
            out = result.output if result.success and result.output else {"success": False, "error": result.error}
            summary = result_summary_for_trace(tname, out)
            _emit_step_output(
                progress_callback,
                "tool_result",
                _truncate(summary, STEP_OUTPUT_TOOL_MAX),
                tool=tname,
            )
            _emit(progress_callback, {"type": "tool_done", "tool": tname})
            trace.append_tool_call(
                tool=tname,
                arguments=targs,
                success=result.success,
                result_summary=summary,
                error=None if result.success else result.error,
            )

    # Final response: Writer with goal + facts only (no full conversation dump)
    _emit(progress_callback, {"type": "status", "text": "Antwoord formuleren…"})
    facts = trace.to_facts_list()
    final_goal = goal or user_message
    soul = agent_input.soul if agent_input.soul is not None else get_soul_prompt()
    writer_messages = build_writer_messages(
        agent_name=name,
        soul=soul,
        goal=final_goal,
        facts=facts,
        response_outline=last_response_outline,
        user_message=user_message,
        no_tools_used=False,
    )
    try:
        final_raw = _writer_llm_call(llm, writer_messages, progress_callback)
    except Exception as e:
        logger.warning("Writer (final) call failed: %s", e)
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
