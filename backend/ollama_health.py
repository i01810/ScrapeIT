"""Ollama service health checks via local HTTP API (/api/tags, /api/ps, /api/chat)."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import NamedTuple

from config import Settings


class OllamaHealth(NamedTuple):
    ollama_connected: bool
    ollama_message: str
    ollama_model_installed: bool
    ollama_model_loaded: bool
    ollama_running_models: list[str]


def _normalize_model_name(name: str) -> str:
    return name.strip().removesuffix(":latest")


def _entry_model_name(entry: dict) -> str:
    return (entry.get("name") or entry.get("model") or "").strip()


def _models_match(selected: str, candidate: str) -> bool:
    if not candidate:
        return False
    return _normalize_model_name(selected) == _normalize_model_name(candidate)


def _fetch_json(url: str, timeout: float = 5.0) -> dict:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def _probe_model_via_api(base: str, model: str, timeout: float = 20.0) -> tuple[bool, str]:
    """Fallback when /api/ps is empty but the model may still respond over HTTP."""
    payload = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": "ping"}],
            "stream": False,
            "options": {"num_predict": 1},
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        f"{base}/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                return True, "Model responded to HTTP API probe."
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return False, f"HTTP {exc.code}: {body[:200]}"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)
    return False, "API probe failed."


def check_ollama_health(settings: Settings) -> OllamaHealth:
    base = settings.ollama_base_url.rstrip("/")
    selected = settings.ollama_model

    try:
        tags_data = _fetch_json(f"{base}/api/tags")
        tag_names = [_entry_model_name(m) for m in tags_data.get("models", [])]
        tag_names = [name for name in tag_names if name]
        installed = any(_models_match(selected, name) for name in tag_names)
    except urllib.error.URLError as exc:
        reason = getattr(exc, "reason", exc)
        return OllamaHealth(
            ollama_connected=False,
            ollama_message=f"Cannot reach Ollama at {base}: {reason}",
            ollama_model_installed=False,
            ollama_model_loaded=False,
            ollama_running_models=[],
        )
    except Exception as exc:  # noqa: BLE001
        return OllamaHealth(
            ollama_connected=False,
            ollama_message=f"Ollama tags check failed: {exc}",
            ollama_model_installed=False,
            ollama_model_loaded=False,
            ollama_running_models=[],
        )

    try:
        ps_data = _fetch_json(f"{base}/api/ps")
        running = [_entry_model_name(m) for m in ps_data.get("models", [])]
        running = [name for name in running if name]
        loaded = any(_models_match(selected, name) for name in running)
    except Exception as exc:  # noqa: BLE001
        return OllamaHealth(
            ollama_connected=True,
            ollama_message=f"Ollama reachable; running-model check failed: {exc}",
            ollama_model_installed=installed,
            ollama_model_loaded=False,
            ollama_running_models=[],
        )

    if not loaded and installed:
        api_ok, api_detail = _probe_model_via_api(base, selected)
        if api_ok:
            loaded = True
            message = (
                f"Model '{selected}' is ready via Ollama HTTP API. "
                f"{api_detail} (ps was empty — common with interactive `ollama run`.)"
            )
            return OllamaHealth(
                ollama_connected=True,
                ollama_message=message,
                ollama_model_installed=installed,
                ollama_model_loaded=loaded,
                ollama_running_models=running,
            )

    if loaded:
        message = f"Model '{selected}' is loaded and running."
    elif not installed:
        message = f"Model '{selected}' is not installed. Run: ollama pull {selected}"
    elif running:
        message = (
            f"Model '{selected}' is installed but not loaded. "
            f"Currently running: {', '.join(running)}. "
            f"Run: ollama run {selected}"
        )
    else:
        message = (
            f"Model '{selected}' is installed but not loaded (ollama ps is empty). "
            f"Run: ollama run {selected}"
        )

    return OllamaHealth(
        ollama_connected=True,
        ollama_message=message,
        ollama_model_installed=installed,
        ollama_model_loaded=loaded,
        ollama_running_models=running,
    )
