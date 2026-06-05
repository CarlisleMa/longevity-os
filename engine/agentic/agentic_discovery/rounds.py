"""Round planning utilities for agentic discovery."""

from __future__ import annotations

import argparse
import json
from collections import Counter

from .retrieval import build_index, retrieve_context_for_candidate
from .schemas import CANDIDATE_STATUSES
from .store import AgenticDiscoveryStore


ACTIVE_STATUSES = ["candidate", "enriched", "critiqued", "feasible", "method_planned"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-root", default=None, help="Override registry state directory.")
    sub = parser.add_subparsers(dest="command", required=True)

    summary = sub.add_parser("summary", help="Summarize registry state.")
    summary.add_argument("--json", action="store_true")

    plan = sub.add_parser("plan", help="Plan the next hypothesis-first discovery round.")
    plan.add_argument("--limit", type=int, default=5)
    plan.add_argument("--status", action="append", choices=CANDIDATE_STATUSES, default=[])
    plan.add_argument("--json", action="store_true")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    store = AgenticDiscoveryStore(args.state_root)

    if args.command == "summary":
        payload = _summary_payload(store)
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 0
        print(_format_summary(payload))
        return 0

    if args.command == "plan":
        build_index(store)
        statuses = args.status or ACTIVE_STATUSES
        candidates = [
            candidate for candidate in store.candidates.all() if candidate.status in statuses
        ]
        candidates.sort(key=lambda candidate: (-candidate.priority, candidate.created_at))
        selected = candidates[: args.limit]
        payload = {
            "summary": _summary_payload(store),
            "selected_candidates": [],
            "recommended_round_order": [
                "retrieve_context",
                "literature_tool_dataset_enrichment",
                "critic_review",
                "feasibility_and_split_check",
                "method_registration",
                "execution_or_slurm_submission",
                "mechanical_verification",
                "follow_up_candidate_deposition",
            ],
        }
        for candidate in selected:
            context = retrieve_context_for_candidate(candidate.candidate_id, store=store, limit=8)
            payload["selected_candidates"].append(
                {
                    "candidate_id": candidate.candidate_id,
                    "title": candidate.title,
                    "status": candidate.status,
                    "priority": candidate.priority,
                    "needs": candidate.needs,
                    "context_hits": [
                        {
                            "doc_id": hit["doc_id"],
                            "kind": hit["kind"],
                            "title": hit["title"],
                            "source_path": hit["source_path"],
                        }
                        for hit in context["hits"]
                    ],
                }
            )
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 0
        print(_format_plan(payload))
        return 0

    raise AssertionError(args.command)


def _summary_payload(store: AgenticDiscoveryStore) -> dict:
    candidates = store.candidates.all()
    return {
        "state_root": str(store.root),
        "counts": store.counts(),
        "candidate_status_counts": dict(Counter(candidate.status for candidate in candidates)),
        "candidate_priority_top": [
            {
                "candidate_id": candidate.candidate_id,
                "status": candidate.status,
                "priority": candidate.priority,
                "title": candidate.title,
            }
            for candidate in sorted(candidates, key=lambda item: (-item.priority, item.created_at))[:10]
        ],
    }


def _format_summary(payload: dict) -> str:
    lines = [f"State root: {payload['state_root']}", "Counts:"]
    for name, count in payload["counts"].items():
        lines.append(f"  {name}: {count}")
    if payload["candidate_status_counts"]:
        lines.append("Candidate statuses:")
        for status, count in sorted(payload["candidate_status_counts"].items()):
            lines.append(f"  {status}: {count}")
    return "\n".join(lines)


def _format_plan(payload: dict) -> str:
    lines = [_format_summary(payload["summary"]), "", "Recommended round order:"]
    for index, step in enumerate(payload["recommended_round_order"], 1):
        lines.append(f"  {index}. {step}")
    if payload["selected_candidates"]:
        lines.append("")
        lines.append("Selected candidates:")
    for candidate in payload["selected_candidates"]:
        lines.append(
            f"- {candidate['candidate_id']} [{candidate['status']}] "
            f"P={candidate['priority']:.2f} {candidate['title']}"
        )
        if candidate["needs"]:
            lines.append(f"  Needs: {', '.join(candidate['needs'])}")
        if candidate["context_hits"]:
            lines.append("  Context hits:")
            for hit in candidate["context_hits"][:5]:
                lines.append(f"    {hit['doc_id']} [{hit['kind']}] {hit['title']}")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
