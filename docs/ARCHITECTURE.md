# Neuroion Architecture

## Overview

Neuroion is a local-first home intelligence platform built with a strict client-server architecture. All business logic and intelligence live in the Homebase (FastAPI server), while clients are thin interfaces that communicate via HTTP API.

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      Clients                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │ iOS App  │  │ Telegram │  │ Setup UI │              │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘              │
│       │             │              │                     │
│       └─────────────┼──────────────┘                     │
│                     │                                     │
│              HTTP API (REST)                             │
└─────────────────────┼─────────────────────────────────────┘
                      │
┌─────────────────────▼─────────────────────────────────────┐
│                    Homebase                                │
│  ┌──────────────────────────────────────────────┐        │
│  │              FastAPI Server                   │        │
│  │  - Authentication & Authorization             │        │
│  │  - Request Routing                            │        │
│  │  - Error Handling                             │        │
│  └──────────────────┬───────────────────────────┘        │
│                     │                                      │
│  ┌──────────────────▼───────────────────────────┐        │
│  │              Agent System                      │        │
│  │  - Intent Interpretation                       │        │
│  │  - Action Planning                             │        │
│  │  - Tool Execution                              │        │
│  └──────┬──────────────────────┬─────────────────┘        │
│         │                      │                           │
│  ┌──────▼──────┐      ┌───────▼────────┐                  │
│  │    LLM      │      │  Tool Registry │                  │
│  │ (Ollama/    │      │  - Menu Gen    │                  │
│  │  Cloud)     │      │  - Grocery     │                  │
│  └─────────────┘      │  - Grocery     │                  │
│                       │  - Preferences │                  │
│                       └────────────────┘                  │
│                                                             │
│  ┌──────────────────────────────────────────────┐        │
│  │          Memory Layer (SQLite)                │        │
│  │  - Households, Users, Preferences            │        │
│  │  - Context Snapshots                         │        │
│  │  - Audit Logs                                │        │
│  └──────────────────────────────────────────────┘        │
│                                                             │
│  ┌──────────────────────────────────────────────┐        │
│  │          Security Layer                       │        │
│  │  - Token Management                           │        │
│  │  - Permission Checking                        │        │
│  │  - Audit Logging                              │        │
│  └──────────────────────────────────────────────┘        │
└───────────────────────────────────────────────────────────┘
```

## Component Details

### Homebase (FastAPI Core)

The Homebase is the central intelligence hub. It contains:

- **API Layer**: FastAPI endpoints for all client interactions
- **Agent System**: Interprets user intent and decides on actions
- **LLM Integration**: AI provider abstraction (`neuroion.core.llm`). All providers implement the same interface (`LLMClient` in `base.py`): `chat()`, `complete()`, `stream()`. Implementations: `OllamaClient` (local), `CloudLLMClient` (e.g. HuggingFace), `OpenAILLMClient` (OpenAI/Anthropic-compatible). The active provider is chosen from device config via `get_llm_client_from_config(db)`.
- **Memory Layer**: SQLite database for persistent storage
- **Security Layer**: Authentication, authorization, and audit logging

### Agent System

The agent follows this flow:

1. **Receive Message**: User message arrives via `/chat` endpoint
2. **Gather Context**: Load recent context snapshots and preferences
3. **LLM Reasoning**: Use Ollama to interpret intent and generate response
4. **Decision**: Determine if action is needed or direct answer suffices
5. **Action Proposal**: If action needed, propose with reasoning
6. **Execution**: Only execute after explicit user confirmation

### Memory Layer

SQLite database stores:

- **Households**: Home units
- **Users**: Users within households
- **Preferences**: Household and user preferences
- **Context Snapshots**: Derived summaries (location, health)
- **Audit Logs**: All suggestions, confirmations, and executions

**Important**: Never stores raw health data, only derived summaries.

#### Database concurrency and connection lifecycle

- The SQLAlchemy engine is created once per process (global) with a SQLite URL and `NullPool`.
- Sessions are created via a single `SessionLocal` factory, but **never shared**:
  - API routes obtain a session via the `get_db` FastAPI dependency.
  - Scripts and background jobs use the `db_session()` context manager.
  - Each session records its owning thread in `session.info["owner_thread_id"]` and is only valid
    within that thread and scope.
- Guardrails:
  - `require_active_session` raises if a session is closed or used from a different thread than the
    one that created it.
  - A `before_flush` SQLAlchemy event (`validate_session_owner_thread`) enforces the same invariant
    at flush time, failing fast with a clear `RuntimeError` instead of letting SQLite crash.
- There is **no global shared Session or Connection**; all DB access is single-owner and scoped.

For concurrency/debugging, you can enable extra DB lifecycle logging by setting `DB_DEBUG_LOG=1`
in the environment (or turning on `DATABASE_ECHO`). This logs session creation/closure together
with thread identifiers, which is useful when investigating threading issues.

#### uvloop and event loop selection

Neuroion runs on Uvicorn and can use `uvloop` when installed. For isolation tests, you can force
the standard asyncio event loop:

- Start Uvicorn with the standard loop:
  - `UVICORN_LOOP=asyncio uvicorn neuroion.core.main:app --host 0.0.0.0 --port 8000`
- Or make sure `uvloop` is not installed in the environment.

The structural safety comes from the explicit session lifecycle and thread-ownership checks above,
not from using or avoiding `uvloop`. Disabling `uvloop` is only recommended as a diagnostic step.

### Security

- **Pairing-based**: Devices pair using short-lived codes
- **JWT Tokens**: Long-lived tokens for authenticated sessions
- **Household Scoping**: All data is scoped to households
- **Permission System**: Role-based access control (owner, admin, member)
- **Audit Trail**: Complete log of all actions

### Clients

Clients are thin interfaces with no business logic:

- **iOS App**: SwiftUI app for chat, location, and health data
- **Telegram Bot**: Python bot that forwards messages to Homebase
- **Setup UI**: React web app for initial pairing (kiosk mode)

## Data Flow

### Chat Flow

```
User → Client → HTTP POST /chat → Homebase
                                    │
                                    ├─→ Auth Check
                                    ├─→ Agent System
                                    │   ├─→ Load Context
                                    │   ├─→ LLM Reasoning
                                    │   └─→ Action Decision
                                    │
                                    └─→ Response (message + actions)
                                        │
