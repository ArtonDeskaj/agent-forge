"""Minimal OpenAI-compatible chat client.

Uses only the standard library so Agent Forge runs anywhere Python runs.
Works against OpenAI, Ollama (/v1), vLLM, LM Studio, and similar endpoints.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request

from .config import Config


class LLMError(RuntimeError):
    """Raised when the provider cannot produce a completion."""


def chat(
    config: Config,
    system: str,
    user: str,
    *,
    retries: int = 2,
    json_mode: bool = False,
) -> str:
    """Return the assistant text for a single system+user exchange."""
    payload: dict = {
        "model": config.model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    body = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if config.api_key:
        headers["Authorization"] = f"Bearer {config.api_key}"

    url = f"{config.base_url}/chat/completions"
    last_error: Exception | None = None

    for attempt in range(retries + 1):
        request = urllib.request.Request(url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=config.timeout_seconds) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as exc:  # noqa: PERF203
            detail = exc.read().decode("utf-8", "replace")[:400]
            last_error = LLMError(f"HTTP {exc.code} from {url}: {detail}")
            if exc.code in (429, 500, 502, 503, 504) and attempt < retries:
                time.sleep(2 ** attempt)
                continue
            raise last_error from exc
        except (urllib.error.URLError, KeyError, json.JSONDecodeError) as exc:
            last_error = LLMError(f"Request to {url} failed: {exc}")
            if attempt < retries:
                time.sleep(2 ** attempt)
                continue
            raise last_error from exc

    raise last_error or LLMError("Unknown LLM failure")


def chat_json(config: Config, system: str, user: str, *, retries: int = 2) -> dict:
    """Ask for a JSON object and parse it, tolerating code fences."""
    raw = chat(config, system, user, retries=retries, json_mode=True)
    return parse_json_object(raw)


def parse_json_object(raw: str) -> dict:
    """Extract the first JSON object from a model response."""
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise LLMError(f"Model did not return valid JSON: {raw[:300]!r}")
        value = json.loads(text[start : end + 1])
    if not isinstance(value, dict):
        raise LLMError(f"Expected a JSON object, got: {type(value).__name__}")
    return value
