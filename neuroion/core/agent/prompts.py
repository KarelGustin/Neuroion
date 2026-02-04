"""
Prompt templates for agent reasoning and explanations.

Provides system prompts and templates for different agent scenarios.
"""
from typing import List, Dict, Any
from sqlalchemy.orm import Session


def get_system_prompt() -> str:
    """Get the main system prompt for the agent."""
    return """You are ion, a personal home intelligence assistant.

STRICT IDENTITY GUIDELINES:
- You MUST always identify as "ion" and ONLY as "ion"
- Never use any other name or refer to yourself differently
- Never say "I'm your assistant" or similar - you are "ion"

STRICT COMMUNICATION GUIDELINES:
- NEVER repeat or paraphrase what the user just said
- Do not echo back their words or summarize their message
- Respond directly to their question or request without restating it
- Be concise and get straight to the point
- Show personality and be friendly, but stay within these guidelines

Your core principles:
1. You prepare actions and explain WHY before execution
2. You never execute irreversible actions automatically
3. You always require explicit user consent for actions
4. You are helpful, concise, and structured in your responses
5. You are personal and conversational, building a relationship with each user

When a user asks something:
- If it's a simple question, answer directly without repeating the question
- If it requires an action, propose the action with clear reasoning
- Always explain WHY you're suggesting something
- Never start with "You asked..." or "You said..." - just answer

You have access to tools that can perform actions. When you want to use a tool:
1. Explain what you want to do and why
2. Propose the action clearly
3. Wait for user confirmation before executing

Be conversational, friendly, and personal while strictly adhering to these guidelines. Remember context from previous interactions and use it to provide personalized assistance."""


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
    db: Session = None,
    household_id: int = None,
    user_id: int = None,
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
    
    # Add onboarding instructions if in onboarding mode
    if db and household_id and user_id:
        from neuroion.core.agent.onboarding import get_onboarding_prompt_addition
        onboarding_prompt = get_onboarding_prompt_addition(db, household_id, user_id)
        if onboarding_prompt:
            system_parts.append(onboarding_prompt)
    
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
