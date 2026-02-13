# Neuroion

**Local-first home intelligence platform**

Neuroion is a privacy-first home intelligence system that runs entirely on your local network. All intelligence and memory live in a local Homebase (Raspberry Pi), while clients (iOS app, Telegram, setup UI) are thin interfaces.

## Core Principles

- **Local-first**: All intelligence and memory live in a local Homebase
- **Privacy-first**: No raw health data is stored, only derived context summaries
- **Consent-based**: System prepares actions, explains WHY, and only executes with explicit user consent
- **Appliance-like**: Feels like a dedicated appliance, not a Raspberry Pi or Linux computer

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   iOS App   │     │  Telegram   │     │  Setup UI   │
└──────┬──────┘     └──────┬───────┘     └──────┬──────┘
       │                   │                    │
       └───────────────────┼────────────────────┘
                           │
                    ┌──────▼──────┐
                    │   Homebase  │
                    │  (FastAPI)  │
                    └──────┬──────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
   ┌────▼────┐      ┌──────▼──────┐    ┌──────▼──────┐
   │  Ollama │      │   SQLite   │    │   Agent    │
   │   LLM   │      │  Database  │    │  System    │
   └─────────┘      └───────────┘    └────────────┘
```

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+ (for setup UI)
- Ollama running on localhost:11434. The default LLM is **Ollama with model `llama3.2`**; run `ollama run llama3.2` so the agent can use it out of the box.
- Docker and Docker Compose (optional, for containerized deployment)

### Development Setup

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd Neuroion
   ```

2. **Install Python dependencies**:
   ```bash
   cd neuroion/core
   pip install -r requirements.txt
   ```

3. **Initialize database** (created automatically on first API run). For demo data (default household), run:
   ```bash
   python scripts/seed_demo.py
   ```

4. **Start the Homebase server**:
   ```bash
   uvicorn neuroion.core.main:app --reload
   ```

5. **Start the setup UI** (in another terminal):
   ```bash
   cd apps/setup-ui
   npm install
   npm run dev
   ```

6. **Start the Telegram bot** (optional, in another terminal):
   ```bash
   export TELEGRAM_BOT_TOKEN=your_bot_token
   export HOMEBASE_URL=http://localhost:8000
   python -m neuroion.telegram.bot
   ```

### Run everything locally (one command)

From the **repository root**, after installing Python and Node dependencies once:

1. **Python**: create a venv and install deps (recommended, especially on Raspberry Pi / Linux where the API script will use it automatically):
   ```bash
   python3 -m venv venv
   ./venv/bin/pip install -r neuroion/core/requirements.txt   # Unix
   # or: venv\Scripts\pip install -r neuroion/core/requirements.txt   # Windows
   ```
2. **Node**: install root and subproject deps (run from repo root):
   ```bash
   npm install
   npm install --prefix apps/setup-ui && npm install --prefix apps/touchscreen-ui && npm install --prefix apps/dashboard
   ```
3. **Start everything**:
   ```bash
   npm run dev
   ```

The API will use `venv/bin/python` if present, otherwise `python3` (Unix) or `python` (Windows).

This starts:

| Service        | URL                    |
|----------------|------------------------|
| Homebase API   | http://localhost:8000  (or port from `API_PORT`, e.g. 8001) |
| Setup UI       | http://localhost:3000  |
| Touchscreen UI | http://localhost:3001  |
| Dashboard      | http://localhost:3002  |

If you set **`API_PORT`** in `.env` (e.g. `API_PORT=8001`), also set **`VITE_API_PORT=8001`** in the same `.env` so the touchscreen-ui and setup-ui use that API port. For the dashboard app, set **`NEXT_PUBLIC_API_PORT=8001`**. The backend, Telegram default URL, and dev scripts already read `API_PORT`.

Useful for **local testing** and **testing on a Raspberry Pi** on your network (open the URLs via the Pi’s IP, e.g. `http://192.168.1.x:3001` for the touchscreen).

**Ollama** (for local LLM) is not started by this command. Run `ollama serve` in a separate terminal, then `ollama run llama3.2` to pull and use the default model.

### Docker Deployment

1. **Set environment variables**:
   ```bash
   export SECRET_KEY=your-secret-key-here
   export TELEGRAM_BOT_TOKEN=your-telegram-bot-token
   ```

2. **Start all services**:
   ```bash
   cd infra
   docker-compose up -d
   ```

3. **Access services**:
   - Homebase API: http://localhost:8000
   - Setup UI: http://localhost:3000
   - API Docs: http://localhost:8000/docs

## Project Structure

```
Neuroion/
├── neuroion/              # Python package (backend)
│   ├── core/              # FastAPI core server
│   │   ├── api/           # API endpoints
│   │   ├── agent/         # Agent system
│   │   ├── llm/           # LLM integration
│   │   ├── memory/        # Database layer
│   │   └── security/      # Security & auth
│   └── telegram/          # Telegram bot (standalone or embedded)
├── apps/                  # Frontend applications
│   ├── setup-ui/          # React setup wizard
│   ├── touchscreen-ui/    # Kiosk / touch UI
│   └── dashboard/        # Next.js dashboard
├── scripts/               # Dev and utility scripts (e.g. seed_demo.py)
├── infra/                 # Docker & deployment
├── docs/                  # Documentation
└── ios/                   # iOS SwiftUI app
```

For demo data (default household), run from repo root: `python scripts/seed_demo.py`.

## Adding Agent Skills

Create a new Python module under `neuroion/core/agent/skills/` and register a tool:

```python
from sqlalchemy.orm import Session
from neuroion.core.agent.tool_registry import register_tool

@register_tool(
    name="my_new_tool",
    description="Short description of what it does",
    parameters={"type": "object", "properties": {"foo": {"type": "string"}}, "required": ["foo"]},
)
def my_new_tool(db: Session, household_id: int, foo: str):
    return {"result": f"foo={foo}"}
```

Tools are auto-imported from the `skills` package at startup.

## API Documentation

See [docs/API.md](docs/API.md) for complete API documentation.

## Configuration

Environment variables:

- `OLLAMA_URL`: Ollama server URL (default: http://localhost:11434)
- `OLLAMA_MODEL`: Model name (default: llama3.2)
- `DATABASE_PATH`: SQLite database path
- `SECRET_KEY`: Secret key for JWT tokens
- `TELEGRAM_BOT_TOKEN`: Telegram bot token (for Telegram service)
- `HOMEBASE_URL`: Homebase API URL (for clients)

## Deployment

### Raspberry Pi 5

1. Install Docker on Raspberry Pi
2. Clone repository
3. Configure environment variables
4. Run `docker-compose up -d`
5. Set up kiosk mode (see `infra/kiosk/README.md`)

### Mac (Development)

Follow the development setup instructions above.

## License

[Your License Here]

## Contributing

[Contributing Guidelines]
