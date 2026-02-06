# Neuroion Config Schema (v1)

This document describes the central device configuration and runtime state used by Neuroion Core. One device has a single source of truth: **device config** (persisted) and **runtime state** (derived or persisted).

## Schema version

- **Version:** 1
- **Stored in:** SQLite via `system_config` and `device_config` tables.

## Device config (persisted)

| Field | Storage | Description |
|-------|---------|-------------|
| **device_name** | `device_config.hostname` | Display name for the device (default: "Neuroion Core"). |
| **timezone** | `system_config` key `"timezone"`, category `"device"` | IANA timezone (e.g. `Europe/Amsterdam`). |
| **wifi** | `system_config` key `"wifi"`, category `"wifi"` | `{ "ssid": string, "password": string }`. Sensitive; never log or return to frontend. |
| **llm_provider** | `system_config` key `"llm_provider"`, category `"llm"` | `{ "provider": "local" \| "cloud" \| "custom" }`. |
| **llm_ollama** | `system_config` key `"llm_ollama"`, category `"llm"` | `{ "base_url", "model", "timeout" }` for local. |
| **llm_cloud** | `system_config` key `"llm_cloud"`, category `"llm"` | Cloud provider config (e.g. HuggingFace); may contain `api_key` — never expose. |
| **llm_custom** | `system_config` key `"llm_custom"`, category `"llm"` | Custom/OpenAI-compatible config; may contain `api_key` — never expose. |
| **neuroion_core** | `system_config` key `"neuroion_core"`, category `"agent"` | Neuroion Core (agent/gateway) config: `{ "gateway"?: { "port"?, "bind"? }, "ui"?: { "assistant": { "name"?: string } }, "models"?: { "defaults"?: { "provider"?, "model"? } } }`. Optional; if missing, gateway config is derived from device + LLM only. |
| **privacy** | `system_config` key `"privacy"`, category `"privacy"` | `{ "telemetry": bool, "updates_check": bool }` (optional). |

## Runtime state

| Field | Storage | Description |
|-------|---------|-------------|
| **setup_completed** | `device_config.setup_completed` | True once onboarding (WiFi, device, AI, household, etc.) is done. |
| **wifi_configured** | `device_config.wifi_configured` | True when home WiFi has been successfully applied (and optionally connected). |
| **last_mode** | Not persisted (or optional `system_config` key) | `"setup"` (SoftAP) or `"lan"` (normal). Can be derived from NetworkManager.get_current_mode(). |
| **retention_policy** | `device_config.retention_policy` | Optional `{ "days": int, "auto_delete": bool }`. |

## Migration from existing data

- **SystemConfig:** Existing keys (`wifi`, `llm_provider`, `llm_ollama`, `llm_cloud`, `llm_custom`, `neuroion_core`) remain as-is. No schema change required. `neuroion_core` is optional; if missing, Neuroion Core config is derived from device + LLM at runtime.
- **DeviceConfig:** Existing columns (`wifi_configured`, `hostname`, `setup_completed`, `retention_policy`) are used. For v1 we use `hostname` as device name; timezone is added as a new `system_config` entry (`timezone`, category `device`) when needed.
- **Future versions:** When introducing v2, add a `config_schema_version` key to `system_config` and document migration steps in this file.

## Single source of truth

- All setup and runtime reads/writes for device config should go through a central module (e.g. `neuroion.core.config_store`) that uses `SystemConfigRepository` and `DeviceConfigRepository`. This avoids duplicate logic and keeps one consistent view of device config and runtime state.

## Member personalisation

- Device config (including Neuroion Core) is global: one per device. After onboarding, members are added via the join flow. Per-member data (services, context) is stored per user: `user_integrations`, `preferences`, `context_snapshots`. Members connect their own integrations and context via dashboard/API; the device and Neuroion Core config stay shared.
