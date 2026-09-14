"""SCAFFOLD step: turn a task spec into prompt + tools + evals.

Follows the researched pattern: simplest design that works, namespaced tools,
realistic multi-call evaluation tasks with verifiable outcomes.
"""

from __future__ import annotations

from .config import Config
from .llm import chat_json

_PROMPT_SYSTEM = """You are Forge, a meta-agent that designs task-specific AI agents.

Given a task specification, write the SYSTEM PROMPT for an agent that performs it.

Rules:
- Prefer the simplest design that works. If a single careful prompt suffices, say so in
  the prompt itself and do not invent unnecessary machinery.
- The prompt must be concrete: role, objective, required procedure, output contract, a
  decision rule for ambiguous or boundary cases, and how to handle failure.
- State decision rules in GENERAL terms (e.g. "treat confirmed data loss as high").
  Never embed specific test inputs, test ids, or worked examples as rules.
- Include a short "Ground truth" rule: rely on real tool output, never assume.
- No fluff, no placeholders, no secrets, no commentary about this design process.
Return a JSON object: {"prompt": "<the full system prompt>"}."""

_TOOLS_SYSTEM = """You are Forge, a meta-agent that designs task-specific AI agents.

Given a task specification and the agent's system prompt, propose the MINIMAL toolset
the agent needs.

Rules:
- Only tools that genuinely serve the task. Fewer is better.
- Namespace names by domain, e.g. email.search, email.draft.
- Each tool returns meaningful context and stays token-efficient in its description.
- If the task needs no external tools, return an empty list and say why in "notes".
Return a JSON object:
{"tools": [{"name": "...", "description": "...", "parameters": {"type": "object", "properties": {...}, "required": [...]}}], "notes": "..."}."""

_EVALS_SYSTEM = """You are Forge, a meta-agent that designs task-specific AI agents.

Given a task specification, design an EVALUATION HARNESS: realistic tasks grounded in
real-world use, each paired with a verifiable expected outcome.

Rules:
- 8 to 15 tasks. Strong tasks require multiple steps or tool calls; no toy sandboxes.
- Every task must be COMPLETELY DISTINCT: different scenario, different wording,
  different customer situation. Never repeat an input, never pad by appending another
  sentence to an earlier task, never clone a scenario at greater length.
- Every task needs an "expected" field a verifier can check (exact value, or an explicit
  success criterion a judge can apply).
- Keep every input under 120 words. Use realistic length, not maximal length.
- Avoid over-specifying the exact tool-call path; allow valid alternatives.
- Include at least one genuinely hard edge case.
Return a JSON object:
{"tasks": [{"id": "t1", "input": "...", "expected": "...", "success_criterion": "..."}],
 "verifier_notes": "..."}."""


def scaffold(config: Config, spec: str) -> dict:
    """Run the full scaffold step for a task description."""
    prompt_obj = chat_json(config, _PROMPT_SYSTEM, f"Task specification:\n{spec}")
    prompt = prompt_obj["prompt"]

    tools_obj = chat_json(
        config, _TOOLS_SYSTEM, f"Task specification:\n{spec}\n\nSystem prompt:\n{prompt}"
    )

    evals_obj = chat_json(
        config, _EVALS_SYSTEM, f"Task specification:\n{spec}\n\nSystem prompt:\n{prompt}"
    )

    from .harness import _normalize

    return {
        "prompt": prompt,
        "tools": {
            "tools": tools_obj.get("tools", []),
            "notes": tools_obj.get("notes", ""),
        },
        "evals": {
            "tasks": _normalize(evals_obj.get("tasks", [])),
            "verifier_notes": evals_obj.get("verifier_notes", ""),
        },
    }
