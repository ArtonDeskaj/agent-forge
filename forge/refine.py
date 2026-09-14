"""REFINE step: evaluator-optimizer loop over the agent prompt and tool specs."""

from __future__ import annotations

from .config import Config
from .evaluate import evaluate
from .llm import chat_json

_CRITIC_SYSTEM = """You are a critical evaluator reviewing an AI agent's performance.

Given the agent's system prompt, its toolset, and a failed-evaluation report, identify
the highest-leverage improvements. Be specific and terse.

Return a JSON object:
{"findings": [{"issue": "...", "fix": "..."}], "summary": "..."}."""

_IMPROVE_SYSTEM = """You are Forge, a meta-agent improving a task-specific AI agent.

Apply the critic's findings to the agent's SYSTEM PROMPT. Preserve what already works.
Do not add complexity the task does not need.

The returned prompt must be a clean, self-contained system prompt. It must NOT contain
critic notes, findings, review commentary, lists of failing test ids, or meta-discussion
about the prompt itself.

Return a JSON object: {"prompt": "<the improved system prompt>"}."""

_FIX_SYSTEM = """You are Forge, a meta-agent repairing a task-specific AI agent.

The agent still fails specific evaluation tasks. Fix the SYSTEM PROMPT so those cases are
handled, by STATING THE DECISION RULE in general terms (the boundary between levels).

Strict rules:
- Never copy concrete task inputs, test ids, or example answers into the prompt.
- Never reference "the tests", "the evaluator", "the findings", or previous iterations.
- No meta-commentary, no review notes, no numbered lists of failures.
- Keep the output contract and everything that already works intact.

Return a JSON object: {"prompt": "<the complete, clean system prompt>"}."""

_UNTRUSTED_MARKERS = (
    "Findings:",
    "Critic summary:",
    "iteration",
    "expected outcome:",
    "success_criterion",
)


def critic(config: Config, spec: str, prompt: str, tools: dict, metrics: dict) -> dict:
    """Ask for concrete improvements based on the evaluation report."""
    failures = [r for r in metrics["results"] if not r["pass"]]
    failure_text = "\n".join(
        f"- [{r['id']}] expected: {str(r.get('expected', ''))[:120]} | "
        f"got: {str(r.get('answer', ''))[:120]} | {r.get('reason', '')}"
        for r in failures
    ) or "(none failed)"
    user = (
        f"Task specification:\n{spec}\n\n"
        f"Agent system prompt:\n{prompt}\n\n"
        f"Toolset:\n{tools.get('tools', [])}\n\n"
        f"Accuracy: {metrics['accuracy']:.0%} ({metrics['passed']}/{metrics['total']})\n\n"
        f"Failures:\n{failure_text}"
    )
    return chat_json(config, _CRITIC_SYSTEM, user)


def improve(config: Config, prompt: str, findings: dict) -> str:
    """Rewrite the prompt from the critic's findings."""
    user = (
        f"Current system prompt:\n{prompt}\n\n"
        f"Critic summary:\n{findings.get('summary', '')}\n\n"
        f"Findings:\n{findings.get('findings', [])}"
    )
    return chat_json(config, _IMPROVE_SYSTEM, user)["prompt"]


def is_clean_prompt(prompt: str) -> bool:
    """Reject rewritten prompts that leaked review notes into the agent's instructions."""
    if not isinstance(prompt, str) or len(prompt.strip()) < 40:
        return False
    lowered = prompt.lower()
    return not any(marker.lower() in lowered for marker in _UNTRUSTED_MARKERS)


def repair(config: Config, prompt: str, metrics: dict, findings: dict) -> str | None:
    """One targeted repair attempt for the still-failing cases.

    Returns the fixed prompt, or ``None`` when the rewrite was rejected, empty, or
    leaked evaluator text. Callers must keep the previous prompt on ``None``.
    """
    failures = [r for r in metrics["results"] if not r["pass"]]
    failure_text = "\n".join(
        f"- a {r.get('reason', '')} case; the agent answered {str(r.get('answer', ''))[:200]}"
        for r in failures
    )
    user = (
        f"Current system prompt:\n{prompt}\n\n"
        f"Critic guidance:\n{findings.get('summary', '')}\n"
        f"{findings.get('findings', [])}\n\n"
        f"Cases still handled wrongly:\n{failure_text}"
    )
    try:
        candidate = chat_json(config, _FIX_SYSTEM, user)["prompt"]
    except Exception as exc:  # noqa: BLE001 - a failed repair must not abort the loop
        return None
    if not is_clean_prompt(candidate) or candidate.strip() == prompt.strip():
        return None
    return candidate


def refine_loop(
    config: Config,
    spec: str,
    prompt: str,
    tools: dict,
    evals: dict,
    *,
    max_iterations: int = 3,
    target_accuracy: float = 0.9,
    log=print,
) -> tuple[str, dict, list[dict]]:
    """Evaluate, critique, improve — until target met or the cap is hit."""
    history: list[dict] = []
    metrics = evaluate(config, prompt, evals)
    history.append({"iteration": 0, "accuracy": metrics["accuracy"]})
    log(f"  iteration 0: accuracy {metrics['accuracy']:.0%}")

    for i in range(1, max_iterations + 1):
        if metrics["accuracy"] >= target_accuracy:
            log(f"  target {target_accuracy:.0%} reached — stopping")
            break
        findings = critic(config, spec, prompt, tools, metrics)
        candidate = repair(config, prompt, metrics, findings)
        if candidate is None:
            log(f"  iteration {i}: rewrite rejected, keeping previous prompt")
            history.append({"iteration": i, "accuracy": metrics["accuracy"], "rejected": True})
            break
        candidate_metrics = evaluate(config, candidate, evals)
        if candidate_metrics["accuracy"] < metrics["accuracy"]:
            log(
                f"  iteration {i}: rejected regression "
                f"({metrics['accuracy']:.0%} -> {candidate_metrics['accuracy']:.0%})"
            )
            history.append({"iteration": i, "accuracy": metrics["accuracy"], "rejected": True})
            break
        prompt = candidate
        metrics = candidate_metrics
        history.append({"iteration": i, "accuracy": metrics["accuracy"]})
        log(f"  iteration {i}: accuracy {metrics['accuracy']:.0%}")

    return prompt, metrics, history
