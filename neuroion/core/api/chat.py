"""
Chat endpoint for agent interactions.

Routes user messages through the agent system and returns structured responses.
Supports streaming via Server-Sent Events (SSE) for real-time progress.
"""
import asyncio
import json
import queue
import threading
from datetime import timedelta
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from neuroion.core.memory.db import get_db, db_session
from neuroion.core.security.permissions import get_current_user
from neuroion.core.agent.agent import Agent, compact_and_save_session
from neuroion.core.memory.repository import ChatMessageRepository
from neuroion.core.services.request_counter import RequestCounter

# Inactivity gap (minutes) after which a new session starts; previous session is then compacted.
SESSION_INACTIVITY_MINUTES = 15

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


# Stream route must be registered before "" so POST /chat/stream is matched
@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    http_request: Request,
    user: dict = Depends(get_current_user),
):
    """
    Send a message to the agent and stream progress via Server-Sent Events.

    Events: status (text), tool_start (tool), tool_done (tool), done (message, actions).
    Keeps the connection alive so long requests (e.g. market research) complete.
    Uses db_session() per thread so the request session is never used from another thread.
    """
    agent = get_agent()
    household_id = user["household_id"]
    user_id = user["user_id"]

    # All request-thread DB work in one session (avoids wrong-thread use)
    with db_session() as db:
        RequestCounter.increment(db, household_id)
        recent = ChatMessageRepository.get_recent(db, household_id, limit=1, user_id=user_id)
        last_msg = recent[0] if recent else None
        new_user_message = ChatMessageRepository.create(
            db=db,
            household_id=household_id,
            user_id=user_id,
            role="user",
            content=request.message,
        )
        if last_msg and new_user_message.created_at and last_msg.created_at:
            gap = new_user_message.created_at - last_msg.created_at
            if gap >= timedelta(minutes=SESSION_INACTIVITY_MINUTES):
                previous_session = ChatMessageRepository.get_previous_session_messages(
                    db=db,
                    household_id=household_id,
                    user_id=user_id,
                    before_created_at=new_user_message.created_at,
                    inactivity_minutes=SESSION_INACTIVITY_MINUTES,
                )
                if previous_session:
                    try:
                        compact_and_save_session(
                            db=db,
                            household_id=household_id,
                            user_id=user_id,
                            messages=previous_session,
                        )
                    except Exception:
                        pass
        conversation_history = ChatMessageRepository.get_messages_for_current_session(
            db=db,
            household_id=household_id,
            user_id=user_id,
            before_or_at=None,
            inactivity_minutes=SESSION_INACTIVITY_MINUTES,
        )

    force_task_mode = (http_request.headers.get("X-Agent-Task-Mode") or "").strip() == "1"
    sync_queue: queue.Queue = queue.Queue()

    def run_agent_in_thread() -> None:
        with db_session() as thread_db:
            try:
                result = agent.process_message(
                    db=thread_db,
                    household_id=household_id,
                    user_id=user_id,
                    message=request.message,
                    conversation_history=conversation_history,
                    force_task_mode=force_task_mode,
                    progress_callback=lambda ev: sync_queue.put(ev),
                )
                sync_queue.put({
                    "type": "done",
                    "message": result.get("message", ""),
                    "actions": result.get("actions", []),
                })
            except Exception as e:
                sync_queue.put({
                    "type": "done",
                    "message": "",
                    "actions": [],
                    "error": str(e),
                })

    thread = threading.Thread(target=run_agent_in_thread)
    thread.start()

    async def event_stream():
        loop = asyncio.get_event_loop()
        while True:
            ev = await loop.run_in_executor(None, sync_queue.get)
            if ev.get("type") == "done":
                if not ev.get("error"):
                    # Save in a session created in this (executor) thread
                    with db_session() as save_db:
                        ChatMessageRepository.create(
                            db=save_db,
                            household_id=household_id,
                            user_id=user_id,
                            role="assistant",
                            content=ev.get("message", ""),
                            metadata={"actions": ev.get("actions", [])} if ev.get("actions") else None,
                        )
                yield f"data: {json.dumps(ev)}\n\n"
                break
            yield f"data: {json.dumps(ev)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


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

    # Last message before this one (to detect session boundary)
    recent = ChatMessageRepository.get_recent(db, household_id, limit=1, user_id=user_id)
    last_msg = recent[0] if recent else None

    # Save user message (server is source of truth)
    new_user_message = ChatMessageRepository.create(
        db=db,
        household_id=household_id,
        user_id=user_id,
        role="user",
        content=request.message,
    )

    # If there was a gap >= SESSION_INACTIVITY_MINUTES, compact the previous session
    if last_msg and new_user_message.created_at and last_msg.created_at:
        gap = new_user_message.created_at - last_msg.created_at
        if gap >= timedelta(minutes=SESSION_INACTIVITY_MINUTES):
            previous_session = ChatMessageRepository.get_previous_session_messages(
                db=db,
                household_id=household_id,
                user_id=user_id,
                before_created_at=new_user_message.created_at,
                inactivity_minutes=SESSION_INACTIVITY_MINUTES,
            )
            if previous_session:
                try:
                    compact_and_save_session(
                        db=db,
                        household_id=household_id,
                        user_id=user_id,
                        messages=previous_session,
                    )
                except Exception:
                    pass  # Don't fail the request if compaction fails

    # Current session = all messages in the active window (including the one we just saved)
    conversation_history = ChatMessageRepository.get_messages_for_current_session(
        db=db,
        household_id=household_id,
        user_id=user_id,
        before_or_at=None,
        inactivity_minutes=SESSION_INACTIVITY_MINUTES,
    )

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
