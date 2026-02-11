# Agent

The agent turns each user message into **one** response: either a direct answer or a single follow-up after a tool call (confirmation or one clarification).

## Goal

- **One answer per message**: Either answer the question directly, or perform one action (e.g. create a reminder) and respond with one short confirmation (e.g. "Herinnering gepland") or one clarification question.
- No separate "cron answer" and "chat answer"; the user always gets a single, coherent reply.

## Message flow

1. **Entry**: Incoming message is handled by `Agent.process_message` in `agent.py`.
2. **Normal flow (default)**: Every message goes through the **gateway** (`run_agent_turn` in `gateway.py`):
   - Build messages with context and preferences (`build_chat_messages` from `prompts.py`).
   - Call the LLM with tools (`llm.chat_with_tools`), or use the structured fallback for models without native tool calling.
   - If the LLM returns tool calls (e.g. `cron.add`): execute them via `tool_router`, then ask the LLM once more for a final user-facing message (`tool_choice="none"`). That final message is the **only** response returned.
   - If no tool calls: the LLM’s reply (or the result of the structured fallback) is returned.
3. **Optional task path**: When the client sends header `X-Agent-Task-Mode: 1` and the message is classified as scheduling intent, the **task path** can be used instead: strict JSON protocol (tool_call / need_info / final), planner, executor, validator. See `_process_task_path` in `agent.py` and `task_prompts.py`.

## Main components

- **agent.py**: `Agent.process_message` – routing and orchestration; task path only when `force_task_mode` (header) and scheduling intent.
- **gateway.py**: `run_agent_turn` – single turn: chat with tools, execute tools if any, return one final message.
- **tool_router.py**: Exposes cron and registry tools to the LLM; `get_all_tools_for_llm()`, `call(tool_name, args, context)`.
- **prompts.py**: System prompt and scheduling addition; enforces "one answer" and clear behaviour for reminders (use cron.* directly or ask once, then one confirmation).
- **task_prompts.py**: System prompt for task path (JSON-only protocol) when `X-Agent-Task-Mode: 1` is used.
