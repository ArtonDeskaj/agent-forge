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

Return a JSON object: {"prompt": "<the improved system prompt>"}."""


def critic(config: Config, spec: str, prompt: str, tools: dict, metrics: dict) -> dict:
    """Ask for concrete improvements based on the evaluation report."""
    failures = [r for r in metrics["results"] if not r["pass"]]
    failure_text = "\n".join(
        f"- [{r['id']}] expected: {r['expected'][:120]} | got: {r['answer'][:120]} | {r['reason']}"
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
        prompt = improve(config, prompt, findings)
        metrics = evaluate(config, prompt, evals)
        history.append({"iteration": i, "accuracy": metrics["accuracy"]})
        log(f"  iteration {i}: accuracy {metrics['accuracy']:.0%}")

    return prompt, metrics, history