User ← Client ← HTTP Response ←────────┘
```

### Action Execution Flow

```
User → Client → HTTP POST /chat/actions/execute → Homebase
                                                    │
                                                    ├─→ Verify Action
                                                    ├─→ Execute Tool
                                                    ├─→ Log to Audit
                                                    │
                                                    └─→ Response (result)
                                                        │
User ← Client ← HTTP Response ←────────────────────────┘
```

### Event Ingestion Flow

```
Client → HTTP POST /events → Homebase
                              │
                              ├─→ Validate Event
                              ├─→ Create Context Snapshot
                              │
                              └─→ Response (success)
```

## Privacy & Security

### Privacy Principles

1. **No Raw Data**: Health data is processed client-side, only summaries sent
2. **Local Storage**: All data stored locally on Homebase
3. **No Cloud**: No external services, everything runs locally
4. **Explicit Consent**: Actions require explicit user confirmation

### Security Measures

1. **Pairing Codes**: Short-lived, one-time use codes
2. **JWT Tokens**: Secure, long-lived authentication
3. **Household Isolation**: Data scoped to households
4. **Audit Logging**: Complete trail of all actions
5. **Input Validation**: All inputs validated before processing

## Deployment

### Development

- FastAPI with hot reload
- SQLite database in user directory
- Ollama on localhost

### Production (Raspberry Pi)

- Docker containers for all services
- Persistent volumes for database
- Kiosk mode for setup UI
- Systemd services for auto-start

## Extensibility

The system is designed for extensibility:

- **LLM Interface**: Abstract interface allows swapping LLM providers
- **Tool Registry**: Easy to add new tools/actions
- **Plugin System**: Future plugin architecture for custom integrations
