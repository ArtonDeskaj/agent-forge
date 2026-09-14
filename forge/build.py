"""CLI entrypoint and pipeline orchestration for Agent Forge."""

from __future__ import annotations

import argparse
import sys

from . import __version__
from .config import Config
from .evaluate import evaluate, report_markdown
from .library import list_agents, load_agent, save_agent, slugify
from .refine import refine_loop
from .scaffold import scaffold


def _build(args: argparse.Namespace) -> int:
    config = Config.from_env(args.base_url, args.api_key, args.model)
    print(f"Agent Forge v{__version__} — provider: {config.describe()}")

    slug = args.name or slugify(args.spec)
    print(f"Task: {args.spec}")
    print(f"Agent slug: {slug}\n")

    print("[1/4] Scaffolding agent prompt, tools, and eval harness ...")
    built = scaffold(config, args.spec)
    tool_count = len(built["tools"]["tools"])
    task_count = len(built["evals"]["tasks"])
    print(f"      prompt: {len(built['prompt'])} chars, "
          f"tools: {tool_count}, eval tasks: {task_count}")

    target = save_agent(
        slug,
        spec={"description": args.spec},
        prompt=built["prompt"],
        tools=built["tools"],
        evals=built["evals"],
    )
    print(f"[2/4] Saved to {target}")

    if not (args.evaluate or args.refine):
        print("\nDone. Re-run with --evaluate or --refine to test the agent.")
        return 0

    print("[3/4] Running evaluation ...")
    if args.refine:
        prompt, metrics, history = refine_loop(
            config,
            args.spec,
            built["prompt"],
            built["tools"],
            built["evals"],
            max_iterations=args.max_iterations,
            target_accuracy=args.target_accuracy,
        )
        # persist the refined prompt
        save_agent(
            slug,
            spec={"description": args.spec},
            prompt=prompt,
            tools=built["tools"],
            evals=built["evals"],
        )
    else:
        metrics = evaluate(config, built["prompt"], built["evals"])
        history = [{"iteration": 0, "accuracy": metrics["accuracy"]}]

    print(f"[4/4] Accuracy: {metrics['accuracy']:.0%} "
          f"({metrics['passed']}/{metrics['total']}), "
          f"mean score {metrics['mean_score']}")

    report_path = target / "report.md"
    report_path.write_text(report_markdown(slug, metrics), encoding="utf-8")
    print(f"      Report: {report_path}")
    if len(history) > 1:
        trail = " -> ".join(f"{h['accuracy']:.0%}" for h in history)
        print(f"      Accuracy trail: {trail}")
    return 0


def _list(_args: argparse.Namespace) -> int:
    agents = list_agents()
    if not agents:
        print("No agents generated yet.")
        return 0
    print("Generated agents:")
    for slug in agents:
        print(f"  - {slug}")
    return 0


def _show(args: argparse.Namespace) -> int:
    agent = load_agent(args.slug)
    print(f"# {agent['slug']}\n")
    print(f"Spec: {agent['spec'].get('description', '')}\n")
    print("## System prompt\n")
    print(agent["prompt"])
    print("\n## Tools\n")
    for tool in agent["tools"].get("tools", []):
        print(f"- {tool.get('name')}: {tool.get('description', '')[:100]}")
    print(f"\n## Eval tasks: {len(agent['evals'].get('tasks', []))}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="forge", description="Agent Forge — build task-specific AI agents."
    )
    parser.add_argument("--version", action="version", version=f"Agent Forge {__version__}")
    parser.add_argument("--base-url", help="OpenAI-compatible base URL")
    parser.add_argument("--api-key", help="API key (prefer FORGE_API_KEY)")
    parser.add_argument("--model", help="Model id")

    sub = parser.add_subparsers(dest="command")

    build = sub.add_parser("build", help="Scaffold an agent from a task description")
    build.add_argument("spec", help="Plain-language task description")
    build.add_argument("--name", help="Explicit agent slug (defaults to derived)")
    build.add_argument("--evaluate", action="store_true", help="Run the eval harness")
    build.add_argument("--refine", action="store_true", help="Run the refine loop")
    build.add_argument("--max-iterations", type=int, default=3)
    build.add_argument("--target-accuracy", type=float, default=0.9)
    build.set_defaults(func=_build)

    ls = sub.add_parser("list", help="List generated agents")
    ls.set_defaults(func=_list)

    show = sub.add_parser("show", help="Show a generated agent")
    show.add_argument("slug")
    show.set_defaults(func=_show)

    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help()
        return 1
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
