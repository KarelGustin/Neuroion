"""
Chat endpoint for agent interactions.

Routes user messages through the agent system and returns structured responses.
"""
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any

from neuroion.core.memory.db import get_db
from neuroion.core.security.permissions import get_current_user
from neuroion.core.agent.agent import Agent
from neuroion.core.memory.repository import ChatMessageRepository
from neuroion.core.services.request_counter import RequestCounter

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    """Chat message request."""
    message: str
    conversation_history: Optional[List[Dict[str, str]]] = None


class ActionResponse(BaseModel):
    """Action proposal response."""
    id: Optional[int]
    name: str
    description: str
    parameters: Dict[str, Any]
    reasoning: str


class ChatResponse(BaseModel):
    """Chat response with message, reasoning, and actions."""
    message: str
    reasoning: str
    actions: List[ActionResponse]


class ActionExecuteRequest(BaseModel):
    """Request to execute a confirmed action."""
    action_id: int


class ActionExecuteResponse(BaseModel):
    """Response from action execution."""
    success: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# Global agent instance
_agent: Optional[Agent] = None


def get_agent() -> Agent:
    """Get or create the global agent instance."""
    global _agent
    if _agent is None:
        _agent = Agent()
    return _agent


@router.post("", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    http_request: Request,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> ChatResponse:
    """
    Send a message to the agent.
    
    Returns structured response with message, reasoning, and proposed actions.
    Actions require explicit confirmation before execution.
    
    Automatically fetches conversation history if not provided and saves messages.
    """
    agent = get_agent()
    household_id = user["household_id"]
    user_id = user["user_id"]
    
    # #region agent log
    try:
        import json as _json, time as _time
        with open('/Users/karelgustin/Neuroion/Neuroion/.cursor/debug.log', 'a') as _f:
            _f.write(_json.dumps({
                "sessionId": "debug-session",
                "runId": "run1",
                "hypothesisId": "H1",
                "location": "chat.py:84",
                "message": "chat entry",
                "data": {"household_id": household_id, "user_id": user_id},
                "timestamp": int(_time.time() * 1000),
            }) + "\n")
    except Exception:
        pass
    # #endregion
    
    # Increment daily request counter
    RequestCounter.increment(db, household_id)
    
    # Get conversation history if not provided
    conversation_history = request.conversation_history
    if conversation_history is None:
        conversation_history = ChatMessageRepository.get_conversation_history(
            db=db,
            household_id=household_id,
            user_id=user_id,
            limit=20,
        )
    
    # Save user message
    ChatMessageRepository.create(
        db=db,
        household_id=household_id,
        user_id=user_id,
        role="user",
        content=request.message,
    )
    
    # Always use Python agent for user-scoped chat so user_id is enforced (conversation history,
    # context and preferences stay strictly per user; neuroion_adapter does not receive user_id).
    force_task_mode = (http_request.headers.get("X-Agent-Task-Mode") or "").strip() == "1"
    response = agent.process_message(
            db=db,
            household_id=household_id,
            user_id=user_id,
            message=request.message,
            conversation_history=conversation_history,
            force_task_mode=force_task_mode,
        )

    # Save assistant response
    assistant_message = response.get("message", "")
    ChatMessageRepository.create(
        db=db,
        household_id=household_id,
        user_id=user_id,
        role="assistant",
        content=assistant_message,
        metadata={
            "reasoning": response.get("reasoning", ""),
            "actions": response.get("actions", []),
        } if response.get("actions") else None,
    )
    
    # Convert actions to response format
    actions = [
        ActionResponse(
            id=action.get("id"),
            name=action.get("name", ""),
            description=action.get("description", ""),
            parameters=action.get("parameters", {}),
            reasoning=action.get("reasoning", ""),
        )
        for action in response.get("actions", [])
    ]
    
    return ChatResponse(
        message=assistant_message,
        reasoning=response.get("reasoning", ""),
        actions=actions,
    )


@router.post("/actions/execute", response_model=ActionExecuteResponse)
def execute_action(
    request: ActionExecuteRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> ActionExecuteResponse:
    """
    Execute a confirmed action.
    
    Requires the action to have been proposed via /chat and confirmed by the user.
    """
    agent = get_agent()
    
    result = agent.execute_action(
        db=db,
        household_id=user["household_id"],
        user_id=user["user_id"],
        action_id=request.action_id,
    )
    
    return ActionExecuteResponse(
        success=result.get("success", False),
        result=result.get("result"),
        error=result.get("error"),
    )
