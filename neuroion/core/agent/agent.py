"""
Main agent orchestrator.

Interprets user intent, decides on actions, and coordinates tool execution.
Supports LLM tool-calling for cron.* tools (scheduling/reminders).

Context loading and history-relevance LLM run in parallel (thread pool) so
the answering LLM is not delayed by surrounding preprocessing.
"""
import json
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, List, Optional, Tuple, Callable
from sqlalchemy.orm import Session

from neuroion.core.llm import get_llm_client_from_config
from neuroion.core.llm.base import LLMClient
from neuroion.core.memory.db import db_session
from neuroion.core.agent.tool_registry import get_tool_registry
from neuroion.core.agent.planner import Planner
from neuroion.core.agent.gateway import run_agent_turn, run_chat_mode, run_reflection_workflow
from neuroion.core.agent.types import AgentInput, RunContext, RunState
from neuroion.core.agent.executor import get_executor
from neuroion.core.agent.agent_loop import run_one_turn
from neuroion.core.agent.agentic import extract_json_from_response
from neuroion.core.agent.task_manager import (
    DONE,
    FAILED,
    get_or_create_task,
    transition,
    can_make_turn,
    can_execute_tool,
    is_terminal,
    clear_active_task_id,
    MAX_TURNS,
)
from neuroion.core.agent.tool_protocol import parse_llm_output
from neuroion.core.agent.task_prompts import build_task_messages
from neuroion.core.agent.prompts import (
    build_history_relevance_messages,
    build_meta_question_classifier_messages,
    build_scheduling_intent_messages,
    build_session_summary_messages,
    get_soul_prompt,
    MODE_CHAT,
    MODE_CODING,
    MODE_RESEARCH,
    MODE_SCHEDULING,
    MODE_TASK,
    NEED_CODING_TAG,
    NEED_RESEARCH_TAG,
    NEED_TASK_TAG,
)
from neuroion.core.agent.policies.guardrails import get_guardrails
from neuroion.core.agent.policies.validator import get_validator
from neuroion.core.observability.tracing import start_run, end_run
from neuroion.core.observability.metrics import record_run_result
from neuroion.core.memory.repository import (
    ContextSnapshotRepository,
    PreferenceRepository,
    SystemConfigRepository,
    UserRepository,
    SessionSummaryRepository,
    DailySummaryRepository,
    UserMemoryRepository,
)
from neuroion.core.security.audit import AuditLogger


def _parse_chat_reply_for_pipeline(reply: str) -> Tuple[str, Optional[str]]:
    """
    Parse chat reply for pipeline trigger tags. Returns (cleaned_reply, tag or None).
    tag is one of NEED_RESEARCH_TAG, NEED_CODING_TAG, NEED_TASK_TAG.
    """
    if not (reply or "").strip():
        return (reply or "").strip(), None
    tag = None
    if NEED_RESEARCH_TAG in reply:
        tag = NEED_RESEARCH_TAG
    elif NEED_CODING_TAG in reply:
        tag = NEED_CODING_TAG
    elif NEED_TASK_TAG in reply:
        tag = NEED_TASK_TAG
    if not tag:
        return reply.strip(), None
    lines = [ln for ln in reply.splitlines() if tag not in ln]
    cleaned = "\n".join(lines).strip()
    return cleaned, tag


# Thread pool for parallel context load + relevance LLM (each task uses its own DB session)
_agent_executor: Optional[ThreadPoolExecutor] = None


def _get_agent_executor() -> ThreadPoolExecutor:
    global _agent_executor
    if _agent_executor is None:
        _agent_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="agent_prep_")
    return _agent_executor


