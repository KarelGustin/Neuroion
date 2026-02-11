"""
Single facade for all tools: cron + registry.
call(tool_name, args, context) -> ToolResult with optional allowlist (guardrails).
"""
import logging
from typing import Any, Dict, List, Optional, Set

from neuroion.core.agent.cron_tools_schema import get_cron_tools_for_llm
from neuroion.core.agent.tool_registry import get_tool_registry
from neuroion.core.agent.tools.dispatcher import execute_tool
from neuroion.core.agent.types import RunContext, ToolResult

logger = logging.getLogger(__name__)


def _cron_tool_names() -> Set[str]:
    return {t.get("function", {}).get("name") for t in get_cron_tools_for_llm() if t.get("function")}


class ToolRouter:
    """
    One registry + dispatch for cron and registry tools.
    call(tool_name, args, context) -> ToolResult; optional allowlist in context.
    """

    def __init__(self) -> None:
        self._registry = get_tool_registry()

    def get_all_tools_for_llm(self) -> List[Dict[str, Any]]:
        """Cron tools + registry tools in OpenAI function format."""
        return get_cron_tools_for_llm() + self._registry.get_tools_for_llm()

    def get_all_tool_names(self) -> Set[str]:
        """Set of all known tool names (cron + registry)."""
        return _cron_tool_names() | set(self._registry.get_tool_names())

    def call(
        self,
        tool_name: str,
        args: Dict[str, Any],
        context: RunContext,
    ) -> ToolResult:
        """
        Execute a tool by name. Validates allowlist if context.allowed_tools is set.
        Returns ToolResult(success, output, error).
        """
        args = args or {}
        if context.allowed_tools is not None and tool_name not in context.allowed_tools:
            logger.warning("Tool %s not in allowlist", tool_name)
            return ToolResult(success=False, error=f"Tool not allowed: {tool_name}")

        result = execute_tool(
            tool_name,
            args,
            context.user_id_str,
            db=context.db,
            household_id=context.household_id,
            user_id_int=context.user_id,
        )
        return ToolResult.from_dispatcher_result(result)


def get_tool_router() -> ToolRouter:
    """Return the global tool router instance."""
    return _router


_router = ToolRouter()
