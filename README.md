# Agent Forge

A meta-agent that **designs, builds, evaluates, and refines task-specific AI agents**.

Point it at a task description; it scaffolds a task-specific system prompt, a minimal
toolset, and an evaluation harness — then iterates until the criteria are met.

Built on researched best practices for agentic systems.

## Status

**v0 — Scaffold.** The builder pipeline is implemented end-to-end and runs against any
LLM provider you configure. See `docs/architecture.md` for the design.

## Install

```bash
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -r requirements.txt
```

## Configure

Agent Forge talks to any OpenAI-compatible chat endpoint (OpenAI, Ollama, vLLM, ...).

```bash
set FORGE_BASE_URL=http://localhost:11434/v1    # Ollama example
set FORGE_API_KEY=ollama
set FORGE_MODEL=llama3.2
```

For OpenAI use `https://api.openai.com/v1` and a real key.

## Use

```bash
# Scaffold an agent for a task
python -m forge.build "Classify incoming support emails by urgency and route them"

# Scaffold + run the evaluation loop
python -m forge.build "..." --evaluate

# Scaffold, evaluate, and refine until criteria pass (bounded)
python -m forge.build "..." --refine --max-iterations 3
```

Output lands in `library/<slug>/`:

```
library/support-email-router/
  spec.json          # the original task spec
  agent.md           # the generated system prompt
  tools.json         # the generated tool definitions
  evals.json         # the generated evaluation harness
  report.md          # latest evaluation report
```

## Layout

```
forge/
  __init__.py
  config.py          # provider + model configuration
  llm.py             # thin OpenAI-compatible client
  build.py           # CLI entrypoint + pipeline orchestration
  scaffold.py        # spec -> agent prompt + tools + evals
  evaluate.py        # run evals, score outcomes, write report
  refine.py          # evaluator-optimizer loop
  library.py         # persist + reuse generated agents
docs/
  architecture.md    # the build loop + pattern choices
  best-practices.md  # distilled research with sources
```

## Roadmap

- [x] **v0 — Scaffold:** spec → task-specific prompt + minimal toolset + first eval harness
- [x] **v0 — Eval harness:** held-out realistic tasks, verifiable outcomes, metrics
- [x] **v1 — Refine loop:** evaluator feedback drives prompt/tool-spec improvements, bounded iterations
- [ ] **v1 — Library reuse:** start new builders from proven library entries
- [ ] **v2 — Full meta-agent:** multi-step orchestration, parallel eval fan-out

## License

MIT
