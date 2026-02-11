"""
Output validator: check(state, output) -> Pass/Fail.
Guards against secrets in output, optional PII; used after Act, before Commit.
"""
import re
from dataclasses import dataclass
from typing import Any, Dict, Optional

from neuroion.core.agent.types import Observation, RunState


@dataclass
class ValidationResult:
    """Result of validator.check()."""
    passed: bool
    error: Optional[str] = None  # reason when passed=False


# Patterns that suggest secrets (tokens, keys, passwords)
SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|apikey)\s*[:=]\s*['\"]?[\w\-]{20,}"),
    re.compile(r"(?i)(secret|password|passwd|token)\s*[:=]\s*['\"]?[\w\-\.]{8,}"),
    re.compile(r"(?i)bearer\s+[\w\-\.]{20,}"),
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),  # OpenAI-style
]


class Validator:
    """Checks observation/output against policy (no secrets, optional PII)."""

    def __init__(self, check_secrets: bool = True, check_pii: bool = False) -> None:
        self.check_secrets = check_secrets
        self.check_pii = check_pii

    def check(self, state: RunState, observation: Observation) -> ValidationResult:
        """
        Validate observation after Act. Returns Pass/Fail.
        On fail, error message indicates why (e.g. possible secret in output).
        """
        if observation.output:
            text = _flatten_to_text(observation.output)
            if self.check_secrets and _contains_secret(text):
                return ValidationResult(passed=False, error="Output may contain secrets; blocked.")
        if observation.message:
            if self.check_secrets and _contains_secret(observation.message):
                return ValidationResult(passed=False, error="Message may contain secrets; blocked.")
        return ValidationResult(passed=True)


def _flatten_to_text(obj: Any) -> str:
    """Recursively flatten dict/list to a single string for pattern matching."""
    if isinstance(obj, str):
        return obj
    if isinstance(obj, dict):
        return " ".join(_flatten_to_text(v) for v in obj.values())
    if isinstance(obj, (list, tuple)):
        return " ".join(_flatten_to_text(x) for x in obj)
    return str(obj)


def _contains_secret(text: str) -> bool:
    for pat in SECRET_PATTERNS:
        if pat.search(text):
            return True
    return False


def check_output(state: RunState, observation: Observation) -> ValidationResult:
    """Convenience: validate using default Validator."""
    return get_validator().check(state, observation)


def get_validator() -> Validator:
    """Default validator (secrets check on)."""
    return Validator(check_secrets=True, check_pii=False)
