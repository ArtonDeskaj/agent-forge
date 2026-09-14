# Agent Forge — Architecture

## The build loop

```
SPEC ──► SCAFFOLD ──► EVALUATE ──► REFINE ──► REUSE
                     ▲              │
                     └── not good ──┘   (bounded iterations → human checkpoint)
```

1. **SPEC** — the user states the task in plain language.
2. **SCAFFOLD** — generate for that task:
   - a task-specific system prompt,
   - a minimal, namespaced toolset,
   - an eval harness of realistic, multi-call tasks with verifiable outcomes.
3. **EVALUATE** — run held-out tasks, verify outcomes, collect metrics:
   accuracy, tool-call counts, token consumption, tool errors, runtime.
4. **REFINE** — a separate evaluator critiques; the builder improves prompt and tool
   descriptions. Hard iteration cap, then stop and report.
5. **REUSE** — store proven agents in `library/`.

## Module responsibilities

| Module        | Responsibility |
| ------------- | -------------- |
| `config.py`   | Read provider/model settings from env or CLI |
| `llm.py`      | Minimal OpenAI-compatible chat client with retry |
| `scaffold.py` | SPEC → agent prompt + tools + evals |
| `evaluate.py` | Run evals, score with a verifier, write report |
| `refine.py`   | Evaluator-optimizer loop over prompt + tools |
| `library.py`  | Slug, persist, and load generated agents |
| `build.py`    | CLI + pipeline orchestration |

## Pattern choices

| Situation | Pattern |
|---|---|
| Fixed sequence of steps | Prompt chaining with gates |
| Distinct input categories | Routing |
| Independent subtasks | Parallelization / voting |
| Unknown subtasks, delegation | Orchestrator-workers |
| Clear criteria, iterative craft | Evaluator-optimizer |

Forge's own loop uses **orchestrator-workers** to decompose a build into scaffold/eval
steps, and an **evaluator-optimizer** loop to refine within each iteration.

## Ground truth & checkpoints

- Every iteration consumes real LLM output and real verifier results — never assume.
- Checkpoints: criteria met, iteration cap hit, or a blocker needing human judgment.
- An agent ships only with eval numbers attached.

## Guardrails

- Iteration budgets everywhere; no runaway loops.
- Read-only exploration is free; destructive or external actions ask first.
- No secrets in generated artifacts.
