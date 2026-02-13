"""
Task-mode system prompt: LLM must output only valid JSON (tool_call | need_info | final).
Use Europe/Amsterdam as default timezone for cron.
"""
from typing import Any, Dict, List, Optional


def get_task_system_prompt() -> str:
    """Short system prompt for structured task output. No extra text allowed."""
    return """You must respond with exactly one JSON object. No other text, no markdown, no explanation outside the JSON.

Allowed forms only:
1) {"type":"tool_call","tool":"<name>","args":{...}}
   Tools: cron.add, cron.update, cron.remove, cron.list, cron.run, cron.runs.
   For cron.add/update: schedule (at|every|cron), sessionTarget (main|isolated), payload (main: kind=systemEvent+text; isolated: kind=agentTurn+message). Default timezone Europe/Amsterdam. everyMs in ms, min 60000.
2) {"type":"need_info","questions":["question1","question2"]}
   Use only when you need a missing detail (e.g. exact time, jobId).
3) {"type":"final","message":"<reply to user>"}
   Use when no tool is needed (e.g. general question) or after you have enough info to answer.

CRON.ADD – always confirm first:
- Never call cron.add in your first response when the user asks for a new reminder or schedule.
- First respond with type "final": describe in plain language what you will schedule (when, what message/action, one-off or recurring) and end with a clear confirmation question (e.g. "Zal ik dit zo inplannen?" or "Wil je dat ik dit plan?").
- Only when the user's next message clearly confirms (ja, ja graag, doe maar, oké, bevestig, yes, sure, etc.) and the previous assistant message was your cron proposal, then respond with tool_call cron.add using the same schedule and payload you described.

CRON.REMOVE / stopping jobs:
- When the user asks to cancel, stop, or remove a reminder/scheduled job: use cron.list first to get the list of jobs and their jobIds, then use cron.remove(jobId) for the one they mean. If multiple jobs match, use need_info to ask which one.

Examples:
- User: "Herinner me over 20 minuten" -> {"type":"final","message":"Ik plan een herinnering over 20 minuten. Je krijgt dan het bericht: 'Herinnering: over 20 minuten'. Zal ik dit zo inplannen?"}
- User: "ja" (after above) -> {"type":"tool_call","tool":"cron.add","args":{"schedule":{"kind":"every","everyMs":1200000},"sessionTarget":"isolated","payload":{"kind":"agentTurn","message":"Herinnering: over 20 minuten"}}}
- User: "Elke dag om 8" -> {"type":"final","message":"Ik plan een dagelijkse herinnering om 08:00 (Europe/Amsterdam). Je krijgt dan: 'Dagelijkse herinnering 08:00'. Zal ik dit inplannen?"}
- User: "Verwijder die herinnering van vanmorgen" -> first call cron.list; if one match use cron.remove with that jobId; if several use need_info.
- User: "Wat is het weer?" -> {"type":"final","message":"Ik heb geen weerinformatie; ik kan wel herinneringen en taken plannen."}"""


def build_task_messages(
    user_message: str,
    previous_exchanges: Optional[List[Dict[str, str]]] = None,
) -> List[Dict[str, str]]:
    """
    Build message list for task-mode LLM call: system + optional previous user/assistant + current user.
    Keep context small: last 1-2 exchanges only.
    """
    messages = [{"role": "system", "content": get_task_system_prompt()}]
    if previous_exchanges:
        for ex in previous_exchanges[-4:]:  # last 2 exchanges max
            role = ex.get("role", "user")
            content = ex.get("content", "")
            if role and content:
                messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_message})
    return messages
