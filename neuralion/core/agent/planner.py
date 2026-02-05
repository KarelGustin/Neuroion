"""
Planner for multi-step action sequences.

Validates action sequences and manages dependencies between actions.
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


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
    """Plans and validates multi-step action sequences."""
    
    def __init__(self, tool_registry):
        """
        Initialize planner.
        
        Args:
            tool_registry: ToolRegistry instance
        """
        self.tool_registry = tool_registry
    
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
