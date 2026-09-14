# Agent Forge — Architecture

## The build loop

```
SPEC ──► SCAFFOLD ──► EVALUATE ──► REFINE ──► REUSE
                     ▲              │
                     └── not good ──┘   (bounded iterations → human checkpoint)
```

1. **SPEC** — user states the task in plain language. If ambiguous: one focused
   clarifying question, no guessing.
2. **SCAFFOLD** — generate for the task:
   - a task-specific system prompt (examples in, no fluff),
   - a minimal, namespaced toolset (each tool: meaningful context back, token-efficient,
     well-descriptionered spec),
   - a first eval harness: 10–30 realistic tasks grounded in real-world use, each with a
     verifiable outcome. Strong tasks require multiple tool calls. No toy sandboxes.
3. **EVALUATE** — run held-out tasks; verify outcomes; collect per-task and aggregate:
   accuracy, tool-call counts, token consumption, tool errors, runtime.
4. **REFINE** — a separate evaluator agent critiques (what worked, what's contradictory,
   what's missing); builder improves prompt + tool descriptions. Loop with a hard
   iteration cap, then stop and report to the human.
5. **REUSE** — store proven agents in `library/`; future builds start from library
   entries instead of scratch.

## Pattern choices (Anthropic taxonomy)

| Situation | Pattern |
|---|---|
| Fixed sequence of steps | Prompt chaining with gates |
| Distinct input categories | Routing (cheap model for easy, strong model for hard) |
| Independent subtasks | Parallelization (sectioning) / voting for confidence |
| Unknown subtasks, delegation | Orchestrator-workers |
| Clear criteria, iterative craft | Evaluator-optimizer |

Forge's own builder loop uses **orchestrator-workers** (decompose the build into
scaffold/eval/refine workers) over **evaluator-optimizer** (refine until criteria).

## Ground truth & checkpoints

- Every loop iteration consumes **real tool output** — never assume.
- Human checkpoints: criteria met, iteration cap hit, or blocker needing judgement.
- Evidence before claims: an agent ships only with eval numbers.

## Guardrails

- Exploration/read-only: free.
- Destructive or external actions: ask first.
- Iteration budgets everywhere; no runaway loops.
