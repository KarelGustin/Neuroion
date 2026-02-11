"""
Guardrails: tool allowlist per agent/context, budget (max steps, tool calls, tokens).
"""
import re
from typing import Optional, Set

class Guardrails:
    """
    Allowlist of tools; budget limits per run.
    When allowlist is None, all registered tools are allowed.
    """

    def __init__(
        self,
        allowed_tools: Optional[Set[str]] = None,
        max_steps: int = 10,
        max_tool_calls: int = 5,
        max_tokens: Optional[int] = None,
    ) -> None:
        self.allowed_tools = allowed_tools  # None = allow all
        self.max_steps = max_steps
        self.max_tool_calls = max_tool_calls
        self.max_tokens = max_tokens

    def tool_allowed(self, tool_name: str) -> bool:
        if self.allowed_tools is None:
            return True
        return tool_name in self.allowed_tools

    def allowed_tools_for_context(self) -> Optional[Set[str]]:
        """Return the set to pass to RunContext.allowed_tools (None = no filter)."""
        return self.allowed_tools

    def within_budget(self, step_count: int, tool_call_count: int, token_count: Optional[int] = None) -> bool:
        if step_count >= self.max_steps:
            return False
        if tool_call_count >= self.max_tool_calls:
            return False
        if self.max_tokens is not None and token_count is not None and token_count >= self.max_tokens:
            return False
        return True


def get_guardrails(
    allowed_tools: Optional[Set[str]] = None,
    max_steps: int = 10,
    max_tool_calls: int = 5,
) -> Guardrails:
    """Default guardrails: optional allowlist (None = allow all), step and tool-call budget."""
    return Guardrails(
        allowed_tools=allowed_tools,
        max_steps=max_steps,
        max_tool_calls=max_tool_calls,
    )
