"""Top-level dispatcher for the agentic discovery CLIs."""

from __future__ import annotations

import argparse

from . import (
    candidates,
    claude_runner,
    evidence,
    execution_proposals,
    graph,
    knowledge,
    migrate,
    rounds,
    slurm_execution,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Agentic discovery workspace.")
    parser.add_argument(
        "area",
        choices=[
            "candidates",
            "knowledge",
            "migrate",
            "compile",
            "graph",
            "evidence",
            "rounds",
            "slurm",
            "sdk",
            "claude-sdk",
        ],
    )
    args, rest = parser.parse_known_args(argv)
    if args.area == "candidates":
        return candidates.main(rest)
    if args.area == "knowledge":
        return knowledge.main(rest)
    if args.area == "migrate":
        return migrate.main(rest)
    if args.area == "compile":
        return execution_proposals.main(rest)
    if args.area == "graph":
        return graph.main(rest)
    if args.area == "evidence":
        return evidence.main(rest)
    if args.area == "rounds":
        return rounds.main(rest)
    if args.area == "slurm":
        return slurm_execution.main(rest)
    if args.area in {"sdk", "claude-sdk"}:
        return claude_runner.main(rest)
    raise AssertionError(args.area)


if __name__ == "__main__":
    raise SystemExit(main())
