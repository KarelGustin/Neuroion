"""
Planner for multi-step action sequences.

Validates action sequences and manages dependencies between actions.
Provides next(state) -> Action for the agentic loop (task path can use LLM internally).
"""
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass

from neuroion.core.agent.types import Action, RunState
from neuroion.core.agent.tool_protocol import parse_llm_output
from neuroion.core.agent.tool_router import get_tool_router


@dataclass
class ActionStep:
    """Represents a single action step in a plan."""
    tool_name: str
    parameters: Dict[str, Any]
    description: str
    depends_on: List[int] = None  # Indices of steps this depends on
    
    def __post_init__(self):
        if self.depends_on is None:
            self.depends_on = []


@dataclass
class ActionPlan:
    """Represents a complete action plan."""
    steps: List[ActionStep]
    reasoning: str
    estimated_duration: Optional[str] = None


class Planner:
    """Plans and validates multi-step action sequences. Supports next(state) -> Action."""

    def __init__(
        self,
        tool_registry: Any,
        llm: Any = None,
        build_task_messages: Optional[Callable[..., List[Dict[str, Any]]]] = None,
    ) -> None:
        """
        Initialize planner.

        Args:
            tool_registry: ToolRegistry instance
            llm: Optional LLM client for task-mode next() (calls LLM + parse_llm_output)
            build_task_messages: Optional fn(message, previous_exchanges) -> messages for task mode
        """
        self.tool_registry = tool_registry
        self.llm = llm
        self.build_task_messages = build_task_messages
        self._tool_router = get_tool_router()

    def next(self, state: RunState) -> Action:
        """
        Decide next action from current state. Returns a single Action.

        - If state.pending_decision is set (kind, payload), converts to Action.
        - Else if state.mode == "task" and state.task and LLM/build_task_messages are set,
          builds messages, calls LLM, parses output, returns Action.
        - Otherwise returns Action.final("") as fallback.
        """
        if state.pending_decision is not None:
            kind, payload = state.pending_decision
            if kind == "tool_call" and payload is not None:
                return Action.tool_call(getattr(payload, "tool", ""), getattr(payload, "args", {}))
            if kind == "need_info" and payload is not None:
                return Action.need_info(getattr(payload, "questions", []) or [])
            if kind == "final" and payload is not None:
                return Action.final(getattr(payload, "message", "") or "")
            # invalid or unknown
            return Action.final("")

        if (
            state.mode == "task"
            and state.task
            and self.llm is not None
            and self.build_task_messages is not None
        ):
            previous = (state.conversation_history or [])[-4:]
            messages = self.build_task_messages(state.message, previous_exchanges=previous)
            raw = self.llm.chat(messages, temperature=0.3)
            allowed = self._tool_router.get_all_tool_names()
            kind, payload = parse_llm_output(raw, state.task.get("last_assistant_output"), allowed_tools=allowed)
            if kind == "tool_call" and payload is not None:
                return Action.tool_call(getattr(payload, "tool", ""), getattr(payload, "args", {}))
            if kind == "need_info" and payload is not None:
                return Action.need_info(getattr(payload, "questions", []) or [])
            if kind == "final" and payload is not None:
                return Action.final(getattr(payload, "message", "") or "")
            return Action.final("")

        return Action.final("")

    def create_plan(
        self,
        goal: str,
        tool_names: List[str],
        parameters_list: List[Dict[str, Any]],
        reasoning: str,
    ) -> ActionPlan:
        """
        Create an action plan from goal and tool calls.
        
        Args:
            goal: What we're trying to achieve
            tool_names: List of tool names to execute
            parameters_list: List of parameter dicts for each tool
            reasoning: Why this plan was created
        
        Returns:
            ActionPlan object
        """
        steps = []
        for i, (tool_name, params) in enumerate(zip(tool_names, parameters_list)):
            tool = self.tool_registry.get(tool_name)
            if not tool:
                raise ValueError(f"Unknown tool: {tool_name}")
            
            step = ActionStep(
                tool_name=tool_name,
                parameters=params,
                description=f"Execute {tool_name}",
            )
            steps.append(step)
        
        return ActionPlan(
            steps=steps,
            reasoning=reasoning,
        )
    
    def validate_plan(self, plan: ActionPlan) -> tuple[bool, Optional[str]]:
        """
        Validate an action plan.
        
        Args:
            plan: ActionPlan to validate
        
        Returns:
            (is_valid, error_message)
        """
        # Check all tools exist
        for step in plan.steps:
            tool = self.tool_registry.get(step.tool_name)
            if not tool:
                return False, f"Unknown tool: {step.tool_name}"
            
            # Validate parameters against tool schema
            # This is a simplified check - in production, use JSON Schema validation
            if not isinstance(step.parameters, dict):
                return False, f"Invalid parameters for {step.tool_name}: must be dict"
        
        # Check for circular dependencies
        if self._has_circular_dependencies(plan):
            return False, "Circular dependencies detected in plan"
        
        return True, None
    
    def _has_circular_dependencies(self, plan: ActionPlan) -> bool:
        """Check if plan has circular dependencies."""
        # Build dependency graph
        graph = {i: set(step.depends_on) for i, step in enumerate(plan.steps)}
        
        # Check for cycles using DFS
        visited = set()
        rec_stack = set()
        
        def has_cycle(node):
            visited.add(node)
            rec_stack.add(node)
            
            for dep in graph.get(node, []):
                if dep not in visited:
                    if has_cycle(dep):
                        return True
                elif dep in rec_stack:
                    return True
            
            rec_stack.remove(node)
            return False
        
        for node in range(len(plan.steps)):
            if node not in visited:
                if has_cycle(node):
                    return True
        
        return False
    
    def execute_plan(
        self,
        plan: ActionPlan,
        db,
        household_id: int,
    ) -> List[Dict[str, Any]]:
        """
        Execute an action plan in order.
        
        Args:
            plan: ActionPlan to execute
            db: Database session
            household_id: Household ID
        
        Returns:
            List of tool execution results
        """
        results = []
        
        for step in plan.steps:
            tool = self.tool_registry.get(step.tool_name)
            if not tool:
                results.append({
                    "step": step.tool_name,
                    "success": False,
                    "error": f"Tool not found: {step.tool_name}",
                })
                continue
            
            try:
                # Execute tool with household_id injected
                step_params = step.parameters.copy()
                step_params["household_id"] = household_id
                
                result = tool.func(db=db, **step_params)
                results.append({
                    "step": step.tool_name,
                    "success": True,
                    "result": result,
                })
            except Exception as e:
                results.append({
                    "step": step.tool_name,
                    "success": False,
                    "error": str(e),
                })
        
        return results
