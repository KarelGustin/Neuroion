"""
Tool registry and implementations.

Defines executable tools that the agent can use to perform actions.
All tools are pure Python functions with validated input/output.
"""
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import importlib
import pkgutil

from neuroion.core.memory.repository import (
    PreferenceRepository,
    ContextSnapshotRepository,
    AuditLogRepository,
)
from sqlalchemy.orm import Session


@dataclass
class Tool:
    """Tool definition with metadata."""
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema for parameters
    func: Callable


class ToolRegistry:
    """Registry for all available tools."""
    
    def __init__(self):
        self._tools: Dict[str, Tool] = {}
    
    def register(self, tool: Tool) -> None:
        """Register a tool."""
        self._tools[tool.name] = tool
    
    def get(self, name: str) -> Optional[Tool]:
        """Get a tool by name."""
        return self._tools.get(name)
    
    def list_tools(self) -> List[Tool]:
        """List all registered tools."""
        return list(self._tools.values())
    
    def get_tools_for_llm(self) -> List[Dict[str, Any]]:
        """Get tool definitions formatted for OpenAI-compatible tool calling."""
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            }
            for tool in self._tools.values()
        ]

    def get_tool_names(self) -> List[str]:
        """Return registered tool names."""
        return list(self._tools.keys())


# Global tool registry
_tool_registry = ToolRegistry()


def register_tool(
    name: str,
    description: str,
    parameters: Dict[str, Any],
):
    """
    Decorator to register a tool.
    
    Usage:
        @register_tool(
            name="generate_week_menu",
            description="Generate a weekly meal menu based on preferences",
            parameters={
                "type": "object",
                "properties": {
                    "dietary_restrictions": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["dietary_restrictions"],
            }
        )
        def generate_week_menu(db: Session, dietary_restrictions: List[str]) -> Dict[str, Any]:
            ...
    """
    def decorator(func: Callable) -> Callable:
        tool = Tool(
            name=name,
            description=description,
            parameters=parameters,
            func=func,
        )
        _tool_registry.register(tool)
        return func
    return decorator


def get_tool_registry() -> ToolRegistry:
    """Get the global tool registry."""
    return _tool_registry


def _load_skill_modules() -> None:
    """Auto-import skill modules so they can register tools."""
    try:
        from neuroion.core.agent import skills as skills_pkg
    except Exception:
        return
    for module in pkgutil.iter_modules(skills_pkg.__path__):
        if module.name.startswith("_"):
            continue
        importlib.import_module(f"{skills_pkg.__name__}.{module.name}")


# Tool implementations

@register_tool(
    name="generate_week_menu",
    description="Generate a weekly meal menu based on household preferences and dietary restrictions",
    parameters={
        "type": "object",
        "properties": {
            "dietary_restrictions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of dietary restrictions (e.g., 'vegetarian', 'gluten-free')",
            },
            "preferences": {
                "type": "object",
                "description": "Additional meal preferences",
            },
        },
        "required": [],
    }
)
def generate_week_menu(
    db: Session,
    household_id: int,
    dietary_restrictions: Optional[List[str]] = None,
    preferences: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Generate a weekly meal menu.
    
    Returns:
        Dict with days of week and meal suggestions
    """
    # Get household preferences
    household_prefs = PreferenceRepository.get_all(db, household_id, category="dietary")
    
    # Build menu structure
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    menu = {}
    
    for day in days:
        menu[day] = {
            "breakfast": "Suggested breakfast based on preferences",
            "lunch": "Suggested lunch based on preferences",
            "dinner": "Suggested dinner based on preferences",
        }
    
    return {
        "menu": menu,
        "dietary_restrictions": dietary_restrictions or [],
        "generated_at": datetime.utcnow().isoformat(),
    }


@register_tool(
    name="create_grocery_list",
    description="Create a grocery shopping list based on meal plans and household preferences",
    parameters={
        "type": "object",
        "properties": {
            "menu_id": {
                "type": "string",
                "description": "Optional menu ID to base list on",
            },
            "additional_items": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Additional items to add to the list",
            },
        },
        "required": [],
    }
)
def create_grocery_list(
    db: Session,
    household_id: int,
    menu_id: Optional[str] = None,
    additional_items: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Create a grocery shopping list.
    
    Returns:
        Dict with categorized grocery items
    """
    # Get household preferences for common items
    prefs = PreferenceRepository.get_all(db, household_id, category="grocery")
    
    items = {
        "produce": [],
        "dairy": [],
        "meat": [],
        "pantry": [],
        "other": additional_items or [],
    }
    
    # Add items based on preferences
    for pref in prefs:
        if pref.key == "common_items" and isinstance(pref.value, list):
            items["pantry"].extend(pref.value)
    
    return {
        "list": items,
        "created_at": datetime.utcnow().isoformat(),
        "total_items": sum(len(category) for category in items.values()),
    }


@register_tool(
    name="summarize_family_preferences",
    description="Summarize household and family member preferences for context",
    parameters={
        "type": "object",
        "properties": {
            "categories": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Specific preference categories to include",
            },
        },
        "required": [],
    }
)
def summarize_family_preferences(
    db: Session,
    household_id: int,
    categories: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Summarize family preferences.
    
    Returns:
        Dict with household and user-level preferences
    """
    # Get household-level preferences
    household_prefs = PreferenceRepository.get_all(db, household_id)
    if categories:
        household_prefs = [p for p in household_prefs if p.category in categories]
    
    # Get user-level preferences
    from neuroion.core.memory.repository import UserRepository
    users = UserRepository.get_by_household(db, household_id)
    
    user_prefs = {}
    for user in users:
        user_prefs[user.name] = PreferenceRepository.get_all(db, household_id, user_id=user.id)
    
    return {
        "household_preferences": {
            pref.key: pref.value for pref in household_prefs
        },
        "user_preferences": {
            name: {pref.key: pref.value for pref in prefs}
            for name, prefs in user_prefs.items()
        },
        "summary": f"Found {len(household_prefs)} household preferences and preferences for {len(users)} users",
    }


@register_tool(
    name="get_dashboard_link",
    description="Get personal dashboard link for the user. Use this when user asks for their dashboard, personal page, or wants to manage integrations. This will generate a login code that expires in 60 seconds.",
    parameters={
        "type": "object",
        "properties": {},
        "required": [],
    }
)
def get_dashboard_link(
    db: Session,
    household_id: int,
    user_id: int,
) -> Dict[str, Any]:
    """
    Get personal dashboard link for user and generate a login code.
    
    Returns:
        Dict with dashboard URL and 4-digit login code
    """
    from neuroion.core.memory.repository import DashboardLinkRepository, LoginCodeRepository
    from neuroion.core.config import settings
    from neuroion.core.services.network import get_dashboard_base_url
    
    # Get or create dashboard link
    link = DashboardLinkRepository.get_or_create(db, user_id)
    
    # Generate login code (expires in 60 seconds)
    login_code = LoginCodeRepository.create_for_user(db, user_id, expires_in_seconds=60)
    
    # Construct URL using detected local IP (works for mobile access)
    base_url = get_dashboard_base_url(settings.dashboard_ui_port, prefer_localhost=False)
    url = f"{base_url}/user/{user_id}"
    
    return {
        "url": url,
        "code": login_code.code,
        "expires_at": login_code.expires_at.isoformat(),
        "message": (
            f"🔗 Your Personal Dashboard\n\n"
            f"Link: {url}\n\n"
            f"Login Code: {login_code.code}\n"
            f"⏱ Valid for 60 seconds"
        ),
    }


_load_skill_modules()
