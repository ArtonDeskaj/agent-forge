"""Slugging and persistence for generated agents."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIBRARY = ROOT / "library"


def slugify(text: str, max_words: int = 6) -> str:
    """Turn a task description into a filesystem-safe slug."""
    words = re.findall(r"[a-z0-9]+", text.lower())
    stop = {"a", "an", "the", "for", "to", "of", "and", "in", "on", "with", "by"}
    kept = [w for w in words if w not in stop][:max_words]
    return "-".join(kept) or "agent"


def agent_dir(slug: str) -> Path:
    return LIBRARY / slug


def save_agent(
    slug: str,
    *,
    spec: dict,
    prompt: str,
    tools: dict,
    evals: dict,
) -> Path:
    """Persist every generated artifact for an agent."""
    target = agent_dir(slug)
    target.mkdir(parents=True, exist_ok=True)
    (target / "spec.json").write_text(
        json.dumps(spec, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (target / "agent.md").write_text(prompt, encoding="utf-8")
    (target / "tools.json").write_text(
        json.dumps(tools, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (target / "evals.json").write_text(
        json.dumps(evals, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return target


def load_agent(slug: str) -> dict:
    """Load a previously generated agent."""
    target = agent_dir(slug)
    if not target.exists():
        raise FileNotFoundError(f"No agent named {slug!r} in {LIBRARY}")

    def read_json(name: str) -> dict:
        return json.loads((target / name).read_text(encoding="utf-8"))

    return {
        "slug": slug,
        "dir": target,
        "spec": read_json("spec.json"),
        "prompt": (target / "agent.md").read_text(encoding="utf-8"),
        "tools": read_json("tools.json"),
        "evals": read_json("evals.json"),
    }


def list_agents() -> list[str]:
    """Return the slugs of every generated agent."""
    if not LIBRARY.exists():
        return []
    return sorted(p.name for p in LIBRARY.iterdir() if p.is_dir())
