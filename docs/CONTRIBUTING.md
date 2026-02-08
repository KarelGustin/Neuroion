# Contributing to Neuroion

## Coding conventions

- **Branding:** Use "Neuroion", "Neuroion Agent", and "Neuroion Core" in all user-facing strings. Do not expose "Neuroion" or other vendor names in the UI.
- **Naming:** Prefer consumer-friendly, clear names for APIs and UI (e.g. "Add Member" not "CreateUser" in copy).
- **Config:** Device config and runtime state are centralized; see [CONFIG_SCHEMA.md](CONFIG_SCHEMA.md). Use `neuroion.core.config_store` for setup-related reads/writes where applicable.
- **Secrets:** Never log API keys, WiFi passwords, or setup secrets. Never return keys in API responses.

## Definition of Done

A change is considered done when:

1. **Tests:** New or modified code paths have tests where practical (unit or integration).
2. **Lint:** Code passes the project linter (e.g. ruff/flake8 for Python, ESLint for frontend if configured).
3. **No secrets in logs:** No passwords, API keys, or tokens are logged or echoed.
4. **Config schema:** If you add or change persisted config, document it in [CONFIG_SCHEMA.md](CONFIG_SCHEMA.md) and consider migration for existing data.
5. **Smoke test:** For setup/onboarding or core flows, the relevant part of the [Smoke test checklist](#smoke-test-checklist) still passes (or is updated).

## Smoke test checklist

Use this to verify core flows after changes. Full step-by-step checklist: [SMOKE_TEST.md](SMOKE_TEST.md).

- [ ] **API health:** `GET /health` returns 200 and `status: ok`.
- [ ] **Setup status:** `GET /setup/status` returns `is_complete` and `steps` (wifi, llm, household).
- [ ] **Setup flow (dev):** Run setup UI, complete WiFi (or skip), household, owner, privacy, model; then `POST /setup/complete`; status shows complete.
- [ ] **Kiosk mode:** Open setup UI with `?kiosk=1`; before complete see Config QR; after complete see dashboard.
- [ ] **Dashboard:** After setup, `GET /api/status` returns network, model, household; dashboard shows Add Member when setup is complete.

## Release checklist

- [ ] Version bumped (e.g. in `neuroion/core` or package.json where applicable).
- [ ] CONFIG_SCHEMA.md and migration steps updated if config changed.
- [ ] [SMOKE_TEST.md](SMOKE_TEST.md) run on target platform (e.g. Raspberry Pi or dev).
- [ ] Changelog or release notes updated.
- [ ] No Neuroion or vendor names in user-facing UI (Neuroion branding only).
