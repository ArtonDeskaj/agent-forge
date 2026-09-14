"""HARNESS: expand a thin eval set into a substantial, gradeable one.

A meta-agent that tests nothing proves nothing. This step runs a dedicated
pass that grows the auto-generated eval harness to a real size, then grades
the harness itself so a thin or unverifiable set is caught instead of
silently reporting "100% on 1 task".

Everything here is LLM-backed except :func:`grade_harness`, which is pure and
therefore unit-testable.
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher

from .config import Config
from .llm import chat_json

_MIN_SUBSTANTIAL_TASKS = 5
_NEAR_DUPLICATE = 0.85
# Short inputs ("input number 1" vs "input number 2") are trivially similar at the
# character level, so character-ratio checks only apply above this length. Below it
# we compare content words instead.
_MIN_CHARS_FOR_RATIO = 60
# Two inputs must share at least this many content words before word overlap marks
# them as duplicates. Domain boilerplate alone does not count.
_MIN_SHARED_WORDS = 5
# At or above this share of the smaller input's content words, the two inputs are
# considered the same task.
_WORD_OVERLAP = 0.8

_EXPAND_SYSTEM = """You are Forge, a meta-agent that designs EVALUATION HARNESSES for
task-specific AI agents.

You receive a task specification and an existing (usually too small) eval set. Grow it
into a substantial, realistic harness.

Rules:
- Return 8 to 12 tasks total, keeping any existing task that is already good.
- Every task needs: id (t1, t2, ...), input, expected, success_criterion.
- "expected" must be checkable: an exact label/value, or an explicit, concrete
  success criterion a judge can apply without guessing.
- Cover the breadth and the edges: typical cases, boundary cases (empty / ambiguous /
  hostile input), and at least one genuinely hard, multi-step edge case.
- Make every task self-contained: no references to other tasks or to missing context.
- Every task must be DISTINCT: do not repeat an input, do not pad by appending one more
  sentence to a previous task, and do not clone a scenario at greater length.
- Keep each input under 120 words.
- Do not invent tools or context the agent was never given.
Return a JSON object: {"tasks": [...], "verifier_notes": "..."}."""

_EXPAND_FILLER_SYSTEM = """You are Forge, a meta-agent that designs EVALUATION HARNESSES.

The previous attempt returned too few usable tasks. Return AT LEAST 8 COMPLETELY
DIFFERENT tasks for the specification below — different scenarios, different phrasings,
different customer situations.

