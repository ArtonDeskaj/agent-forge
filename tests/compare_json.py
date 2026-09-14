# -*- coding: utf-8 -*-
"""Compare JSON reliability across local models."""
import json
import urllib.request

URL = "http://localhost:11434/v1/chat/completions"
PROMPT = (
    "Design a system prompt for an agent that classifies support emails by urgency. "
    'Return JSON: {"prompt": "<the full system prompt>"}'
)


def try_model(model: str, max_tokens: int) -> str:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": PROMPT}],
        "temperature": 0.2,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
    }
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        URL, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            data = json.loads(r.read().decode())
        content = data["choices"][0]["message"]["content"]
        try:
            obj = json.loads(content)
            ok = "prompt" in obj
            return f"OK-JSON prompt={ok} len={len(content)}"
        except json.JSONDecodeError as e:
            return f"BAD-JSON ({e}) raw_tail={content[-60:]!r}"
    except Exception as e:
        return f"ERROR {e}"


for model in ["qwen2.5:3b", "llama3.2"]:
    for mt in [1024, 4096]:
        print(f"{model:12} max_tokens={mt:5} -> {try_model(model, mt)}")
