# Uitleg: werking en aanpassingen

## 1. Werking op dit moment

- **Telegram**: De gebruiker stuurt een bericht → de bot roept Homebase `POST /chat` aan met een Bearer token. Homebase haalt de conversatiegeschiedenis (SQLite) op en roept de agent aan. De agent gebruikt de ingestelde LLM (Ollama, Cloud of OpenAI). Alleen bij OpenAI worden tool_calls daadwerkelijk uitgevoerd; bij Ollama/Cloud geeft het model alleen tekst (“Ik maak een cron job…”) en wordt er geen tool uitgevoerd. Bij “actions” moet de gebruiker expliciet `/execute <id>` typen.

- **Cron**: Jobs staan in `~/.neuroion/cron/jobs.json`, runs in `runs/<jobId>.jsonl`. De scheduler draait in hetzelfde proces als de API. Endpoints `/tool/cron.*` bestaan al; ze worden gebruikt wanneer de LLM echte tool_calls teruggeeft (OpenAI) of wanneer de **task-mode** (gestructureerd JSON) wordt gebruikt voor scheduling-berichten.

- **Task-mode** (nieuw): Als `AGENT_TASK_MODE=1` (standaard) en het gebruikersbericht wijst op planning/herinneringen (bijv. “herinner me”, “elke dag om 8”), dan gebruikt de agent het **gestructureerde JSON-protocol**: de LLM moet precies één JSON-object teruggeven (`tool_call`, `need_info` of `final`). De agent parsed dat, voert cron-tools direct uit via de dispatcher en voorkomt eindeloze “Ik zal…”-antwoorden met een duplicate-intent guard.

## 2. Waar aanpassingen komen

- **Task-capable maken (tegen “loopt vast”-probleem)**  
  - Nieuwe bestanden: `neuroion/core/agent/task_manager.py`, `tool_protocol.py`, `task_prompts.py`, `neuroion/core/agent/tools/dispatcher.py` en `cron_handlers.py`.  
  - Aanpassingen: `neuroion/core/agent/agent.py` (task-pad), `neuroion/core/api/chat.py` (header `X-Agent-Task-Mode`), `neuroion/core/cron/storage.py` (pad naar `~/.neuroion/cron/`).  
  - Hier zijn het gestructureerde JSON-protocol en de task state machine geïmplementeerd zodat ook lokale LLMs tools kunnen aansturen.

- **Anti-loop en veiligheid**  
  - In `task_manager.py`: max turns (4), max tool attempts (2).  
  - In `tool_protocol.py`: duplicate-intent detectie.  
  - In cron: bestaande limieten (20 jobs/dag, everyMs ≥ 60s); bevestiging bij destructieve/hoge-frequentie acties kan hierop aansluiten.

- **Tests**  
  - Nieuwe tests in `tests/`: o.a. `test_tool_protocol.py`, `test_task_manager.py`, `test_dispatcher_integration.py`, `test_anti_loop.py`, en de map `tests/behavior_prompts/` met de 10 NL→JSON-voorbeelden.  
  - Uitvoeren: `pytest tests/test_tool_protocol.py tests/test_task_manager.py tests/test_dispatcher_integration.py tests/test_anti_loop.py tests/test_behavior_prompts.py -v` (na `pip install pytest` indien nodig).

## 3. Waar je moet zijn om X te doen

| Doel | Bestand(en) |
|------|-------------|
| Cron-job limiet of tijdzone wijzigen | `neuroion/core/config.py` (env vars), `neuroion/core/cron/validation.py`, `neuroion/core/cron/service.py` |
| Telegram-berichten aanpassen | `neuroion/telegram/bot.py` (`handle_message`, `execute_command`) |
| Agent prompt (normale chat) | `neuroion/core/agent/prompts.py` |
| Task-prompt (alleen JSON) | `neuroion/core/agent/task_prompts.py` |
| Welke tool wanneer uitvoeren | `neuroion/core/agent/tools/dispatcher.py`, `neuroion/core/agent/tools/cron_handlers.py` |
| Cron-contract (main/isolated, schedule types) | `neuroion/core/cron/models.py`, `neuroion/core/cron/validation.py` |
| Task state machine / limieten | `neuroion/core/agent/task_manager.py` |
| Parsing en anti-loop (JSON, duplicate intent) | `neuroion/core/agent/tool_protocol.py` |

## 4. Feature flags en rollback

- **AGENT_TASK_MODE**: In `neuroion/core/config.py` (env `AGENT_TASK_MODE`, standaard `1`). Zet op `0` om het task-pad uit te schakelen; dan wordt alleen het bestaande chat-pad (en bij OpenAI tool_calls) gebruikt.
- **Rollback**: Zet `AGENT_TASK_MODE=0` of pas de keyword-detectie in `agent._scheduling_intent()` aan. Cron-scheduler en `/tool/cron.*` blijven bruikbaar.
