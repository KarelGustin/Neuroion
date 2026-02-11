"""
Prompt templates for agent reasoning and explanations.

Provides system prompts and templates for different agent scenarios.
"""
from typing import List, Dict, Any
import json
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
- Be concise: Keep responses to 1-3 sentences unless the user explicitly asks for more detail
- NEVER use markdown formatting - no **bold**, no *italic*, no code blocks, no formatting of any kind
- Write as a normal human assistant would speak - plain text only
- Show personality and be friendly, but stay within these guidelines

Your core principles:
1. You can use tools directly when needed to help the user
2. You never execute irreversible actions automatically
3. You are helpful, concise, and structured in your responses
4. You are personal and conversational, building a relationship with each user

ONE RESPONSE PER MESSAGE:
- Give exactly one answer: either a direct reply to the user's question, OR (if you take an action) only the outcome of that action (one short confirmation or one clarification question). Never give both a chat answer and a separate tool result as two responses; the user must receive a single, coherent message.

When a user asks something:
- If it's a simple question, answer directly without repeating the question
- If it requires an action, use the right tool; the system will then ask you for one final message—give only that (e.g. a short confirmation or one clarification). Do not pre-explain and then tool-call; either answer or act, then one update.
- Never start with "You asked..." or "You said..." - just answer
- Keep responses brief and to the point - 1-3 sentences is ideal
- Never use markdown formatting like **bold** or any other formatting symbols

You have access to tools that can perform actions. Use tools whenever they are needed to complete the request. Ask for clarification only when required information is missing.

