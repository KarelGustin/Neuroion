"""
Neuroion adapter: start/stop Neuroion gateway as the Neuroion Agent.

Uses the vendored Neuroion in vendor/neuroion; starts gateway via Node.
Writes minimal Neuroion config from Neuroion device config (no API keys in file).
"""
import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_process: Optional[subprocess.Popen] = None


def _neuroion_root() -> Optional[Path]:
    """Return path to vendor/neuroion (repo root is parent of neuroion package)."""
    try:
        # neuroion/core/services/neuroion_adapter.py -> repo root = ../../..
        this_file = Path(__file__).resolve()
        repo_root = this_file.parent.parent.parent.parent
        neuroion = repo_root / "vendor" / "neuroion"
        if neuroion.is_dir():
            return neuroion
    except Exception as e:
        logger.warning("Could not resolve Neuroion root: %s", e)
    return None


def is_available() -> bool:
    """Return True if Neuroion vendor is present and runnable."""
    root = _neuroion_root()
    if not root:
        return False
    run_script = root / "scripts" / "run-node.mjs"
    return run_script.is_file()


def start(config_dir: Optional[Path] = None, env_extra: Optional[Dict[str, str]] = None) -> bool:
    """
    Start the Neuroion gateway process.
    config_dir: optional directory for NEUROION_STATE_DIR (contains neuroion.json).
    env_extra: optional env vars (e.g. API keys); never logged.
    Returns True if started successfully.
    """
    global _process
    if _process is not None:
        logger.info("Neuroion gateway already running")
        return True
    root = _neuroion_root()
    if not root:
        logger.error("Neuroion vendor not found")
        return False
    run_script = root / "scripts" / "run-node.mjs"
    if not run_script.is_file():
        logger.error("Neuroion run script not found: %s", run_script)
        return False
    env = os.environ.copy()
    if config_dir is not None:
        env["NEUROION_STATE_DIR"] = str(config_dir)
    if env_extra:
        env.update(env_extra)
    try:
        _process = subprocess.Popen(
            ["node", "scripts/run-node.mjs", "gateway"],
            cwd=str(root),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        logger.info("Neuroion gateway started (PID %s)", _process.pid)
        return True
    except Exception as e:
        logger.error("Failed to start Neuroion gateway: %s", e, exc_info=True)
        _process = None
        return False


def stop() -> bool:
    """Stop the Neuroion gateway process. Returns True if stopped or was not running."""
    global _process
    if _process is None:
        return True
    try:
        _process.terminate()
        _process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        _process.kill()
        _process.wait(timeout=5)
    except Exception as e:
        logger.warning("Error stopping Neuroion gateway: %s", e)
    finally:
        _process = None
        logger.info("Neuroion gateway stopped")
    return True


def is_running() -> bool:
    """Return True if the gateway process is running."""
    global _process
    if _process is None:
        return False
    return _process.poll() is None


def write_config(device_config: Dict[str, Any], state_dir: Path) -> None:
    """
    Write Neuroion config from Neuroion device config and optional neuroion_core blob.
    Merges device LLM + neuroion_core (if present) with defaults. Does not write API keys.
    """
    state_dir = Path(state_dir)
    state_dir.mkdir(parents=True, exist_ok=True)

    # Defaults from device config (LLM)
    llm = device_config.get("llm_provider") or {}
    provider = llm.get("provider", "local") if isinstance(llm, dict) else (llm or "local")
    ollama = device_config.get("llm_ollama") or {}
    openai = device_config.get("llm_openai") or {}
    custom = device_config.get("llm_custom") or {}
    model_name = "qwen2:7b-instruct"
    defaults_provider = "ollama"
    provider_base_url = None

    if provider == "local":
        model_name = ollama.get("model", "qwen2:7b-instruct") if isinstance(ollama, dict) else "qwen2:7b-instruct"
        defaults_provider = "ollama"
    elif provider == "openai":
        model_name = openai.get("model", "gpt-4o-mini") if isinstance(openai, dict) else "gpt-4o-mini"
        defaults_provider = "openai"
        if isinstance(openai, dict):
            provider_base_url = openai.get("base_url")
    elif provider == "custom":
        model_name = custom.get("model", "gpt-4o-mini") if isinstance(custom, dict) else "gpt-4o-mini"
        defaults_provider = "openai"
        if isinstance(custom, dict):
            provider_base_url = custom.get("base_url")

    # Base config: defaults derived from device
    cfg = {
        "gateway": {
            "port": 3141,
            "bind": "lan",
            "controlUi": {"enabled": True, "basePath": "/neuroion"},
        },
        "ui": {"assistant": {"name": "Neuroion Agent"}},
        "models": {"defaults": {"provider": defaults_provider, "model": model_name}},
    }

    if provider_base_url and provider_base_url != "https://api.openai.com/v1":
        cfg.setdefault("models", {}).setdefault("providers", {})
        cfg["models"]["providers"]["openai"] = {"baseUrl": provider_base_url}

    # Merge neuroion_core blob if present (same config store; rebranded Neuroion Core)
    def _deep_merge(base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
        merged = dict(base or {})
        for key, value in (update or {}).items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = _deep_merge(merged[key], value)
            else:
                merged[key] = value
        return merged

    core = device_config.get("neuroion_core")
    if core and isinstance(core, dict):
        cfg = _deep_merge(cfg, core)

    config_path = state_dir / "neuroion.json"
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
    logger.info("Wrote Neuroion Core config to %s", config_path)


def send_chat(message: str, gateway_port: int = 3141) -> Optional[str]:
    """
    Send a chat message to the Neuroion gateway and return the assistant reply.
    Returns None if the gateway is not running or the request fails (caller should use Python agent).
    """
    if not is_running():
        return None
    try:
        import urllib.request
        import urllib.error
        req = urllib.request.Request(
            f"http://127.0.0.1:{gateway_port}/v1/chat",
            data=json.dumps({"message": message}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("message") or data.get("reply") or data.get("content")
    except Exception as e:
        logger.debug("Neuroion gateway chat request failed: %s", e)
        return None


def build_env_extra_from_db(db) -> Dict[str, str]:
    """
    Build env vars for Neuroion from secure config (API keys).
    Returns a dict; does not log secrets.
    """
    from neuroion.core.memory.repository import SystemConfigRepository
    from neuroion.core.config import settings as app_settings

    env: Dict[str, str] = {}
    provider_config = SystemConfigRepository.get(db, "llm_provider")
    provider = provider_config.value if isinstance(provider_config.value, str) else provider_config.value.get("provider", "local") if provider_config else "local"

    if provider == "openai":
        openai_config = SystemConfigRepository.get(db, "llm_openai")
        if openai_config and isinstance(openai_config.value, dict):
            api_key = openai_config.value.get("api_key")
            base_url = openai_config.value.get("base_url")
            if api_key:
                env["OPENAI_API_KEY"] = api_key
            if base_url and base_url != "https://api.openai.com/v1":
                env["OPENAI_BASE_URL"] = base_url
    elif provider == "custom":
        custom_config = SystemConfigRepository.get(db, "llm_custom")
        if custom_config and isinstance(custom_config.value, dict):
            api_key = custom_config.value.get("api_key")
            base_url = custom_config.value.get("base_url")
            if api_key:
                env["OPENAI_API_KEY"] = api_key
            if base_url and base_url != "https://api.openai.com/v1":
                env["OPENAI_BASE_URL"] = base_url

    if getattr(app_settings, "telegram_bot_token", None):
        env["TELEGRAM_BOT_TOKEN"] = app_settings.telegram_bot_token
    if getattr(app_settings, "telegram_bot_username", None):
        env["TELEGRAM_BOT_USERNAME"] = app_settings.telegram_bot_username

    return env
