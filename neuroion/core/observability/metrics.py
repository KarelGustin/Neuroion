"""
Simple in-memory metrics for the agentic loop: success/fail per run, per tool; tool error rate.
"""
import logging
from typing import Dict, Optional

logger = logging.getLogger("neuroion.agent.metrics")


class AgentMetrics:
    """In-memory counters for agent runs and tool calls."""

    def __init__(self) -> None:
        self._runs_total = 0
        self._runs_success = 0
        self._runs_failed = 0
        self._tool_calls_total: Dict[str, int] = {}
        self._tool_errors_total: Dict[str, int] = {}

    def record_run_result(self, success: bool) -> None:
        self._runs_total += 1
        if success:
            self._runs_success += 1
        else:
            self._runs_failed += 1

    def record_tool_call(self, tool_name: str, success: bool) -> None:
        self._tool_calls_total[tool_name] = self._tool_calls_total.get(tool_name, 0) + 1
        if not success:
            self._tool_errors_total[tool_name] = self._tool_errors_total.get(tool_name, 0) + 1

    def get_run_stats(self) -> Dict[str, int]:
        return {
            "runs_total": self._runs_total,
            "runs_success": self._runs_success,
            "runs_failed": self._runs_failed,
        }

    def get_tool_stats(self) -> Dict[str, Dict[str, int]]:
        return {
            "calls": dict(self._tool_calls_total),
            "errors": dict(self._tool_errors_total),
        }

    def get_success_rate(self) -> Optional[float]:
        if self._runs_total == 0:
            return None
        return self._runs_success / self._runs_total


_metrics = AgentMetrics()


def get_metrics() -> AgentMetrics:
    return _metrics


def record_run_result(success: bool) -> None:
    _metrics.record_run_result(success)


def record_tool_call(tool_name: str, success: bool) -> None:
    _metrics.record_tool_call(tool_name, success)
