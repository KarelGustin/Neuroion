"""
Main agent orchestrator.

Interprets user intent, decides on actions, and coordinates tool execution.
Supports LLM tool-calling for cron.* tools (scheduling/reminders).
"""
import json
import re
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from neuroion.core.llm import get_llm_client_from_config
from neuroion.core.agent.tool_registry import get_tool_registry
from neuroion.core.agent.planner import Planner
from neuroion.core.agent.gateway import run_agent_turn
from neuroion.core.agent.types import RunContext, RunState
from neuroion.core.agent.executor import get_executor
from neuroion.core.agent.agent_loop import run_one_turn
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
from neuroion.core.agent.prompts import build_scheduling_intent_messages
from neuroion.core.agent.policies.guardrails import get_guardrails
from neuroion.core.agent.policies.validator import get_validator
from neuroion.core.observability.tracing import start_run, end_run
from neuroion.core.observability.metrics import record_run_result
from neuroion.core.memory.repository import ContextSnapshotRepository
from neuroion.core.security.audit import AuditLogger


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
    
    def process_message(
        self,
        db: Session,
        household_id: int,
        user_id: Optional[int],
        message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        force_task_mode: bool = False,
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
        # Get context
        context_snapshots = ContextSnapshotRepository.get_recent(
            db, household_id, limit=10, user_id=user_id
        )
        context_dicts = [
            {
                "timestamp": str(snap.timestamp),
                "event_type": snap.event_type,
                "summary": snap.summary,
            }
            for snap in context_snapshots
        ]
        
        # Get LLM client from config (refresh on each call to ensure latest config)
        self.llm = get_llm_client_from_config(db)

        # Task path only when client explicitly requests it (X-Agent-Task-Mode: 1)
        user_id_str = str(user_id) if user_id is not None else "0"
        if force_task_mode and self._scheduling_intent(message):
            result = self._process_task_path(
                db, household_id, user_id, user_id_str, message, conversation_history
            )
            if result is not None:
                return result

        llm_response = run_agent_turn(
            db=db,
            household_id=household_id,
            user_id=user_id,
            message=message,
            conversation_history=conversation_history,
            llm=self.llm,
            context_snapshots=context_dicts,
            user_preferences=None,
            household_preferences=None,
        )
        # Post-process response: strip markdown bold syntax and trim
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
