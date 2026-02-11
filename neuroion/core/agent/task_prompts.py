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

Examples:
- User: "Herinner me over 20 minuten" -> {"type":"tool_call","tool":"cron.add","args":{"schedule":{"kind":"every","everyMs":1200000},"sessionTarget":"isolated","payload":{"kind":"agentTurn","message":"Herinnering: over 20 minuten"}}}
- User: "Wat is het weer?" -> {"type":"final","message":"Ik heb geen weerinformatie; ik kan wel herinneringen en taken plannen."}
- User: "Elke dag om 8" -> {"type":"tool_call","tool":"cron.add","args":{"schedule":{"kind":"cron","expr":"0 8 * * *","tz":"Europe/Amsterdam"},"sessionTarget":"isolated","payload":{"kind":"agentTurn","message":"Dagelijkse herinnering 08:00"}}}"""


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
