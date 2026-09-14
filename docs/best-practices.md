# AI Agent Building — Best Practices Reference

Collected 2026-09-14 for Arton (building AI agents / an AI that helps make AI agents).

Primary sources: Anthropic Engineering (authoritative), arXiv meta-agent research.

## Core principle (Anthropic — "Building effective agents")

- **Always find the simplest solution. Only add complexity when needed.** Agentic systems trade latency and cost for task performance. Often a single optimized LLM call with retrieval + in-context examples is enough. Many teams over-engineer.

## Workflows vs Agents (distinct architectural patterns)

- **Workflow:** LLMs/tools orchestrated through predefined code paths (predictable, consistent).
- **Agent:** LLM dynamically directs its own process and tool use; controls *how* it accomplishes the task (flexible, model-driven decision-making).
- Use agents only when you need flexibility + model-driven decisions at scale.

## The 5 composable workflow patterns (in increasing complexity)

1. **Prompt chaining** — decompose into fixed sequence; programmatic "gates" check intermediate steps. Best when task cleanly splits into fixed subtasks. (e.g. outline → check → write)
2. **Routing** — classify input, direct to specialized handler. Best for distinct categories with separate optimized prompts. (e.g. route easy Qs to cheap model, hard Qs to capable model)
3. **Parallelization** — two flavors:
   - *Sectioning:* split into independent subtasks run in parallel (each consideration gets focused attention).
   - *Voting:* run same task multiple times for diverse outputs (e.g. code vulnerability review).
4. **Orchestrator-workers** — central LLM dynamically breaks down tasks, delegates to workers, synthesizes results. Key difference from parallelization: subtasks NOT predefined, determined from input. (e.g. multi-file coding)
5. **Evaluator-optimizer** — one LLM generates, another evaluates + gives feedback in a loop. Best with clear evaluation criteria + measurable iterative improvement. (e.g. literary translation, iterative search)

## Agents (autonomous)

- Start from user command/discussion → plan and operate independently → return to human for info/judgement at checkpoints.
- **Crucial: gain "ground truth" from the environment at each step** (tool results, code execution) to assess progress. Return to human at checkpoints or blockers.
- Emerging as LLMs mature in: understanding complex inputs, reasoning/planning, **reliable tool use**, error recovery.

## Frameworks

- Frameworks (Claude Agent SDK, AWS Strands, Rivet, Vellum) ease getting started but add abstraction that obscures prompts/responses and complicates debugging.
- **Start with LLM APIs directly**, understand the underlying code, before adopting a framework.

## Writing effective tools (Anthropic — for agents)

- Tools = contract between deterministic systems and non-deterministic agents. **Design them FOR agents, not like developer APIs.**
- Loop: prototype → evaluate → improve (ideally with an agent helping write/optimize).

### Tool evaluation
- Generate lots of eval tasks grounded in real-world uses (multi-call, dozens of tool calls). Avoid superficial sandbox tasks.
- Strong task example: "Customer 9182 charged 3×; find logs, check other customers affected."
- Pair each prompt with verifiable outcome (exact string match → Claude judge). Avoid overly strict verifiers.
- Track: accuracy, runtime, tool-call count, token consumption, tool errors.
- Use reasoning/blocks + interleaved thinking to probe WHY agents do/don't call tools.

### 5 principles for high-quality tools
1. **Choose the right tools** (and which NOT to implement).
2. **Namespacing** tools to define clear functional boundaries.
3. **Return meaningful context** from tools back to agents.
4. **Optimize tool responses for token efficiency.**
5. **Prompt-engineer tool descriptions and specs.**

## Meta-agent / "agent that makes agents" research

- **ADAS (Automated Design of Agentic Systems)** — arXiv 2408.08435: meta-agent proposes/discovered agent programs; evolutionary search.
- **Alita-G** — arXiv 2510.23601: self-evolving generative agent for agent generation.
- **AgentFactory** — arXiv 2603.18000: self-evolving framework through executable subagent accumulation + reuse.
- **Autogenesis** — arXiv 2604.15034: self-evolving agent protocol.
- Common themes: self-designing meta-agents that **construct, instantiate, refine** task-specific agents; accumulate + reuse subagents; evaluator-optimizer loops.
- Related Anthropic: **"Writing effective tools ... using AI agents"** = an actual working example of an AI optimizing its own tools.

## Practical implications for an "AI that helps make AI agents"

1. Prefer simple, composable patterns over monolithic frameworks.
2. Make the meta-agent's tools great: prototype → eval → optimize loop; return rich context, token-efficient.
3. Use orchestrator-workers + evaluator-optimizer as the core loop for building/refining sub-agents.
4. Ground every step with real tool output; checkpoints back to the human.
5. Treat sub-agents as reusable, accumulate them (AgentFactory pattern).

## Links
- https://www.anthropic.com/engineering/building-effective-agents
- https://www.anthropic.com/engineering/writing-tools-for-agents
- https://www.anthropic.com/engineering/effective-context-engineering-for-agents
- https://arxiv.org/pdf/2408.08435 (ADAS)
- https://arxiv.org/html/2510.23601v1 (Alita-G)
- https://arxiv.org/pdf/2603.18000 (AgentFactory)
- https://arxiv.org/pdf/2604.15034 (Autogenesis)
