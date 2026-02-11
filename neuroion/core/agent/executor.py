"""
Executor: runs one Action and returns an Observation.
Uses ToolRouter for tool_call actions.
"""
import logging
import time
from typing import Any, Dict, Optional

from neuroion.core.agent.tool_router import ToolRouter, get_tool_router
from neuroion.core.agent.types import Action, Observation, RunContext, ToolResult

logger = logging.getLogger(__name__)


class Executor:
    """Executes a single Action; returns Observation."""

    def __init__(self, tool_router: Optional[ToolRouter] = None) -> None:
        self.tool_router = tool_router or get_tool_router()

    def run(self, action: Action, context: RunContext) -> Observation:
        """
        Execute the action and return an observation.
        For tool_call: invokes tool_router.call; for need_info/final: returns observation directly.
        """
        if action.type == "tool_call":
            start = time.perf_counter()
            result = self.tool_router.call(action.tool, action.args, context)
            latency_ms = (time.perf_counter() - start) * 1000
            metadata: Dict[str, Any] = {"latency_ms": round(latency_ms, 2)}
            return Observation.from_tool_result(action, result, metadata=metadata)
        if action.type == "need_info":
            return Observation.need_info(action)
        if action.type == "final":
            return Observation.final(action)
        if action.type == "sub_goal":
            logger.warning("sub_goal action not implemented; returning failure")
            return Observation(
                action=action,
                success=False,
                error="sub_goal not implemented",
                metadata={},
            )
        return Observation(
            action=action,
            success=False,
            error=f"Unknown action type: {action.type}",
            metadata={},
        )


def get_executor() -> Executor:
    """Return a default Executor instance."""
    return Executor()
