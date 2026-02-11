"""
10 behavior prompts: NL user message -> expected JSON type and key payload.
Used by test_behavior_prompts to assert protocol accepts expected JSON shapes.
"""
BEHAVIOR_CASES = [
    {
        "id": 1,
        "user_nl": "Herinner me over 20 minuten",
        "expected_type": "tool_call",
        "expected_tool": "cron.add",
        "expected_args_keys": ["schedule", "sessionTarget", "payload"],
        "schedule_kind": "every",
        "everyMs_min": 60000,
    },
    {
        "id": 2,
        "user_nl": "Elke dag om 8 uur",
        "expected_type": "tool_call",
        "expected_tool": "cron.add",
        "expected_args_keys": ["schedule", "sessionTarget", "payload"],
        "schedule_kind": "cron",
    },
    {
        "id": 3,
        "user_nl": "Zet een wekker voor 07:00 morgen",
        "expected_type": "tool_call",
        "expected_tool": "cron.add",
        "expected_args_keys": ["schedule", "sessionTarget", "payload"],
        "schedule_kind": "at",
    },
    {
        "id": 4,
        "user_nl": "Toon mijn geplande taken",
        "expected_type": "tool_call",
        "expected_tool": "cron.list",
        "expected_args_keys": [],
    },
    {
        "id": 5,
        "user_nl": "Verwijder herinnering job xyz",
        "expected_type": "tool_call",
        "expected_tool": "cron.remove",
        "expected_args_keys": ["jobId"],
    },
    {
        "id": 6,
        "user_nl": "Voer job abc nu uit",
        "expected_type": "tool_call",
        "expected_tool": "cron.run",
        "expected_args_keys": ["jobId"],
    },
    {
        "id": 7,
        "user_nl": "Wanneer is job xyz laatst gedraaid?",
        "expected_type": "tool_call",
        "expected_tool": "cron.runs",
        "expected_args_keys": ["jobId"],
    },
    {
        "id": 8,
        "user_nl": "Wijzig job abc naar elke 2 uur",
        "expected_type": "tool_call",
        "expected_tool": "cron.update",
        "expected_args_keys": ["jobId"],
    },
    {
        "id": 9,
        "user_nl": "Wat is het weer?",
        "expected_type": "final",
        "expected_tool": None,
    },
    {
        "id": 10,
        "user_nl": "Herinner me om 15:00 vandaag",
        "expected_type": "tool_call",
        "expected_tool": "cron.add",
        "expected_args_keys": ["schedule", "sessionTarget", "payload"],
        "schedule_kind": "at",
    },
]
