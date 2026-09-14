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
