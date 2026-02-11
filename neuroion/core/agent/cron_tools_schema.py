"""
JSON Schema definitions for cron.* tools (OpenAI function calling format).
Used when calling LLM with tools so the agent can create/manage cron jobs.
"""
from typing import List, Dict, Any

# OpenAI tools format: list of {"type": "function", "function": {"name", "description", "parameters"}}
def get_cron_tools_for_llm() -> List[Dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": "cron.add",
                "description": "Add a new scheduled job. Do not use for greetings, 'hoe gaat het', 'how are you', or general conversation; only when the user explicitly asks for a reminder or schedule (e.g. 'herinner me over 20 min', 'elke dag om 8'). For reminders: at (one-off), every (everyMs >= 60000), or cron (5-field). Default timezone Europe/Amsterdam.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "schedule": {
                            "type": "object",
                            "description": "When to run: at (ISO8601+tz), every (everyMs >= 60000), or cron (5-field, tz)",
                            "properties": {
                                "kind": {"type": "string", "enum": ["at", "every", "cron"]},
                                "at": {"type": "string", "description": "ISO8601 with timezone (e.g. +01:00 or Z), for kind=at"},
                                "everyMs": {"type": "integer", "description": "Milliseconds between runs (min 60000), for kind=every"},
                                "expr": {"type": "string", "description": "5-field cron: min hour day month weekday, for kind=cron"},
                                "tz": {"type": "string", "description": "IANA timezone, default Europe/Amsterdam, for kind=cron"},
                            },
                            "required": ["kind"],
                        },
                        "sessionTarget": {"type": "string", "enum": ["main", "isolated"], "description": "main=systemEvent, isolated=agentTurn"},
                        "payload": {
                            "type": "object",
                            "description": "main: {kind:'systemEvent', text}; isolated: {kind:'agentTurn', message, delivery?}",
                            "properties": {
                                "kind": {"type": "string", "enum": ["systemEvent", "agentTurn"]},
                                "text": {"type": "string"},
                                "message": {"type": "string"},
                                "delivery": {"type": "object"},
                            },
                        },
                        "wakeMode": {"type": "string", "enum": ["now", "next-heartbeat"], "default": "next-heartbeat"},
                        "label": {"type": "string", "description": "Optional label for the job"},
                    },
                    "required": ["schedule", "sessionTarget", "payload"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "cron.update",
                "description": "Update an existing cron job by jobId. Do not use for greetings or general conversation; only when the user explicitly asks to change an existing reminder or schedule.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "jobId": {"type": "string"},
                        "schedule": {"type": "object"},
                        "sessionTarget": {"type": "string", "enum": ["main", "isolated"]},
                        "payload": {"type": "object"},
                        "wakeMode": {"type": "string", "enum": ["now", "next-heartbeat"]},
                        "label": {"type": "string"},
                    },
                    "required": ["jobId"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "cron.remove",
                "description": "Remove a cron job by jobId. Do not use for greetings or general conversation; only when the user explicitly asks to cancel or delete a reminder or scheduled job.",
                "parameters": {
                    "type": "object",
                    "properties": {"jobId": {"type": "string"}},
                    "required": ["jobId"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "cron.list",
                "description": "List all cron jobs for the user. Do not use for greetings or general conversation; only when the user explicitly asks to see their reminders or scheduled jobs.",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "cron.run",
                "description": "Run a cron job once immediately by jobId. Do not use for greetings or general conversation; only when the user explicitly asks to run or trigger a scheduled job now.",
                "parameters": {
                    "type": "object",
                    "properties": {"jobId": {"type": "string"}},
                    "required": ["jobId"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "cron.runs",
                "description": "Get run history for a job. Do not use for greetings or general conversation; only when the user explicitly asks for the history or log of a scheduled job. jobId and optional limit.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "jobId": {"type": "string"},
                        "limit": {"type": "integer", "description": "Max runs to return", "default": 100},
                    },
                    "required": ["jobId"],
                },
            },
        },
    ]
