"""
One iteration of the agentic heartbeat: Plan -> Act -> Validate.
Caller does Observe (gather state) and Commit (task/memory/trace).
"""
from typing import Optional, Tuple

from neuroion.core.agent.types import Action, Observation, RunContext, RunState
from neuroion.core.agent.planner import Planner
from neuroion.core.agent.executor import Executor
from neuroion.core.agent.policies.validator import Validator, ValidationResult
from neuroion.core.observability.tracing import get_tracer, span_step
from neuroion.core.observability.metrics import get_metrics, record_tool_call


def run_one_turn(
    state: RunState,
    context: RunContext,
    planner: Planner,
    executor: Executor,
    validator: Validator,
) -> Tuple[Action, Observation, ValidationResult]:
    """
    Run one Observe -> Plan -> Act -> Validate. Caller does Observe (build state)
    and Commit (task transition, memory, trace).
    Returns (action, observation, validation). Caller commits and may loop or stop.
    """
    with span_step("plan", args={"message_len": len(state.message)}):
        action = planner.next(state)

    with span_step("act", tool_name=action.tool if action.type == "tool_call" else None, args=action.args if action.type == "tool_call" else None):
        observation = executor.run(action, context)

    if action.type == "tool_call":
        get_metrics().record_tool_call(action.tool, observation.success)

    validation = validator.check(state, observation)
    return action, observation, validation
