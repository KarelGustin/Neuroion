"""
Example skill module.

Demonstrates how to register a new tool for the agent.
"""
from typing import Dict, Any
from sqlalchemy.orm import Session

from neuroion.core.agent.tool_registry import register_tool


@register_tool(
    name="echo_text",
    description="Echo back a short message. Useful for testing tool calls.",
    parameters={
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Message to echo back"},
        },
        "required": ["text"],
    },
)
def echo_text(db: Session, household_id: int, text: str) -> Dict[str, Any]:
    """Return the same text."""
    return {"echo": text}
