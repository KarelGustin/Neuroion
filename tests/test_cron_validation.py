"""
Unit tests for cron validation rules.
"""
import pytest
from neuroion.core.cron.validation import (
    CronValidationError,
    validate_session_target_and_payload,
    validate_every_ms,
    validate_at_timezone,
    validate_cron_expression,
    validate_jobs_per_user_per_day,
)


def test_main_requires_system_event():
    validate_session_target_and_payload("main", {"kind": "systemEvent", "text": "hello"})
    with pytest.raises(CronValidationError, match="systemEvent"):
        validate_session_target_and_payload("main", {"kind": "agentTurn", "message": "x"})


def test_isolated_requires_agent_turn():
    validate_session_target_and_payload("isolated", {"kind": "agentTurn", "message": "hi"})
    with pytest.raises(CronValidationError, match="agentTurn"):
        validate_session_target_and_payload("isolated", {"kind": "systemEvent", "text": "x"})


def test_delivery_only_for_isolated():
    validate_session_target_and_payload("isolated", {"kind": "agentTurn", "message": "m", "delivery": {"x": 1}})
    with pytest.raises(CronValidationError, match="delivery"):
        validate_session_target_and_payload("main", {"kind": "systemEvent", "text": "t", "delivery": {}})


def test_every_ms_minimum():
    validate_every_ms(60000)
    validate_every_ms(120000)
    with pytest.raises(CronValidationError, match="60000"):
        validate_every_ms(59999)
    with pytest.raises(CronValidationError, match="60000"):
        validate_every_ms(0)


def test_at_requires_timezone():
    validate_at_timezone("2025-02-11T10:00:00+01:00")
    validate_at_timezone("2025-02-11T10:00:00Z")
    validate_at_timezone("2025-02-11T10:00:00+02:00")
    with pytest.raises(CronValidationError, match="timezone"):
        validate_at_timezone("2025-02-11T10:00:00")
    with pytest.raises(CronValidationError, match="timezone"):
        validate_at_timezone("2025-02-11 10:00:00")


def test_cron_every_minute_rejected_by_default():
    validate_cron_expression("5 * * * *")  # every hour at :05
    validate_cron_expression("0 8 * * *")  # daily 8am
    with pytest.raises(CronValidationError, match="every minute"):
        validate_cron_expression("* * * * *")
    with pytest.raises(CronValidationError, match="every minute"):
        validate_cron_expression("* * * * *", allow_every_minute=False)


def test_cron_every_minute_allowed_with_flag():
    validate_cron_expression("* * * * *", allow_every_minute=True)


def test_cron_every_minute_allowed_with_allowlist():
    validate_cron_expression("* * * * *", allowlist_expressions=["* * * * *"])


def test_cron_five_fields_required():
    with pytest.raises(CronValidationError, match="5-field"):
        validate_cron_expression("1 2 3")
    with pytest.raises(CronValidationError, match="5-field"):
        validate_cron_expression("1 2 3 4 5 6")


def test_jobs_per_user_per_day_limit():
    validate_jobs_per_user_per_day(0, 20)
    validate_jobs_per_user_per_day(19, 20)
    with pytest.raises(CronValidationError, match="max"):
        validate_jobs_per_user_per_day(20, 20)
    with pytest.raises(CronValidationError, match="max"):
        validate_jobs_per_user_per_day(21, 20)
