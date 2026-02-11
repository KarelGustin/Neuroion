"""
Tool dispatcher: registry of tool name -> handler, unified execute with validation and error handling.
"""
import logging
import inspect
from typing import Any, Callable, Dict, Optional

from neuroion.core.agent.tools.cron_handlers import CRON_HANDLERS
from neuroion.core.cron.validation import CronValidationError
from neuroion.core.agent.tool_registry import get_tool_registry

logger = logging.getLogger(__name__)

_registry: Dict[str, Callable[[str, Dict[str, Any]], Dict[str, Any]]] = dict(CRON_HANDLERS)


def register(name: str, handler: Callable[[str, Dict[str, Any]], Dict[str, Any]]) -> None:
    """Register a tool handler."""
    _registry[name] = handler


def get_dispatcher() -> Dict[str, Callable]:
    """Return the registry (read-only view)."""
    return dict(_registry)


def execute_tool(
    tool_name: str,
    args: Dict[str, Any],
    user_id: str,
    db: Optional[Any] = None,
    household_id: Optional[int] = None,
    user_id_int: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Execute a tool by name. Validates via cron contract (handled inside CronService).
    Returns result dict; on error returns {success: false, error: "..."}.
    """
    user_id = str(user_id)
    args = args or {}
    handler = _registry.get(tool_name)
    if not handler:
        tool = get_tool_registry().get(tool_name)
        if not tool:
            logger.warning("Unknown tool: %s", tool_name)
            return {"success": False, "error": f"Unknown tool: {tool_name}"}
        if db is None or household_id is None:
            return {"success": False, "error": f"Tool {tool_name} requires db and household_id"}
        try:
            kwargs = _build_tool_kwargs(tool.func, args, household_id, user_id_int)
            result = tool.func(db=db, **kwargs)
            logger.info("Tool %s executed for user %s", tool_name, user_id)
            return result if isinstance(result, dict) else {"success": True, "result": result}
        except Exception as e:
            logger.exception("Tool %s failed: %s", tool_name, e)
            return {"success": False, "error": str(e)}
    try:
        result = handler(user_id, args)
        logger.info("Tool %s executed for user %s", tool_name, user_id)
        return result if isinstance(result, dict) else {"success": True, "result": result}
    except CronValidationError as e:
        logger.info("Tool %s validation failed: %s", tool_name, e)
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.exception("Tool %s failed: %s", tool_name, e)
        return {"success": False, "error": str(e)}


def _build_tool_kwargs(
    func: Callable,
    args: Dict[str, Any],
    household_id: Optional[int],
    user_id_int: Optional[int],
) -> Dict[str, Any]:
    """Filter/augment args for a tool function based on its signature."""
    sig = inspect.signature(func)
    kwargs = dict(args or {})
    if household_id is not None and "household_id" in sig.parameters and "household_id" not in kwargs:
        kwargs["household_id"] = household_id
    if user_id_int is not None and "user_id" in sig.parameters and "user_id" not in kwargs:
        kwargs["user_id"] = user_id_int
    allowed = set(sig.parameters.keys()) - {"db"}
    return {k: v for k, v in kwargs.items() if k in allowed}