Rules:
- Never repeat or lightly reword a task that already exists.
- Never pad by appending more sentences to an earlier task.
- Keep each input under 120 words.
Every task needs: id, input, expected, success_criterion.
Return a JSON object: {"tasks": [...], "verifier_notes": "..."}."""


def _normalized_letters(text: str) -> str:
    """Collapse an input to its word content, for duplicate detection."""
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))


def _is_near_duplicate(candidate: str, existing: str) -> bool:
    """True when two inputs are the same task in different clothes.

    Detection is ordered so the cheapest, least ambiguous signals decide first,
    and every fuzzy signal is gated by the amount of evidence available:

    1. identical word content  -> duplicate
    2. one input is a prefix/contained in the other AND at least
       ``_MIN_SHARED_WORDS`` content words are shared -> duplicate
       (a genuinely new sentence appended to a task, not a two-word fragment)
    3. long inputs only: character ratio high AND enough words shared -> duplicate
    4. otherwise: same task only if word overlap of content words is high AND
       at least ``_MIN_SHARED_WORDS`` words are shared

    Short inputs such as "input number 1" vs "input number 2" share only two
    content words, so they are correctly treated as distinct tasks.
    """
    a, b = _normalized_letters(candidate), _normalized_letters(existing)
    if not a or not b:
        return True

    words_a, words_b = set(a.split()), set(b.split())
    shared = words_a & words_b
    enough_shared = len(shared) >= _MIN_SHARED_WORDS

    if a == b:
        return True

    if (a in b or b in a) and enough_shared:
        return True

    if min(len(a), len(b)) >= _MIN_CHARS_FOR_RATIO and enough_shared:
        if SequenceMatcher(None, a, b).ratio() >= _NEAR_DUPLICATE:
            return True

    if not enough_shared:
        return False
    smaller = max(1, min(len(words_a), len(words_b)))
    return (len(shared) / smaller) >= _WORD_OVERLAP


def _valid_task(task: object) -> bool:
    """A task counts only if it is self-contained and gradeable."""
    if not isinstance(task, dict):
        return False
    for field in ("input", "expected"):
        value = task.get(field)
        if not isinstance(value, str) or len(value.strip()) < 3:
            return False
    return True


def _normalize(tasks: list) -> list[dict]:
    """Keep valid, distinct tasks and renumber them deterministically."""
    seen: list[str] = []
    kept: list[dict] = []
    for task in tasks:
        if not _valid_task(task):
            continue
        text = task["input"].strip()
        if any(_is_near_duplicate(text, prev) for prev in seen):
            continue
        seen.append(text)
        kept.append(
            {
                "id": f"t{len(kept) + 1}",
                "input": text,
                "expected": task["expected"].strip(),
                "success_criterion": str(task.get("success_criterion", "")).strip(),
            }
        )
    return kept


def expand_evals(
    config: Config,
    spec: str,
    prompt: str,
    evals: dict,
    *,
    min_tasks: int = _MIN_SUBSTANTIAL_TASKS,
    max_passes: int = 2,
    log=print,
) -> dict:
    """Grow an eval set until it is substantial, or the passes run out."""
    tasks = _normalize(evals.get("tasks", []))
    notes = str(evals.get("verifier_notes", ""))
    user_base = (
        f"Task specification:\n{spec}\n\n"
        f"Agent system prompt:\n{prompt}\n\n"
        f"Existing tasks:\n{tasks}\n\n"
        "Write NEW tasks only: none of the inputs above may be repeated or reworded."
    )

    for attempt in range(max_passes):
        if len(tasks) >= min_tasks:
            break
        system = _EXPAND_SYSTEM if attempt == 0 else _EXPAND_FILLER_SYSTEM
        user = user_base if attempt == 0 else (
            f"Task specification:\n{spec}\n\nExisting tasks:\n{tasks}"
        )
        try:
            grown = chat_json(config, system, user)
        except Exception as exc:  # noqa: BLE001 - keep what we already have
            log(f"      harness expansion pass {attempt + 1} failed: {exc}")
            break
        merged = _normalize(list(grown.get("tasks", [])) + tasks)
        log(f"      harness pass {attempt + 1}: {len(tasks)} -> {len(merged)} tasks")
        tasks = merged
        if grown.get("verifier_notes"):
            notes = str(grown["verifier_notes"])

    if len(tasks) < min_tasks:
        log(f"      harness still thin ({len(tasks)} tasks) after {max_passes} passes")

    return {"tasks": tasks, "verifier_notes": notes}


def grade_harness(evals: dict, *, min_tasks: int = _MIN_SUBSTANTIAL_TASKS) -> dict:
    """Grade the harness itself. Pure; no LLM calls.

    A harness is only trustworthy when it is big enough, every task is
    self-contained, and the expected outcomes are actually checkable.
    """
    tasks = evals.get("tasks", []) or []
    total = len(tasks)
    empty_expected = [t.get("id") for t in tasks if not str(t.get("expected", "")).strip()]
    missing_criterion = [
        t.get("id")
        for t in tasks
        if not str(t.get("success_criterion", "")).strip()
        and len(str(t.get("expected", "")).strip()) > 40
    ]
    unique_inputs = {
        str(t.get("input", "")).strip().lower() for t in tasks if str(t.get("input", "")).strip()
    }
    inputs = [str(t.get("input", "")).strip() for t in tasks if str(t.get("input", "")).strip()]
    near_duplicates = [
        tasks[i].get("id")
        for i in range(len(inputs))
        for j in range(i)
        if _is_near_duplicate(inputs[i], inputs[j])
    ]

    checks = {
        "substantial": total >= min_tasks,
        "expected_present": not empty_expected,
        "criteria_present": not missing_criterion,
        "inputs_unique": len(unique_inputs) == total and not near_duplicates,
    }
    score = sum(1 for ok in checks.values() if ok) / len(checks)

    return {
        "tasks": total,
        "unique_inputs": len(unique_inputs),
        "empty_expected": empty_expected,
        "missing_criterion": missing_criterion,
        "near_duplicates": near_duplicates,
        "checks": checks,
        "score": round(score, 3),
        "ok": all(checks.values()),
    }


def harness_markdown(grade: dict) -> str:
    """Render a harness grade as markdown."""
    lines = [
        "## Harness grade",
        "",
        f"- **Tasks:** {grade['tasks']} (unique inputs: {grade['unique_inputs']})",
        f"- **Score:** {grade['score']:.0%}",
        f"- **Substantial (>= {_MIN_SUBSTANTIAL_TASKS} tasks):** "
        f"{'yes' if grade['checks']['substantial'] else 'NO'}",
        f"- **Every task has an expected outcome:** "
        f"{'yes' if grade['checks']['expected_present'] else 'NO'}",
        f"- **Every free-form task has a success criterion:** "
        f"{'yes' if grade['checks']['criteria_present'] else 'NO'}",
        f"- **Inputs unique:** {'yes' if grade['checks']['inputs_unique'] else 'NO'}",
    ]
    for label, ids in (
        ("Tasks with no expected outcome", grade["empty_expected"]),
        ("Tasks missing a success criterion", grade["missing_criterion"]),
        ("Near-duplicate tasks", grade["near_duplicates"]),
    ):
        if ids:
            lines.append(f"- **{label}:** {', '.join(str(i) for i in ids)}")
    lines.append("")
    return "\n".join(lines)
