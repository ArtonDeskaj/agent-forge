"""Tests for the parts of Agent Forge that do not need an LLM.

Run: python -m pytest tests/ -q     (or: python tests/test_core.py)
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from forge.library import slugify  # noqa: E402
from forge.llm import LLMError, parse_json_object  # noqa: E402
from forge.evaluate import report_markdown  # noqa: E402
from forge.refine import is_clean_prompt  # noqa: E402
from forge.harness import (  # noqa: E402
    expand_evals,
    grade_harness,
    harness_markdown,
)
from forge.config import Config  # noqa: E402


def test_slugify_basic() -> None:
    assert slugify("Classify incoming support emails by urgency") == (
        "classify-incoming-support-emails-urgency"
    )


def test_slugify_strips_stopwords_and_caps_words() -> None:
    slug = slugify("A tool for the analysis of and reporting on things", max_words=3)
    assert slug == "tool-analysis-reporting"
    assert slug.count("-") == 2


def test_slugify_empty_is_safe() -> None:
    assert slugify("!!!") == "agent"


def test_parse_json_plain() -> None:
    assert parse_json_object('{"a": 1}') == {"a": 1}


def test_parse_json_fenced() -> None:
    assert parse_json_object('```json\n{"a": 1}\n```') == {"a": 1}


def test_parse_json_with_prose() -> None:
    assert parse_json_object('Sure! Here you go: {"a": 1} Hope that helps.') == {"a": 1}


def test_parse_json_repairs_raw_newlines() -> None:
    # Small models often emit literal newlines inside string values.
    raw = '{"prompt": "line one\nline two"}'
    assert parse_json_object(raw) == {"prompt": "line one\nline two"}


def test_parse_json_rejects_non_object() -> None:
    try:
        parse_json_object("[1, 2, 3]")
    except LLMError:
        return
    raise AssertionError("expected LLMError for a JSON array")


def test_report_markdown_contains_metrics() -> None:
    metrics = {
        "total": 2,
        "passed": 1,
        "accuracy": 0.5,
        "mean_score": 0.5,
        "seconds": 1.23,
        "results": [
            {"id": "t1", "pass": True, "score": 1.0, "seconds": 0.4, "reason": "ok"},
            {"id": "t2", "pass": False, "score": 0.0, "seconds": 0.8, "reason": "bad | pipe"},
        ],
    }
    md = report_markdown("demo", metrics)
    assert "Accuracy:** 50%" in md
    assert "| t1 | yes |" in md
    assert "bad / pipe" in md  # pipes escaped for the table


def test_config_from_env_defaults() -> None:
    cfg = Config.from_env()
    assert cfg.base_url.startswith("http")
    assert cfg.describe().endswith("(api key: missing)")


def test_config_strips_trailing_slash() -> None:
    cfg = Config.from_env(base_url="http://x/v1/")
    assert cfg.base_url == "http://x/v1"


def test_config_max_tokens_roomy_by_default() -> None:
    # Small local models truncate JSON below ~4096; that was the original bug.
    cfg = Config.from_env()
    assert cfg.max_tokens >= 4096


def test_grade_harness_flags_thin_set() -> None:
    thin = {
        "tasks": [
            {"id": "t1", "input": "one", "expected": "high", "success_criterion": "x"}
        ]
    }
    grade = grade_harness(thin)
    assert grade["ok"] is False
    assert grade["checks"]["substantial"] is False
    assert grade["score"] < 1.0
    assert "NO" in harness_markdown(grade)


def test_grade_harness_accepts_substantial_set() -> None:
    good = {
        "tasks": [
            {
                "id": f"t{i}",
                "input": f"input number {i}",
                "expected": "high" if i % 2 else "low",
                "success_criterion": "classify correctly",
            }
            for i in range(1, 7)
        ]
    }
    grade = grade_harness(good)
    assert grade["ok"] is True
    assert grade["score"] == 1.0
    assert grade["unique_inputs"] == 6
    assert "Harness grade" in harness_markdown(grade)


def test_grade_harness_reports_empty_expected_and_missing_criterion() -> None:
    weak = {
        "tasks": [
            *[
                {
                    "id": f"t{i}",
                    "input": f"distinct input {i}",
                    "expected": "ok",
                    "success_criterion": "x",
                }
                for i in range(1, 5)
            ],
            {"id": "t5", "input": "distinct input 5", "expected": "   "},
            {
                "id": "t6",
                "input": "distinct input 6",
                "expected": "A long free-form expected outcome " * 3,
            },
        ]
    }
    grade = grade_harness(weak)
    assert grade["empty_expected"] == ["t5"]
    assert grade["missing_criterion"] == ["t6"]
    assert grade["ok"] is False


def test_grade_harness_detects_duplicate_inputs() -> None:
    dupes = {
        "tasks": [
            {
                "id": f"t{i}",
                "input": "the SAME input",
                "expected": "ok",
                "success_criterion": "x",
            }
            for i in range(1, 6)
        ]
    }
    grade = grade_harness(dupes)
    assert grade["unique_inputs"] == 1
    assert grade["checks"]["inputs_unique"] is False


def test_expand_evals_keeps_original_when_expansion_fails() -> None:
    class Boom:
        pass

    orig = {
        "tasks": [
            {"id": "t1", "input": "hello there", "expected": "low", "success_criterion": "c"}
        ],
        "verifier_notes": "keep me",
    }
    out = expand_evals(Boom(), "spec", "prompt", orig, log=lambda *_: None)
    assert out["tasks"][0]["input"] == "hello there"
    assert out["verifier_notes"] == "keep me"


def test_is_clean_prompt_rejects_leaked_review_notes() -> None:
    clean = (
        "You classify support emails into High, Medium or Low urgency. "
        "Use High for outages and locked accounts, Medium for degraded service, "
        "Low for cosmetic requests. Return JSON."
    )
    assert is_clean_prompt(clean) is True

    for leaked in (
        clean + "\nFindings: [t2] wrong level",
        clean + "\nCritic summary: the agent fails",
        clean + "\niteration 1: accuracy 56%",
        "too short",
        "",
    ):
        assert is_clean_prompt(leaked) is False, leaked[:40]


def test_expand_evals_merges_and_dedupes() -> None:
    generated = [
        {
            "id": "x1",
            "input": "new case",
            "expected": "high",
            "success_criterion": "classify",
        },
        {
            "id": "x2",
            "input": "hello there",
            "expected": "low",
            "success_criterion": "classify",
        },
        {"id": "x3", "input": "", "expected": "high", "success_criterion": "c"},
    ]
    calls = {"n": 0}

    class FakeCfg:
        pass

    import forge.harness as harness_mod

    real_chat_json = harness_mod.chat_json
    harness_mod.chat_json = lambda *a, **k: {
        "tasks": generated,
        "verifier_notes": "expanded",
    }
    try:
        orig = {
            "tasks": [
                {
                    "id": "t1",
                    "input": "hello there",
                    "expected": "low",
                    "success_criterion": "c",
                }
            ],
            "verifier_notes": "orig",
        }
        out = expand_evals(FakeCfg(), "spec", "prompt", orig, log=lambda *_: None)
    finally:
        harness_mod.chat_json = real_chat_json

    inputs = [t["input"] for t in out["tasks"]]
    assert "hello there" in inputs
    assert len(inputs) == len(set(inputs))  # the duplicate was dropped
    assert all(t["input"] for t in out["tasks"])  # the empty one was dropped
    assert all(t["id"].startswith("t") for t in out["tasks"])  # renumbered
    assert out["verifier_notes"] == "expanded"
    assert calls["n"] == 0


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for fn in tests:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"FAIL {fn.__name__}: {exc}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
