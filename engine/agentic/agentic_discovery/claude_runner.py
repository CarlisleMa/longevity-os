"""Claude Agent SDK runner for hypothesis-first discovery rounds."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from .claude_runtime import ClaudeAgentSdkUnavailable, diagnose_claude_sdk
from .retrieval import build_index, retrieve_context_for_candidate
from .rounds import ACTIVE_STATUSES
from .store import AgenticDiscoveryStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-root", default=None, help="Override registry state directory.")
    sub = parser.add_subparsers(dest="command", required=True)

    diagnose = sub.add_parser("diagnose", help="Check Claude Agent SDK availability and auth.")
    diagnose.add_argument("--json", action="store_true")

    dry_run = sub.add_parser("dry-run", help="Produce a deterministic round plan without calling Claude.")
    dry_run.add_argument("--candidate-id", action="append", default=[], dest="candidate_ids")
    dry_run.add_argument("--limit", type=int, default=3)
    dry_run.add_argument("--json", action="store_true")

    run = sub.add_parser("run", help="Run one Claude Agent SDK discovery manager round.")
    run.add_argument("--candidate-id", action="append", default=[], dest="candidate_ids")
    run.add_argument("--limit", type=int, default=3)
    run.add_argument("--model", default=None)
    run.add_argument("--max-turns", type=int, default=12)
    run.add_argument("--effort", choices=["low", "medium", "high", "xhigh", "max"], default=None)
    run.add_argument("--instruction", default="")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    store = AgenticDiscoveryStore(args.state_root)

    if args.command == "diagnose":
        payload = diagnose_claude_sdk().to_dict()
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print(_format_diagnostic(payload))
        return 0

    if args.command == "dry-run":
        payload = deterministic_round_plan(store, args.candidate_ids, args.limit)
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print(_format_dry_run(payload))
        return 0

    if args.command == "run":
        try:
            output = asyncio.run(
                run_claude_round(
                    store=store,
                    candidate_ids=args.candidate_ids,
                    limit=args.limit,
                    model=args.model,
                    max_turns=args.max_turns,
                    effort=args.effort,
                    instruction=args.instruction,
                )
            )
        except ClaudeAgentSdkUnavailable as exc:
            raise SystemExit(f"{exc}\nRun `python -m agentic_discovery sdk diagnose` for details.") from exc
        print(output)
        return 0

    raise AssertionError(args.command)


async def run_claude_round(
    store: AgenticDiscoveryStore,
    candidate_ids: list[str],
    limit: int,
    model: str | None,
    max_turns: int,
    effort: str | None,
    instruction: str,
) -> str:
    from claude_agent_sdk import ResultMessage, query

    from .claude_agents import build_claude_options

    plan = deterministic_round_plan(store, candidate_ids, limit)
    prompt = _prompt(store, plan, instruction)
    options = build_claude_options(
        state_root=str(store.root),
        model=model,
        max_turns=max_turns,
        cwd=Path(__file__).resolve().parents[1],
        effort=effort,
    )
    final = ""
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, ResultMessage):
            final = message.result
    return final or "Claude Agent SDK run completed without a ResultMessage."


def deterministic_round_plan(
    store: AgenticDiscoveryStore,
    candidate_ids: list[str],
    limit: int,
) -> dict[str, Any]:
    build_index(store)
    selected = []
    if candidate_ids:
        for candidate_id in candidate_ids:
            candidate = store.candidates.get(candidate_id)
            if candidate is None:
                selected.append({"candidate_id": candidate_id, "error": "not_found"})
            else:
                selected.append(_candidate_context_payload(store, candidate_id))
    else:
        candidates = [
            candidate for candidate in store.candidates.all() if candidate.status in ACTIVE_STATUSES
        ]
        candidates.sort(key=lambda candidate: (-candidate.priority, candidate.created_at))
        for candidate in candidates[:limit]:
            selected.append(_candidate_context_payload(store, candidate.candidate_id))

    return {
        "state_root": str(store.root),
        "counts": store.counts(),
        "selected_candidates": selected,
        "round_steps": [
            "retrieve_context",
            "literature_tool_dataset_enrichment",
            "scientific_critique",
            "feasibility_and_leakage_review",
            "method_plan_registration",
            "execution_proposal_static_validation",
            "execution_proposal_scientific_feasibility_mechanical_gate",
            "guarded_execution_spec_dry_run_or_submission_if_explicitly_authorized",
            "execution_record_registration_if_artifacts_are_supplied",
            "mechanical_verification",
            "surprise_and_follow_up_deposition",
            "round_synthesis",
        ],
    }


def _candidate_context_payload(store: AgenticDiscoveryStore, candidate_id: str) -> dict[str, Any]:
    context = retrieve_context_for_candidate(candidate_id, store=store, limit=8)
    candidate = context["candidate"]
    hits = [
        {
            "doc_id": hit["doc_id"],
            "kind": hit["kind"],
            "title": hit["title"],
            "source_path": hit["source_path"],
            "snippet": hit["snippet"],
        }
        for hit in context["hits"]
    ]
    return {
        "candidate_id": candidate["candidate_id"],
        "title": candidate["title"],
        "status": candidate["status"],
        "priority": candidate["priority"],
        "needs": candidate["needs"],
        "context_hits": hits,
    }


def _prompt(store: AgenticDiscoveryStore, plan: dict[str, Any], instruction: str) -> str:
    return "\n".join(
        [
            "Run one hypothesis-first discovery management round.",
            f"State root: {store.root}",
            "Use the agentic_discovery MCP tools for all durable writes.",
            "Do not run raw shell commands or edit source files. Submit Slurm jobs only through guarded execution-spec tools when explicitly authorized.",
            "",
            "Deterministic preflight plan:",
            json.dumps(plan, indent=2, sort_keys=True),
            "",
            "Human instruction:",
            instruction
            or "Review the selected queue, retrieve/enrich/critique/plan as appropriate, and register structured records.",
        ]
    )


def _format_diagnostic(payload: dict[str, Any]) -> str:
    auth = payload["auth_status"]
    lines = [
        f"Claude SDK available for live runs: {payload['available']}",
        f"claude-agent-sdk version: {payload['package_version'] or 'not installed'}",
        f"SDK module file: {payload['module_file'] or 'not importable'}",
        f"Bundled Claude CLI: {payload['bundled_cli_path'] or 'not found'}",
        f"Bundled Claude CLI version: {payload['bundled_cli_version'] or 'unknown'}",
        f"Global Claude CLI: {payload['global_cli_path'] or 'not found'}",
        f"node on PATH: {payload['node_path'] or 'not found'}",
        f"ANTHROPIC_API_KEY present: {payload['anthropic_api_key_present']}",
        f"Claude plan login detected: {bool(auth.get('loggedIn'))}",
    ]
    if auth.get("email"):
        lines.append(f"Claude account: {auth['email']}")
    if auth.get("subscriptionType"):
        lines.append(f"Subscription type: {auth['subscriptionType']}")
    lines.append(payload["message"])
    return "\n".join(lines)


def _format_dry_run(payload: dict[str, Any]) -> str:
    lines = [f"State root: {payload['state_root']}", "Counts:"]
    for name, count in payload["counts"].items():
        lines.append(f"  {name}: {count}")
    lines.append("Round steps:")
    for index, step in enumerate(payload["round_steps"], 1):
        lines.append(f"  {index}. {step}")
    if payload["selected_candidates"]:
        lines.append("Selected candidates:")
    for candidate in payload["selected_candidates"]:
        if "error" in candidate:
            lines.append(f"  {candidate['candidate_id']}: {candidate['error']}")
            continue
        lines.append(
            f"  {candidate['candidate_id']} [{candidate['status']}] "
            f"P={candidate['priority']:.2f} {candidate['title']}"
        )
        for hit in candidate["context_hits"][:5]:
            lines.append(f"    context: {hit['doc_id']} [{hit['kind']}] {hit['title']}")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
