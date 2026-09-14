# Agent Forge

A meta-agent that **designs, builds, evaluates, and refines task-specific AI agents**.

Built on researched best practices for agentic systems (Anthropic Engineering + meta-agent research).

## Why

Two goals, one project:

1. **Personal tool** — a working meta-agent that scaffolds, instantiates, evaluates,
   and improves small task-specific agents.
2. **Portfolio project** — a demonstrable implementation of the patterns hiring
   managers look for: orchestrator-workers, evaluator-optimizer, tool engineering,
   and evaluation harnesses.

## Core principles

1. **Simplest thing that works first.** A well-prompted single call beats an agent;
   an agent beats a workflow only when the latency/cost ⇄ accuracy tradeoff pays.
2. **Workflows vs. agents is a deliberate choice.** Predefined paths = predictable;
   model-directed = flexible.
3. **Core loop:** orchestrator-workers (decompose → delegate → synthesize) +
   evaluator-optimizer (generate → evaluate → refine).
4. **Tools are contracts with non-deterministic agents** — prototype → evaluate →
   optimize. Namespaced, context-rich, token-efficient.
5. **Accumulate, don't rebuild.** Proven subagents go into a reusable library.

## Layout

```
agent-forge/
  README.md              <- you are here
  docs/
    architecture.md      <- the build loop + pattern choices
    best-practices.md    <- distilled research with sources
  meta-agent-prompt.md   <- draft system prompt for Forge itself
  forge/                 <- (planned) the builder implementation
  library/               <- (planned) accumulated, proven subagents
```

## Roadmap

- [ ] **v0 — Scaffold:** spec → generates a task-specific prompt + minimal toolset + first eval harness
- [ ] **v0 — Eval harness:** held-out realistic tasks, verifiable outcomes, metrics
- [ ] **v1 — Refine loop:** evaluator feedback drives prompt/tool-spec improvements, bounded iterations
- [ ] **v1 — Library:** reuse accumulated agents; new builders start from proven entries
- [ ] **v2 — Full meta-agent:** Forge system prompt drives the whole loop

## License

MIT
