"""EVALUATE step: run the generated agent against its eval harness.

Uses an LLM judge when the task has a free-form expected outcome, and records
accuracy plus token/tool metrics per the researched metrics set.
"""

from __future__ import annotations

import time

from .config import Config
from .llm import chat, chat_json
from .scaffold import _PROMPT_SYSTEM  # reuse the builder persona

_JUDGE_SYSTEM = """You are a strict but fair evaluator. You compare an agent's answer to
an expected outcome for a task.

Judge substance, not formatting. Accept correct answers phrased differently. Reject
answers that miss required facts, invent facts, or ignore the task.

Return a JSON object: {"pass": true|false, "score": 0.0-1.0, "reason": "<short>"}."""


def run_task(config: Config, prompt: str, task: dict) -> str:
    """Have the built agent attempt one evaluation task.

    Provider failures are isolated to the single task so one bad request cannot
    abort the whole evaluation run. The task input is bounded so a small local
    model's context window is never the reason the run dies.
    """
    user = str(task["input"])[:6000]
    try:
        return chat(config, prompt, user, retries=0)
    except Exception as exc:  # noqa: BLE001
        return f"[task failed: {exc}]"


def judge(config: Config, task: dict, answer: str) -> dict:
    """Score one answer against the task's expected outcome."""
    user = (
        f"Task input:\n{task['input']}\n\n"
        f"Expected outcome:\n{task.get('expected', '')}\n\n"
        f"Success criterion:\n{task.get('success_criterion', '')}\n\n"
        f"Agent answer:\n{answer}"
    )
    try:
        return chat_json(config, _JUDGE_SYSTEM, user)
    except Exception as exc:  # noqa: BLE001 - degrade to a failed judgment
        return {"pass": False, "score": 0.0, "reason": f"judge error: {exc}"}


def evaluate(config: Config, prompt: str, evals: dict) -> dict:
    """Run every eval task and aggregate the results."""
    results = []
    started = time.perf_counter()

    for task in evals.get("tasks", []):
        t0 = time.perf_counter()
        answer = run_task(config, prompt, task)
        verdict = judge(config, task, answer)
        results.append(
            {
                "id": task.get("id"),
                "input": task["input"],
                "answer": answer,
                "expected": task.get("expected", ""),
                "pass": bool(verdict.get("pass")),
                "score": float(verdict.get("score", 0.0)),
                "reason": verdict.get("reason", ""),
                "seconds": round(time.perf_counter() - t0, 2),
            }
        )

    total = len(results)
    passed = sum(1 for r in results if r["pass"])
    mean_score = (sum(r["score"] for r in results) / total) if total else 0.0

    return {
        "total": total,
        "passed": passed,
        "accuracy": (passed / total) if total else 0.0,
        "mean_score": round(mean_score, 3),
        "seconds": round(time.perf_counter() - started, 2),
        "results": results,
    }


def report_markdown(slug: str, metrics: dict) -> str:
    """Render an evaluation report."""
    lines = [
        f"# Evaluation report — {slug}",
        "",
        f"- **Tasks:** {metrics['total']}",
        f"- **Passed:** {metrics['passed']}",
        f"- **Accuracy:** {metrics['accuracy']:.0%}",
        f"- **Mean judge score:** {metrics['mean_score']}",
        f"- **Wall time:** {metrics['seconds']}s",
        "",
        "## Per task",
        "",
        "| ID | Pass | Score | Seconds | Reason |",
        "|----|------|-------|---------|--------|",
    ]
    for r in metrics["results"]:
        reason = (r["reason"] or "").replace("|", "/")[:80]
        lines.append(
            f"| {r['id']} | {'yes' if r['pass'] else 'no'} | {r['score']:.2f} | "
            f"{r['seconds']} | {reason} |"
        )
    lines.append("")
    return "\n".join(lines)
