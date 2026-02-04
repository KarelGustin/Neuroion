"""
Prompt templates for agent reasoning and explanations.

Provides system prompts and templates for different agent scenarios.
"""
from typing import List, Dict, Any


def get_system_prompt() -> str:
    """Get the main system prompt for the agent."""
    return """You are Neuroion, a local-first home intelligence assistant.

Your core principles:
1. You prepare actions and explain WHY before execution
2. You never execute irreversible actions automatically
3. You always require explicit user consent for actions
4. You are helpful, concise, and structured in your responses

When a user asks something:
- If it's a simple question, answer directly
- If it requires an action, propose the action with clear reasoning
- Always explain WHY you're suggesting something

You have access to tools that can perform actions. When you want to use a tool:
1. Explain what you want to do and why
2. Propose the action clearly
3. Wait for user confirmation before executing

Be conversational but professional. Remember context from previous interactions."""


def format_context_snapshots(snapshots: List[Dict[str, Any]]) -> str:
    """
    Format context snapshots for inclusion in prompts.
    
    Args:
        snapshots: List of context snapshot dicts
    
    Returns:
        Formatted string for prompt
    """
    if not snapshots:
        return "No recent context available."
    
    lines = ["Recent context:"]
    for snap in snapshots[:10]:  # Limit to 10 most recent
        timestamp = snap.get("timestamp", "")
        event_type = snap.get("event_type", "")
        summary = snap.get("summary", "")
        lines.append(f"- [{timestamp}] {event_type}: {summary}")
    
    return "\n".join(lines)


def format_preferences(preferences: Dict[str, Any]) -> str:
    """
    Format preferences for inclusion in prompts.
    
    Args:
        preferences: Dict of preferences
    
    Returns:
        Formatted string for prompt
    """
    if not preferences:
        return "No preferences stored."
    
    lines = ["Household preferences:"]
    for key, value in list(preferences.items())[:20]:  # Limit to 20
        if isinstance(value, (dict, list)):
            value_str = str(value)[:100]  # Truncate long values
        else:
            value_str = str(value)
        lines.append(f"- {key}: {value_str}")
    
    return "\n".join(lines)


def build_chat_messages(
    user_message: str,
    context_snapshots: List[Dict[str, Any]] = None,
    preferences: Dict[str, Any] = None,
    conversation_history: List[Dict[str, str]] = None,
) -> List[Dict[str, str]]:
    """
    Build message list for LLM chat completion.
    
    Args:
        user_message: Current user message
        context_snapshots: Recent context snapshots
        preferences: Household preferences
        conversation_history: Previous messages in conversation
    
    Returns:
        List of message dicts for LLM
    """
    messages = []
    
    # System prompt with context
    system_parts = [get_system_prompt()]
    
    if preferences:
        system_parts.append("\n" + format_preferences(preferences))
    
    if context_snapshots:
        system_parts.append("\n" + format_context_snapshots(context_snapshots))
    
    messages.append({
        "role": "system",
        "content": "\n".join(system_parts),
    })
    
    # Conversation history
    if conversation_history:
        messages.extend(conversation_history[-10:])  # Last 10 messages
    
    # Current user message
    messages.append({
        "role": "user",
        "content": user_message,
    })
    
    return messages


def build_reasoning_prompt(
    user_intent: str,
    available_tools: List[Dict[str, Any]],
    context: Dict[str, Any] = None,
) -> str:
    """
    Build a prompt for the agent to reason about actions.
    
    Args:
        user_intent: What the user wants
        available_tools: List of available tools
        context: Additional context
    
    Returns:
        Reasoning prompt string
    """
    prompt_parts = [
        f"User intent: {user_intent}",
        "",
        "Available tools:",
    ]
    
    for tool in available_tools:
        prompt_parts.append(f"- {tool['name']}: {tool['description']}")
    
    prompt_parts.extend([
        "",
        "Decide:",
        "1. Should you answer directly, or propose an action?",
        "2. If proposing an action, which tool should you use?",
        "3. What is your reasoning for this decision?",
        "",
        "Respond in this format:",
        "DECISION: [answer|action]",
        "TOOL: [tool_name if action]",
        "REASONING: [explanation]",
    ])
    
    return "\n".join(prompt_parts)
