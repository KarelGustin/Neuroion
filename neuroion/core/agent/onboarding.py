"""
Onboarding flow management for new users.

Handles the kennismaking conversation after pairing.
"""
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from neuroion.core.memory.repository import PreferenceRepository


# Onboarding questions in order
ONBOARDING_QUESTIONS = [
    {
        "key": "first_name",
        "question": "Hello! I'm ion, your personal assistant. What's your first name?",
        "category": "personal",
    },
    {
        "key": "communication_style",
        "question": "What's your preferred way for me to address you? (e.g., formal/informal tone)",
        "category": "personal",
    },
    {
        "key": "interests",
        "question": "What are your main interests or hobbies?",
        "category": "personal",
    },
    {
        "key": "daily_schedule",
        "question": "What's your typical daily routine? (when do you wake up, work, etc.)",
        "category": "personal",
    },
    {
        "key": "communication_preferences",
        "question": "Do you have any communication preferences? (short/long, technical/simple)",
        "category": "personal",
    },
    {
        "key": "assistance_preferences",
        "question": "What do you think I can help you with? (planning, information, automation, etc.)",
        "category": "personal",
    },
    {
        "key": "household_context",
        "question": "Do you live alone or with others? (for household context)",
        "category": "personal",
    },
    {
        "key": "home_context",
        "question": "Are there specific things I should know about your home or environment?",
        "category": "personal",
    },
    {
        "key": "notification_preferences",
        "question": "Do you have preferences for notifications or reminders?",
        "category": "personal",
    },
    {
        "key": "additional_info",
        "question": "Is there anything special I should know about you to help you better?",
        "category": "personal",
    },
]


def get_onboarding_question_index(db: Session, household_id: int, user_id: int) -> int:
    """
    Get the current onboarding question index for a user.
    
    Returns:
        Index of current question (0-based), or -1 if completed
    """
    onboarding_state = PreferenceRepository.get(
        db, household_id, "onboarding_question_index", user_id=user_id
    )
    
    if onboarding_state:
        try:
            index = int(onboarding_state.value) if isinstance(onboarding_state.value, (int, str)) else -1
            # Check if all questions are completed
            if index >= len(ONBOARDING_QUESTIONS):
                return -1  # Completed
            return index
        except (ValueError, TypeError):
            return 0  # Start from beginning
    
    return 0  # Not started


def is_onboarding_completed(db: Session, household_id: int, user_id: int) -> bool:
    """Check if user has completed onboarding."""
    completed = PreferenceRepository.get(
        db, household_id, "onboarding_completed", user_id=user_id
    )
    if completed:
        return bool(completed.value) if isinstance(completed.value, bool) else str(completed.value).lower() == "true"
    return False


def get_current_onboarding_question(db: Session, household_id: int, user_id: int) -> Optional[Dict[str, Any]]:
    """
    Get the current onboarding question for a user.
    
    Returns:
        Question dict or None if completed
    """
    if is_onboarding_completed(db, household_id, user_id):
        return None
    
    index = get_onboarding_question_index(db, household_id, user_id)
    if index < 0 or index >= len(ONBOARDING_QUESTIONS):
        return None
    
    # Initialize question index if not set (first time)
    if index == 0:
        onboarding_state = PreferenceRepository.get(
            db, household_id, "onboarding_question_index", user_id=user_id
        )
        if not onboarding_state:
            # Initialize to 0
            PreferenceRepository.set(
                db=db,
                household_id=household_id,
                key="onboarding_question_index",
                value=0,
                user_id=user_id,
                category="onboarding",
            )
    
    return ONBOARDING_QUESTIONS[index]


def save_onboarding_answer(
    db: Session,
    household_id: int,
    user_id: int,
    question_key: str,
    answer: str,
    category: str = "personal",
) -> None:
    """Save an onboarding answer as a user preference."""
    PreferenceRepository.set(
        db=db,
        household_id=household_id,
        key=question_key,
        value=answer,
        user_id=user_id,
        category=category,
    )


def advance_onboarding(db: Session, household_id: int, user_id: int) -> Optional[Dict[str, Any]]:
    """
    Advance to the next onboarding question.
    
    Returns:
        Next question dict, or None if completed
    """
    current_index = get_onboarding_question_index(db, household_id, user_id)
    
    if current_index < 0:
        return None  # Already completed
    
    next_index = current_index + 1
    
    if next_index >= len(ONBOARDING_QUESTIONS):
        # Mark as completed
        PreferenceRepository.set(
            db=db,
            household_id=household_id,
            key="onboarding_completed",
            value=True,
            user_id=user_id,
            category="onboarding",
        )
        return None
    
    # Update question index
    PreferenceRepository.set(
        db=db,
        household_id=household_id,
        key="onboarding_question_index",
        value=next_index,
        user_id=user_id,
        category="onboarding",
    )
    
    return ONBOARDING_QUESTIONS[next_index]


def get_onboarding_prompt_addition(db: Session, household_id: int, user_id: int) -> str:
    """
    Get additional prompt instructions when user is in onboarding mode.
    
    Returns:
        Additional prompt text for onboarding context
    """
    if is_onboarding_completed(db, household_id, user_id):
        return ""
    
    current_question = get_current_onboarding_question(db, household_id, user_id)
    if not current_question:
        return ""
    
    return f"""
ONBOARDING MODE: You are currently in an onboarding conversation with this user.
You are asking personal questions to get to know them better.

STRICT ONBOARDING GUIDELINES:
- You MUST use the EXACT question provided below - do not rephrase or create your own questions
- The user's message is their answer to the current question
- NEVER repeat what the user said - acknowledge briefly without echoing their words
- Always identify as "ion" - never use any other name
- Keep responses short and conversational (1-2 sentences max for acknowledgment)
- Do not provide long explanations or try to help with other things yet
- Focus only on the onboarding conversation

Current question to ask (use EXACTLY as written): "{current_question['question']}"
Question key: {current_question['key']}

RESPONSE FORMAT:
1. Brief warm acknowledgment (1 sentence, do NOT repeat their answer)
2. Ask the next question exactly as provided (it will be given to you after you respond)

After all questions are answered, you will be notified and can then help with anything they need.
"""