Be conversational, friendly, and personal while strictly adhering to these guidelines. Remember context from previous interactions and use it to provide personalized assistance."""


def get_scheduling_prompt_addition() -> str:
    """Addition to system prompt: when user asks for scheduling/reminders, use cron.* tools. Default timezone Europe/Amsterdam."""
    return (
        "\n\nScheduling and reminders: When the user asks for a reminder or scheduled action, use the cron.* tools. "
        "If you have enough context (time, message, recurrence), call the tool immediately; the user will receive one confirmation (e.g. 'Herinnering gepland'). "
        "If something is missing (e.g. exact time or reminder text), ask once briefly for that detail—then one message only. "
        "Do not give a long explanation and then a separate tool result; one short confirmation or one clarification is enough. "
        "Use Europe/Amsterdam as default timezone when not specified."
    )


def get_structured_tool_prompt(tools: List[Dict[str, Any]]) -> str:
    """System prompt for structured JSON tool selection."""
    tool_lines = []
    for tool in tools:
        name = tool.get("name", "")
        description = tool.get("description", "")
        parameters = tool.get("parameters", {})
        tool_lines.append(f"- {name}: {description}")
        tool_lines.append(f"  parameters: {json.dumps(parameters, ensure_ascii=False)}")
    tool_text = "\n".join(tool_lines) if tool_lines else "No tools available."
    return (
        "You must respond with exactly one JSON object. No other text.\n\n"
        "Allowed forms only:\n"
        "1) {\"type\":\"tool_call\",\"tool\":\"<name>\",\"args\":{...}}\n"
        "2) {\"type\":\"need_info\",\"questions\":[\"question1\",\"question2\"]}\n"
        "3) {\"type\":\"final\",\"message\":\"<reply to user>\"}\n\n"
        "Choose tool_call only if a tool is needed. If missing details, use need_info.\n\n"
        "Available tools:\n"
        f"{tool_text}"
    )


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


def format_preferences(
    user_preferences: Dict[str, Any] = None,
    household_preferences: Dict[str, Any] = None,
) -> str:
    """
    Format preferences for inclusion in prompts.
    
    Args:
        user_preferences: Dict of user-specific preferences
        household_preferences: Dict of household-level preferences
    
    Returns:
        Formatted string for prompt
    """
    lines = []
    
    if household_preferences:
        lines.append("Household preferences (shared by all members):")
        for key, value in list(household_preferences.items())[:20]:  # Limit to 20
            if isinstance(value, (dict, list)):
                value_str = str(value)[:100]  # Truncate long values
            else:
                value_str = str(value)
            lines.append(f"- {key}: {value_str}")
    
    if user_preferences:
        if household_preferences:
            lines.append("")  # Empty line between sections
        lines.append("User-specific preferences (override household preferences):")
        for key, value in list(user_preferences.items())[:20]:  # Limit to 20
            if isinstance(value, (dict, list)):
                value_str = str(value)[:100]  # Truncate long values
            else:
                value_str = str(value)
            lines.append(f"- {key}: {value_str}")
    
    if not lines:
        return "No preferences stored."
    
    return "\n".join(lines)


def build_chat_messages(
    user_message: str,
    context_snapshots: List[Dict[str, Any]] = None,
    preferences: Dict[str, Any] = None,
    user_preferences: Dict[str, Any] = None,
    household_preferences: Dict[str, Any] = None,
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
    system_parts.append(get_scheduling_prompt_addition())

    # Add onboarding instructions if in onboarding mode
    if db and household_id and user_id:
        from neuroion.core.agent.onboarding import get_onboarding_prompt_addition
        onboarding_prompt = get_onboarding_prompt_addition(db, household_id, user_id)
        if onboarding_prompt:
            system_parts.append(onboarding_prompt)
    
    # Format preferences (use new format if user/household provided, otherwise fallback to old format)
    if user_preferences is not None or household_preferences is not None:
        prefs_text = format_preferences(
            user_preferences=user_preferences,
            household_preferences=household_preferences,
        )
        if prefs_text != "No preferences stored.":
            system_parts.append("\n" + prefs_text)
    elif preferences:
        # Fallback to old format for backwards compatibility
        system_parts.append("\n" + format_preferences(household_preferences=preferences))
    
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


def build_structured_tool_messages(
    user_message: str,
    tools: List[Dict[str, Any]],
    conversation_history: List[Dict[str, str]] = None,
) -> List[Dict[str, str]]:
    """Build messages for structured JSON tool selection."""
    messages = [{"role": "system", "content": get_structured_tool_prompt(tools)}]
    if conversation_history:
        messages.extend(conversation_history[-6:])
    messages.append({"role": "user", "content": user_message})
    return messages


def build_tool_result_messages(
    user_message: str,
    tool_name: str,
    tool_result: Dict[str, Any],
    context_snapshots: List[Dict[str, Any]] = None,
    user_preferences: Dict[str, Any] = None,
    household_preferences: Dict[str, Any] = None,
    conversation_history: List[Dict[str, str]] = None,
    db: Session = None,
    household_id: int = None,
    user_id: int = None,
) -> List[Dict[str, str]]:
    """Build messages to respond after a tool has run (no tool calling)."""
    system_parts = [get_system_prompt(), get_scheduling_prompt_addition()]
    if db and household_id and user_id:
        from neuroion.core.agent.onboarding import get_onboarding_prompt_addition
        onboarding_prompt = get_onboarding_prompt_addition(db, household_id, user_id)
        if onboarding_prompt:
            system_parts.append(onboarding_prompt)
    if user_preferences is not None or household_preferences is not None:
        prefs_text = format_preferences(
            user_preferences=user_preferences,
            household_preferences=household_preferences,
        )
        if prefs_text != "No preferences stored.":
            system_parts.append("\n" + prefs_text)
    if context_snapshots:
        system_parts.append("\n" + format_context_snapshots(context_snapshots))
    system_parts.append(
        "\nTool result:\n"
        f"tool={tool_name}\n"
        f"result={json.dumps(tool_result, ensure_ascii=False, default=str)}"
    )
    messages = [{"role": "system", "content": "\n".join(system_parts)}]
    if conversation_history:
        messages.extend(conversation_history[-10:])
    messages.append({"role": "user", "content": user_message})
    return messages


def build_scheduling_intent_messages(message: str) -> List[Dict[str, str]]:
    """Build messages for LLM to classify whether the user message is about scheduling/reminders."""
    system = (
        "Determine if the user message is about scheduling, reminders, timers, alarms, or recurring/cron-like tasks. "
        "Examples: setting a reminder, 'remind me in X', 'every day at 8', planning something at a specific time, etc. "
        "Answer with ONLY a JSON object, no other text. Format: {\"scheduling_intent\": true} or {\"scheduling_intent\": false}."
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": (message or "").strip() or " "},
    ]


def build_context_extraction_messages(
    user_message: str,
    assistant_message: str,
) -> List[Dict[str, str]]:
    """Build messages for context extraction."""
    system_prompt = (
        "Extract durable user or household context from the conversation. "
        "Only capture information that is likely to be useful later (preferences, routines, constraints, "
        "important facts). If nothing useful, return type=none.\n\n"
        "Respond with exactly one JSON object and no other text.\n"
        "Allowed forms:\n"
        "1) {\"type\":\"context\",\"event_type\":\"note\",\"summary\":\"...\",\"metadata\":{...},\"scope\":\"user\"}\n"
        "2) {\"type\":\"none\"}\n\n"
        "Guidelines:\n"
        "- summary must be concise, factual, and standalone (1 sentence).\n"
        "- scope: \"user\" or \"household\" (default user).\n"
        "- event_type: short label like preference, schedule, home, health, location, note.\n"
        "- metadata is optional and should be small.\n"
        "- Do NOT include onboarding questions or meta commentary.\n\n"
        "Conversation:\n"
        f"User: {user_message}\n"
        f"Assistant: {assistant_message}"
    )
    return [{"role": "system", "content": system_prompt}]


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
