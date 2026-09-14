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
    """Extract the first JSON object from a model response.

    Small local models often emit raw newlines inside string values or trailing
    prose. We try strict parsing first, then repair common defects.
    """
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()

    for candidate in _json_candidates(text):
        try:
            value = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value

    raise LLMError(f"Model did not return valid JSON: {raw[:300]!r}")


def _json_candidates(text: str):
    """Yield progressively repaired JSON object candidates."""
    yield text
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        snippet = text[start : end + 1]
        yield snippet
        # Repair: escape raw control characters inside strings.
        yield _escape_control_chars(snippet)


def _escape_control_chars(snippet: str) -> str:
    """Escape unescaped newlines/tabs inside JSON string literals."""
    out = []
    in_string = False
    escaped = False
    for ch in snippet:
        if escaped:
            out.append(ch)
            escaped = False
            continue
        if ch == "\\":
            out.append(ch)
            escaped = True
            continue
        if ch == '"':
            in_string = not in_string
            out.append(ch)
            continue
        if in_string and ch in "\r\n\t":
            out.append({ "\n": "\\n", "\r": "\\r", "\t": "\\t" }[ch])
            continue
        out.append(ch)
    return "".join(out)