def _load_context_task(
    household_id: int, user_id: Optional[int]
) -> Tuple[
    List[Dict[str, Any]],
    Optional[Dict],
    Optional[Dict],
    str,
    Optional[str],
    Optional[str],
    Optional[str],
    Optional[str],
]:
    """Run in thread: load context snapshots, preferences, agent_name, location, session/daily summaries, user memories."""
    with db_session() as db:
        context_snapshots = ContextSnapshotRepository.get_recent(db, household_id, limit=10, user_id=user_id)
        context_dicts = [
            {"timestamp": str(snap.timestamp), "event_type": snap.event_type, "summary": snap.summary}
            for snap in context_snapshots
        ]
        user_preferences = PreferenceRepository.get_all(db, household_id, user_id=user_id)
        household_preferences = PreferenceRepository.get_all(db, household_id, user_id=None)
        agent_name = "ion"
        cfg = SystemConfigRepository.get(db, "agent_name")
        if cfg and getattr(cfg, "value", None):
            try:
                v = json.loads(cfg.value) if isinstance(cfg.value, str) else cfg.value
                if isinstance(v, str) and v.strip():
                    agent_name = v.strip()
            except (TypeError, ValueError):
                pass

        user_location: Optional[str] = None
        session_summaries_text: Optional[str] = None
        daily_summaries_text: Optional[str] = None
        user_memories_text: Optional[str] = None

        if user_id is not None:
            user = UserRepository.get_by_id(db, user_id)
            if user and getattr(user, "timezone", None):
                tz = (user.timezone or "").strip() or "Europe/Amsterdam"
                user_location = f"Timezone: {tz}. Always take the user's location and time into account (scheduling, local services, 'here', 'local', etc.)."

            session_summaries = SessionSummaryRepository.get_recent_for_user(
                db, household_id, user_id, limit=5
            )
            if session_summaries:
                lines = [
                    f"- [{s.session_end_at}] {s.summary}"
                    for s in reversed(session_summaries)
                ]
                session_summaries_text = "Recent session context:\n" + "\n".join(lines)

            daily_summaries = DailySummaryRepository.get_recent_days(
                db, household_id, user_id, days=3
            )
            if daily_summaries:
                lines = []
                for s in daily_summaries:
                    d = s.date.strftime("%Y-%m-%d") if hasattr(s.date, "strftime") else str(s.date)[:10]
                    lines.append(f"- {d}: {s.summary}")
                daily_summaries_text = "Summary of the last 3 days:\n" + "\n".join(lines)

            user_memories = UserMemoryRepository.get_all_for_user(
                db, household_id, user_id, limit=30
            )
            if user_memories:
                lines = [f"- [{m.memory_type}] {m.summary}" for m in reversed(user_memories)]
                user_memories_text = "What you know about this user (long-term):\n" + "\n".join(lines)

        return (
            context_dicts,
            user_preferences,
            household_preferences,
            agent_name,
            user_location,
            session_summaries_text,
            daily_summaries_text,
            user_memories_text,
        )


# Max messages from current session to send to LLM (rest is summarized via session summaries)
MAX_SESSION_MESSAGES_IN_CONTEXT = 50


def _get_llm_task() -> LLMClient:
    """Run in thread: get LLM client. Uses its own DB session."""
    with db_session() as db:
        return get_llm_client_from_config(db)


def compact_and_save_session(
    db: Session,
    household_id: int,
    user_id: int,
    messages: List[Any],
) -> None:
    """
    Summarize a list of chat messages (a session) and save as SessionSummary.
    messages: list of objects with .role, .content, .created_at (e.g. ChatMessage).
    """
    if not messages or len(messages) == 0:
        return
    try:
        llm = get_llm_client_from_config(db)
    except Exception:
        return
    hist = [{"role": getattr(m, "role", m.get("role")), "content": getattr(m, "content", m.get("content", ""))} for m in messages]
    prompt_messages = build_session_summary_messages(hist)
    raw = llm.chat(prompt_messages, temperature=0.2, max_tokens=300)
    summary = (raw or "").strip()[:2000] if raw else ""
    if not summary:
        return
    first = messages[0]
    last = messages[-1]
    session_start_at = getattr(first, "created_at", first.get("created_at"))
    session_end_at = getattr(last, "created_at", last.get("created_at"))
    if not session_start_at or not session_end_at:
        return
    SessionSummaryRepository.create(
        db=db,
        household_id=household_id,
        user_id=user_id,
        session_start_at=session_start_at,
        session_end_at=session_end_at,
        summary=summary,
        message_count=len(messages),
    )


def _relevance_and_llm_task(
    message: str,
    recent_6: List[Dict[str, str]],
    household_id: int,
    user_id: Optional[int],
) -> Tuple[List[Dict[str, str]], LLMClient]:
    """Run in thread: get LLM, run history-relevance (if recent_6), return (filtered_history, llm). Uses its own DB session."""
    with db_session() as db:
        llm = get_llm_client_from_config(db)
        if not recent_6:
            return ([], llm)
        relevance_messages = build_history_relevance_messages(message, recent_6)
        include_count = 0
        try:
            raw = llm.chat(relevance_messages, temperature=0.2)
            if raw:
                parsed = json.loads(raw.strip())
                n = int(parsed.get("include_count", 0))
                include_count = max(0, min(n, len(recent_6)))
        except (json.JSONDecodeError, ValueError, TypeError):
            include_count = 3
        filtered_history = recent_6[-include_count:] if include_count else []
        return (filtered_history, llm)


