"""
Tracing for the agentic loop: one trace per run, steps as spans.
Logs tool name, sanitized args, result summary, latency, optional token count.
"""
import json
import logging
import time
import uuid
from contextlib import contextmanager
from typing import Any, Dict, Optional

logger = logging.getLogger("neuroion.agent.tracing")


def _sanitize(args: Optional[Dict[str, Any]], max_len: int = 200) -> Dict[str, Any]:
    """Redact or truncate args for safe logging."""
    if not args:
        return {}
    out = {}
    for k, v in args.items():
        if k.lower() in ("password", "secret", "token", "key", "api_key"):
            out[k] = "[REDACTED]"
        else:
            s = json.dumps(v, default=str) if not isinstance(v, str) else v
            out[k] = s[:max_len] + "..." if len(s) > max_len else s
    return out


class AgentTracer:
    """Per-run trace with step spans."""

    def __init__(self) -> None:
        self._run_id: Optional[str] = None
        self._step_id: Optional[str] = None
        self._run_start: Optional[float] = None
        self._spans: list = []

    def start_run(self) -> str:
        self._run_id = str(uuid.uuid4())[:8]
        self._run_start = time.perf_counter()
        self._spans = []
        logger.info("agent_run_start run_id=%s", self._run_id)
        return self._run_id

    def end_run(self, success: bool, error: Optional[str] = None) -> None:
        duration_ms = (time.perf_counter() - (self._run_start or 0)) * 1000
        logger.info(
            "agent_run_end run_id=%s success=%s duration_ms=%.2f error=%s spans=%d",
            self._run_id,
            success,
            duration_ms,
            error or "",
            len(self._spans),
        )
        self._run_id = None
        self._run_start = None

    @contextmanager
    def span_step(
        self,
        name: str,
        tool_name: Optional[str] = None,
        args: Optional[Dict[str, Any]] = None,
    ):
        """Context manager for one step (e.g. planner.next or executor.run)."""
        step_id = str(uuid.uuid4())[:8]
        self._step_id = step_id
        start = time.perf_counter()
        safe_args = _sanitize(args)
        logger.debug(
            "agent_span_start run_id=%s step_id=%s name=%s tool=%s args=%s",
            self._run_id,
            step_id,
            name,
            tool_name or "",
            safe_args,
        )
        try:
            yield {"step_id": step_id, "run_id": self._run_id}
        finally:
            latency_ms = (time.perf_counter() - start) * 1000
            self._spans.append({"step_id": step_id, "name": name, "tool": tool_name, "latency_ms": latency_ms})
            logger.debug(
                "agent_span_end run_id=%s step_id=%s name=%s latency_ms=%.2f",
                self._run_id,
                step_id,
                name,
                latency_ms,
            )
            self._step_id = None

    @property
    def run_id(self) -> Optional[str]:
        return self._run_id


_tracer = AgentTracer()


def get_tracer() -> AgentTracer:
    return _tracer


def start_run() -> str:
    return _tracer.start_run()


def end_run(success: bool, error: Optional[str] = None) -> None:
    _tracer.end_run(success, error)


@contextmanager
def span_step(name: str, tool_name: Optional[str] = None, args: Optional[Dict[str, Any]] = None):
    with _tracer.span_step(name, tool_name=tool_name, args=args) as ctx:
        yield ctx
