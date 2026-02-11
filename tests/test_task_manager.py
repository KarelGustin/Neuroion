"""Unit tests for task_manager: state, persistence, limits."""
import tempfile
import pytest


def test_create_and_load_task(monkeypatch):
    import neuroion.core.agent.task_manager as tm
    d = tempfile.mkdtemp(prefix="neuroion_task_")
    monkeypatch.setenv("TASK_DATA_DIR", d)
    task = tm.create_task("user-1", initial_state=tm.NEEDS_INFO)
    assert task["task_id"]
    assert task["chat_id"] == "user-1"
    assert task["state"] == tm.NEEDS_INFO
    assert task["turn_count"] == 0
    loaded = tm.load_task(task["task_id"])
    assert loaded is not None
    assert loaded["task_id"] == task["task_id"]


def test_can_make_turn_and_can_execute_tool(monkeypatch):
    import neuroion.core.agent.task_manager as tm
    d = tempfile.mkdtemp(prefix="neuroion_task_")
    monkeypatch.setenv("TASK_DATA_DIR", d)
    task = tm.create_task("user-1")
    assert tm.can_make_turn(task) is True
    assert tm.can_execute_tool(task) is True
    task = tm.transition(task, tm.DONE, increment_turn=True)
    for _ in range(5):
        task = tm.transition(task, task["state"], increment_turn=True)
    assert tm.can_make_turn(task) is False


def test_is_terminal(monkeypatch):
    import neuroion.core.agent.task_manager as tm
    d = tempfile.mkdtemp(prefix="neuroion_task_")
    monkeypatch.setenv("TASK_DATA_DIR", d)
    task = tm.create_task("user-1")
    assert tm.is_terminal(task) is False
    task = tm.transition(task, tm.DONE)
    assert tm.is_terminal(task) is True
