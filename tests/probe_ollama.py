# -*- coding: utf-8 -*-
"""Probe what Ollama's /v1 endpoint rejects."""
import json
import urllib.request

URL = "http://localhost:11434/v1/chat/completions"


def call(name, payload):
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        URL, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            data = json.loads(r.read().decode())
        msg = data["choices"][0]["message"]["content"]
        print(f"OK   {name}: {msg[:80]!r}")
    except urllib.error.HTTPError as e:
        print(f"FAIL {name}: HTTP {e.code} {e.read().decode('utf-8','replace')[:200]}")
    except Exception as e:
        print(f"FAIL {name}: {e}")


base = [{"role": "user", "content": "Reply with the single word: ok"}]

call("minimal", {"model": "llama3.2", "messages": base})
call("max_tokens", {"model": "llama3.2", "messages": base, "max_tokens": 100})
call("json_mode", {"model": "llama3.2", "messages": base,
                   "response_format": {"type": "json_object"}})
call("temp+max", {"model": "llama3.2", "messages": base,
                  "temperature": 0.2, "max_tokens": 100})
call("temp+max+json", {"model": "llama3.2", "messages": base,
                       "temperature": 0.2, "max_tokens": 100,
                       "response_format": {"type": "json_object"}})
