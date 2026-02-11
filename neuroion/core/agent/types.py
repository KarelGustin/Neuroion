"""
Shared types for the agentic loop: RunContext, RunState, Action, ToolResult, Observation.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

# Pending decision from LLM: (kind, payload) where kind in ("tool_call", "need_info", "final")
PendingDecision = Tuple[str, Any]


@dataclass
class RunState:
    """State passed into Planner.next(): current message, conversation, task, last observation."""
    message: str
    conversation_history: Optional[List[Dict[str, str]]] = None
    task: Optional[Dict[str, Any]] = None  # task_manager task dict
    last_observation: Optional["Observation"] = None
    mode: str = "chat"  # "chat" | "task"
    # When set, planner converts this to Action without calling LLM (kind, payload from parse_llm_output)
    pending_decision: Optional[PendingDecision] = None


@dataclass
class RunContext:
    """Context passed through the agent loop (Observe -> Plan -> Act -> Validate -> Commit)."""
    db: Any
    household_id: int
    user_id: Optional[int] = None
    user_id_str: str = "0"
    # Optional allowlist of tool names; if set, tool_router will reject tools not in set
    allowed_tools: Optional[Set[str]] = None


@dataclass
class ToolResult:
    """Result of a single tool invocation."""
    success: bool
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    @classmethod
    def from_dispatcher_result(cls, result: Dict[str, Any]) -> "ToolResult":
        """Build from the dict returned by tools.dispatcher.execute_tool."""
        if result.get("success") is False:
            return cls(success=False, error=result.get("error", "Unknown error"), output=result)
        return cls(success=True, output=result, error=None)


@dataclass
class Action:
    """Single step produced by the planner: tool_call, need_info, final, or sub_goal."""
    type: str  # "tool_call" | "need_info" | "final" | "sub_goal"
    tool: str = ""
    args: Dict[str, Any] = field(default_factory=dict)
    questions: List[str] = field(default_factory=list)
    message: str = ""

    @classmethod
    def tool_call(cls, tool: str, args: Optional[Dict[str, Any]] = None) -> "Action":
        return cls(type="tool_call", tool=tool, args=args or {})

    @classmethod
    def need_info(cls, questions: List[str]) -> "Action":
        return cls(type="need_info", questions=questions)

    @classmethod
    def final(cls, message: str) -> "Action":
        return cls(type="final", message=message)


@dataclass
class Observation:
    """Result of executing one Action (from Executor.run)."""
    action: Action
    success: bool
    # For tool_call: tool result summary or error
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    # For need_info: echoed questions; for final: the message
    message: Optional[str] = None
    # Optional metadata (latency, tokens, etc.)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_tool_result(cls, action: Action, tool_result: ToolResult, metadata: Optional[Dict[str, Any]] = None) -> "Observation":
        return cls(
            action=action,
            success=tool_result.success,
            output=tool_result.output,
            error=tool_result.error,
            metadata=metadata or {},
        )

    @classmethod
    def need_info(cls, action: Action) -> "Observation":
        return cls(action=action, success=True, message=" ".join(action.questions) if action.questions else None)

    @classmethod
    def final(cls, action: Action) -> "Observation":
        return cls(action=action, success=True, message=action.message)
