"""
Task session management and state machine for task-capable agent.

States: IDLE -> NEEDS_INFO -> READY_TO_EXECUTE -> EXECUTING -> DONE | FAILED
Persistence: JSON files under ~/.neuroion/tasks/ (or TASK_DATA_DIR).
"""
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from neuroion.core.config import settings

# State constants
IDLE = "IDLE"
NEEDS_INFO = "NEEDS_INFO"
READY_TO_EXECUTE = "READY_TO_EXECUTE"
EXECUTING = "EXECUTING"
DONE = "DONE"
FAILED = "FAILED"
PENDING_CONFIRM = "PENDING_CONFIRM"

MAX_TURNS = 4
MAX_TOOL_ATTEMPTS = 2


def _tasks_dir() -> Path:
    base = os.environ.get("TASK_DATA_DIR")
    if base:
        return Path(base)
    return Path(settings.database_path).parent / "tasks"


def _task_path(task_id: str) -> Path:
    _tasks_dir().mkdir(parents=True, exist_ok=True)
    return _tasks_dir() / f"{task_id}.json"


def _chat_tasks_dir(chat_id: str) -> Path:
    """Directory for tasks by chat_id (optional: list active task ids)."""
    d = _tasks_dir() / "by_chat"
    d.mkdir(parents=True, exist_ok=True)
    return d


def create_task(chat_id: str, initial_state: str = NEEDS_INFO) -> Dict[str, Any]:
    """Create a new task session. chat_id is user_id or composite id."""
    task_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    task = {
        "task_id": task_id,
        "chat_id": str(chat_id),
        "state": initial_state,
        "turn_count": 0,
        "tool_attempt_count": 0,
        "created_at": now,
        "last_message_at": now,
        "pending_confirm": None,
        "meta": {},
        "last_assistant_output": None,
    }
    path = _task_path(task_id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(task, f, indent=2, ensure_ascii=False)
    return task


def load_task(task_id: str) -> Optional[Dict[str, Any]]:
    """Load task by id. Returns None if not found or invalid."""
    path = _task_path(task_id)
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, TypeError):
        return None


def save_task(task: Dict[str, Any]) -> None:
    """Persist task."""
    task_id = task.get("task_id")
    if not task_id:
        return
    path = _task_path(task_id)
    task["last_message_at"] = datetime.now(timezone.utc).isoformat()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(task, f, indent=2, ensure_ascii=False)


def _active_task_path(chat_id: str) -> Path:
    return _tasks_dir() / "by_chat" / f"{chat_id}.json"


def get_active_task_id(chat_id: str) -> Optional[str]:
    """Return active (non-terminal) task_id for chat_id if any."""
    path = _active_task_path(chat_id)
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        tid = data.get("task_id")
        if not tid:
            return None
        task = load_task(tid)
        if task and not is_terminal(task):
            return tid
    except (json.JSONDecodeError, TypeError):
        pass
    return None


def set_active_task_id(chat_id: str, task_id: str) -> None:
    """Record active task_id for chat_id."""
    _active_task_path(chat_id).parent.mkdir(parents=True, exist_ok=True)
    path = _active_task_path(chat_id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"task_id": task_id, "chat_id": chat_id}, f)


def clear_active_task_id(chat_id: str) -> None:
    """Clear active task for chat_id (e.g. when task DONE/FAILED)."""
    path = _active_task_path(chat_id)
    if path.exists():
        try:
            path.unlink()
        except OSError:
            pass


def get_or_create_task(
    chat_id: str,
    message: str,
    task_id_from_request: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get existing task by task_id_from_request, or by active task for chat_id, if still open;
    otherwise create a new task. Chat_id is used as session key.
    """
    tid = task_id_from_request or get_active_task_id(str(chat_id))
    if tid:
        task = load_task(tid)
        if task and task.get("chat_id") == str(chat_id) and not is_terminal(task):
            return task
    task = create_task(str(chat_id), initial_state=NEEDS_INFO)
    set_active_task_id(str(chat_id), task["task_id"])
    return task


def transition(
    task: Dict[str, Any],
    new_state: str,
    *,
    increment_turn: bool = False,
    increment_tool_attempt: bool = False,
    last_assistant_output: Optional[str] = None,
    pending_confirm: Optional[Dict] = None,
) -> Dict[str, Any]:
    """Update task state and optional counters. Saves to disk."""
    task["state"] = new_state
    if increment_turn:
        task["turn_count"] = task.get("turn_count", 0) + 1
    if increment_tool_attempt:
        task["tool_attempt_count"] = task.get("tool_attempt_count", 0) + 1
    if last_assistant_output is not None:
        task["last_assistant_output"] = last_assistant_output
    if pending_confirm is not None:
        task["pending_confirm"] = pending_confirm
    save_task(task)
    return task


def can_make_turn(task: Dict[str, Any]) -> bool:
    """True if turn_count < MAX_TURNS."""
    return (task.get("turn_count") or 0) < MAX_TURNS


def can_execute_tool(task: Dict[str, Any]) -> bool:
    """True if tool_attempt_count < MAX_TOOL_ATTEMPTS."""
    return (task.get("tool_attempt_count") or 0) < MAX_TOOL_ATTEMPTS


def is_terminal(task: Dict[str, Any]) -> bool:
    """True if state is DONE or FAILED."""
    return task.get("state") in (DONE, FAILED)