class Agent:
    """Main agent orchestrator."""
    
    def __init__(self):
        """Initialize agent with LLM client, tool registry, executor, validator, guardrails."""
        self.llm = None
        self.tool_registry = get_tool_registry()
        self.planner = Planner(self.tool_registry)
        self.executor = get_executor()
        self.validator = get_validator()
        self.guardrails = get_guardrails()

    @staticmethod
    def _emit_progress(progress_callback: Optional[Callable[[Dict[str, Any]], None]], event: Dict[str, Any]) -> None:
        if progress_callback:
            try:
                progress_callback(event)
            except Exception:
                pass

    def process_message(
        self,
        db: Session,
        household_id: int,
        user_id: Optional[int],
        message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        force_task_mode: bool = False,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> Dict[str, Any]:
        """
        Process a user message and return structured response.
        
        Args:
            db: Database session
            household_id: Household ID
            user_id: User ID (optional)
            message: User message
            conversation_history: Previous messages
        
        Returns:
            Dict with 'message', 'reasoning', and 'actions' keys
        """
        if user_id is not None:
            PreferenceRepository.delete_onboarding_preferences(db, household_id, user_id)

        # Use full current session as conversation history (caller provides session messages)
        full_session = conversation_history or []
        filtered_history = full_session[-MAX_SESSION_MESSAGES_IN_CONTEXT:] if full_session else []

        executor = _get_agent_executor()
        future_context = executor.submit(_load_context_task, household_id, user_id)
        future_llm = executor.submit(_get_llm_task)

        (
            context_dicts,
            user_preferences,
            household_preferences,
            agent_name,
            user_location,
            session_summaries_text,
            daily_summaries_text,
            user_memories_text,
        ) = future_context.result()
        self.llm = future_llm.result()

        user_id_str = str(user_id) if user_id is not None else "0"
        agent_input = AgentInput(
            user_message=message,
            agent_name=agent_name,
            soul=get_soul_prompt(),
            memory=context_dicts,
            user_preferences=user_preferences,
            household_preferences=household_preferences,
            conversation_history=filtered_history,
            system_instructions_extra=None,
            user_location=user_location,
            session_summaries_text=session_summaries_text,
            daily_summaries_text=daily_summaries_text,
            user_memories_text=user_memories_text,
        )

        # Client override: header forces task path when scheduling intent
        if force_task_mode and self._scheduling_intent(message):
            result = self._process_task_path(
                db, household_id, user_id, user_id_str, message, filtered_history
            )
            if result is not None:
                return result

        # Fast path: one chat call (no separate mode router). Model may add [NEED_RESEARCH], [NEED_CODING], [NEED_TASK].
        self._emit_progress(progress_callback, {"type": "status", "text": "Ik denk na…"})
        llm_response = run_chat_mode(agent_input, self.llm)
        cleaned_reply, pipeline_tag = _parse_chat_reply_for_pipeline(llm_response)

        if pipeline_tag == NEED_TASK_TAG:
            result = self._process_task_path(
                db, household_id, user_id, user_id_str, message, filtered_history
            )
            if result is not None:
                return result
            llm_response = cleaned_reply
        elif pipeline_tag == NEED_RESEARCH_TAG:
            self._emit_progress(progress_callback, {"type": "status", "text": "Ik zoek op het web…"})
            llm_response = run_agent_turn(
                agent_input=agent_input,
                db=db,
                household_id=household_id,
                user_id=user_id,
                llm=self.llm,
                use_codebase_tools=False,
                progress_callback=progress_callback,
            )
        elif pipeline_tag == NEED_CODING_TAG:
            self._emit_progress(progress_callback, {"type": "status", "text": "Ik zoek in de codebase…"})
            llm_response = run_agent_turn(
                agent_input=agent_input,
                db=db,
                household_id=household_id,
                user_id=user_id,
                llm=self.llm,
                use_codebase_tools=True,
                progress_callback=progress_callback,
            )
        else:
            llm_response = cleaned_reply

        llm_response = re.sub(r"\*\*(.+?)\*\*", r"\1", llm_response)
        llm_response = llm_response.strip()

        if user_id:
            self._store_context_snapshot(
                db=db,
                household_id=household_id,
                user_id=user_id,
                user_message=message,
                assistant_message=llm_response,
            )

        return {
            "message": llm_response,
            "reasoning": "",
            "actions": [],
        }
    
    def _scheduling_intent(self, message: str) -> bool:
        """True if the LLM interprets the message as scheduling/reminders (task mode)."""
        if not (message or "").strip():
            return False
        if not self.llm:
            return False
        messages = build_scheduling_intent_messages(message)
        try:
            raw = self.llm.chat(messages, temperature=0.0, max_tokens=64)
            data = _parse_json_object(raw)
            if isinstance(data, dict) and "scheduling_intent" in data:
                return bool(data["scheduling_intent"])
        except Exception:
            pass
        return False

    def _process_task_path(
        self,
        db: Session,
        household_id: int,
        user_id: Optional[int],
        user_id_str: str,
        message: str,
        conversation_history: Optional[List[Dict[str, str]]],
    ) -> Optional[Dict[str, Any]]:
        """Run task-mode via Observe -> Plan -> Act -> Validate -> Commit. Returns None to fall back to chat path."""
        start_run()
        try:
            task = get_or_create_task(user_id_str, message)
            if not can_make_turn(task):
                transition(task, FAILED)
                clear_active_task_id(user_id_str)
                end_run(False, "max_turns")
                record_run_result(False)
                return {
                    "message": "Too many steps; please try again with a shorter request.",
                    "reasoning": "",
                    "actions": [],
                }
            previous = []
            if conversation_history:
                previous = conversation_history[-4:]
            messages = build_task_messages(message, previous_exchanges=previous)
            raw = self.llm.chat(messages, temperature=0.3)
            kind, payload = parse_llm_output(
                raw, task.get("last_assistant_output"),
                allowed_tools=self.planner._tool_router.get_all_tool_names(),
            )
            transition(task, task.get("state"), increment_turn=True, last_assistant_output=raw)

            # Observe: state with pending_decision from LLM
            state = RunState(
                message=message,
                conversation_history=conversation_history,
                task=task,
                mode="task",
                pending_decision=(kind, payload),
            )
            context = RunContext(
                db=db,
                household_id=household_id,
                user_id=user_id,
                user_id_str=user_id_str,
                allowed_tools=self.guardrails.allowed_tools_for_context(),
            )
            action, observation, validation = run_one_turn(
                state, context, self.planner, self.executor, self.validator
            )

            if not validation.passed:
                end_run(False, validation.error)
                record_run_result(False)
                return {
                    "message": validation.error or "Blocked by policy.",
                    "reasoning": "",
                    "actions": [],
                }

            # Commit
            if action.type == "tool_call":
                if not can_execute_tool(task):
                    clear_active_task_id(user_id_str)
                    transition(task, FAILED)
                    end_run(False, "max_tool_attempts")
                    record_run_result(False)
                    return {
                        "message": "Maximum tool attempts reached for this task. Please start over.",
                        "reasoning": "",
                        "actions": [],
                    }
                transition(task, DONE, increment_tool_attempt=True)
                clear_active_task_id(user_id_str)
                end_run(True)
                record_run_result(True)
                if not observation.success:
                    msg = observation.error or "Something went wrong."
                else:
                    msg = self._task_result_to_message(action.tool, observation.output or {})
                return {"message": msg, "reasoning": "", "actions": []}

            if action.type == "need_info":
                transition(task, "NEEDS_INFO")
                end_run(True)
                record_run_result(True)
                msg = observation.message or "Please provide the requested information."
                return {"message": msg, "reasoning": "", "actions": []}

            if action.type == "final":
                transition(task, DONE)
                clear_active_task_id(user_id_str)
                end_run(True)
                record_run_result(True)
                return {"message": (action.message or "").strip() or "Done.", "reasoning": "", "actions": []}

            transition(task, FAILED)
            clear_active_task_id(user_id_str)
            end_run(False, "invalid_output")
            record_run_result(False)
            return {
                "message": "Please respond with only a JSON object (tool_call, need_info, or final). No other text.",
                "reasoning": "",
                "actions": [],
            }
        except Exception as e:
            end_run(False, str(e))
            record_run_result(False)
            raise

    def _store_context_snapshot(
        self,
        db: Session,
        household_id: int,
        user_id: int,
        user_message: str,
        assistant_message: str,
    ) -> None:
        """Ask LLM to extract context and store if useful."""
        from neuroion.core.agent.prompts import build_context_extraction_messages
        messages = build_context_extraction_messages(user_message, assistant_message)
        raw = self.llm.chat(messages, temperature=0.2)
        data = _parse_json_object(raw)
        if not isinstance(data, dict):
            return
        if (data.get("type") or "").strip().lower() != "context":
            return
        summary = str(data.get("summary") or "").strip()
        if not summary:
            return
        event_type = str(data.get("event_type") or "note").strip() or "note"
        metadata = data.get("metadata")
        scope = (data.get("scope") or "user").strip().lower()
        target_user_id = None if scope == "household" else user_id
        try:
            ContextSnapshotRepository.create(
                db=db,
                household_id=household_id,
                user_id=target_user_id,
                event_type=event_type[:50],
                summary=summary,
                context_metadata=metadata if isinstance(metadata, dict) else None,
            )
            # Also store in long-term user memories when scope is user (so agent learns about the user)
            if scope == "user" and user_id is not None:
                try:
                    UserMemoryRepository.create(
                        db=db,
                        household_id=household_id,
                        user_id=user_id,
                        memory_type=event_type[:50] or "note",
                        summary=summary,
                        memory_metadata=metadata if isinstance(metadata, dict) else None,
                    )
                except Exception:
                    pass
        except Exception:
            return

    def _task_result_to_message(self, tool: str, result: Dict[str, Any]) -> str:
        """Turn tool result into a short user-facing message."""
        if tool == "cron.add" and result.get("jobId"):
            return f"Herinnering gepland. (job {result['jobId'][:8]}...)"
        if tool == "cron.list" and "jobs" in result:
            n = len(result["jobs"])
            return f"Je hebt {n} geplande taak/taken." if n != 1 else "Je hebt 1 geplande taak."
        if tool == "cron.remove" and result.get("success"):
            return "Taak verwijderd."
        if tool == "cron.run" and result.get("success"):
            return "Taak uitgevoerd."
        if tool == "cron.runs" and "runs" in result:
            n = len(result["runs"])
            return f"Laatste {n} run(s)."
        return str(result.get("result", result))

    def execute_action(
        self,
        db: Session,
        household_id: int,
        user_id: Optional[int],
        action_id: int,
    ) -> Dict[str, Any]:
        """
        Execute a confirmed action.
        
        Args:
            db: Database session
            household_id: Household ID
            user_id: User ID
            action_id: Audit log ID of the action
        
        Returns:
            Execution result
        """
        from neuroion.core.memory.models import AuditLog
        
        # Get audit log
        audit_log = db.query(AuditLog).filter(AuditLog.id == action_id).first()
        if not audit_log:
            return {"success": False, "error": "Action not found"}
        
        # Confirm action
        AuditLogger.log_confirmation(db, action_id, user_id)
        
        # Get tool
        tool = self.tool_registry.get(audit_log.action_name)
        if not tool:
            AuditLogger.log_failure(db, action_id, f"Tool not found: {audit_log.action_name}")
            return {"success": False, "error": f"Tool not found: {audit_log.action_name}"}
        
        # Execute tool
        try:
            params = audit_log.input_data or {}
            params["household_id"] = household_id
            
            result = tool.func(db=db, **params)
            
            # Log success
            AuditLogger.log_execution(db, action_id, output_data=result)
            
            return {
                "success": True,
                "result": result,
            }
        except Exception as e:
            AuditLogger.log_failure(db, action_id, str(e))
            return {
                "success": False,
                "error": str(e),
            }


def _parse_json_object(raw: str) -> Optional[Dict[str, Any]]:
    """Best-effort parse of a single JSON object from a string."""
    if not raw:
        return None
    text = raw.strip()
    if text.startswith("{") and text.endswith("}"):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
    code = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text, re.IGNORECASE)
    if code:
        try:
            return json.loads(code.group(1).strip())
        except json.JSONDecodeError:
            pass
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
                try:
                    return json.loads(text[start : i + 1])
                except json.JSONDecodeError:
                    return None
    return None
