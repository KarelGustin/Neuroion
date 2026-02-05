# Neuroion Core Inventory

Doel: read-only inventaris van huidige codebase als basis voor Neuroion Core (engine-vendor traject).

## 1) Entrypoints

### Python main / API server
- `neuroion/core/main.py`
  - FastAPI app bootstrap (`app = FastAPI(...)`).
  - Lifespan startup/shutdown:
    - `init_db()`
    - `start_telegram_bot()` / `stop_telegram_bot()`
  - Router registratie: health, setup, join, members, pairing, chat, events, admin, dashboard, integrations, preferences.
  - Lokale run entrypoint: `if __name__ == "__main__": uvicorn.run(...)`.

### Telegram handler
- `telegram/bot.py`
  - Bot entrypoint: `main()`.
  - Runtime: `Application.builder().token(...).build()` + `run_polling(...)`.
  - Handlers:
    - `/start` → `start_command`
    - `/pair` → `pair_command`
    - `/dashboard` → `dashboard_command`
    - `/execute` → `execute_command`
    - vrije tekst → `handle_message`

### Infra/API container entrypoints
- `infra/Dockerfile`
  - Container CMD: `uvicorn neuroion.core.main:app --host 0.0.0.0 --port 8000`.
- `infra/docker-compose.yml`
  - Services: `homebase`, `setup-ui`, `telegram-bot`.

## 2) Huidige Telegram flow (bestanden + functies)

### Bestanden
- `telegram/bot.py`
- `telegram/config.py`
- `neuroion/core/services/telegram_service.py` (embedded opstartpad vanuit Homebase)

### Flow
1. Bot start via `telegram/bot.py:main()` of embedded via `start_telegram_bot()` in `neuroion/core/services/telegram_service.py`.
2. Pairing:
   - `/start <code>` of `/pair <code>`
   - `POST /pair/confirm` naar Homebase API met `device_id=telegram_<user_id>`.
   - JWT token wordt lokaal gepersisteerd in `~/.neuroion/telegram_tokens.json`.
3. Chat:
   - `handle_message()` controleert pairing token.
   - `POST /chat` met bearer token.
   - Reply van backend (`message`, optioneel `actions`) wordt teruggestuurd naar Telegram.
4. Action confirm:
   - `/execute <action_id>` → `POST /chat/actions/execute`.
5. Dashboard deep-link/login code:
   - `/dashboard` gebruikt backend endpoints voor login code + dashboard URL.

## 3) Memory opslag (sqlite/paths/modules)

### Database pad en driver
- `neuroion/core/config.py`
  - `DATABASE_PATH` env (default: `~/.neuroion/neuroion.db`).
  - `get_database_url()` retourneert `sqlite:///...` en maakt parent directory aan.

### Database modules
- `neuroion/core/memory/db.py`
  - SQLAlchemy engine op SQLite.
  - `init_db()` maakt schema en voert lichte runtime kolom-migraties uit.
  - `get_db()` dependency voor FastAPI.
  - SQLite pragmas: foreign keys, WAL, busy timeout.
- `neuroion/core/memory/models.py`
  - ORM modellen (users/households/config/history/etc.).
- `neuroion/core/memory/repository.py`
  - Repositorylaag voor CRUD en querylogica.

### Extra lokale state buiten sqlite
- `telegram/bot.py`
  - Telegram device tokens in JSON: `~/.neuroion/telegram_tokens.json`.

## 4) Infra boot (systemd, docker-compose)

### Systemd
- `infra/systemd/neuroion-setup-mode.service`
  - oneshot service, start setup-mode script.
- `infra/systemd/neuroion-normal-mode.service`
  - oneshot service, start normal-mode script.

### Network/scripts
- `infra/scripts/switch-to-setup-mode.sh`
- `infra/scripts/switch-to-normal-mode.sh`
- `infra/scripts/switch-network-mode.sh`
- `infra/scripts/setup-softap.sh`
- `infra/scripts/setup-mdns.sh`
- `infra/scripts/install.sh`
  - Installeert dependencies, buildt UI’s, kopieert systemd units/scripts, reload systemd.

### Docker Compose
- `infra/docker-compose.yml`
  - `homebase`: FastAPI backend (poort 8000)
  - `setup-ui`: setup frontend (poort 3000)
  - `telegram-bot`: losse botcontainer

## 5) UI’s en rolverdeling

### `setup-ui/`
- Setup en onboarding frontend voor initiële configuratie.
- Focus op pairing/QR, status, en setup wizard stappen.
- Relevante bron:
  - `setup-ui/README.md`
  - `setup-ui/src/components/*`

### `touchscreen-ui/`
- Dedicated touchscreen/kiosk UI (los van setup wizard).
- Package naam wijst op kiosk/touch context: `neuroion-touchscreen-ui`.
- Relevante bron:
  - `touchscreen-ui/package.json`

### `dashboard-nextjs/`
- Web dashboard (Next.js) voor gebruikersflow en beheer/join trajecten.
- Aanwezige pagina’s tonen o.a. join flow en completion screens.
- Relevante bron:
  - `dashboard-nextjs/app/layout.tsx`
  - `dashboard-nextjs/app/join/page.tsx`
  - `dashboard-nextjs/app/join/complete/page.tsx`

## 6) Snelle pointerlijst voor volgende taken

- Core API bootstrap: `neuroion/core/main.py`
- Setup endpoints: `neuroion/core/api/setup.py`
- Chat endpoint: `neuroion/core/api/chat.py`
- Telegram runtime (standalone): `telegram/bot.py`
- Telegram runtime (embedded): `neuroion/core/services/telegram_service.py`
- DB config + path: `neuroion/core/config.py`
- DB engine/session/init: `neuroion/core/memory/db.py`
- Infra compose: `infra/docker-compose.yml`
- Infra systemd units: `infra/systemd/*.service`
