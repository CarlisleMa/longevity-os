"""CLI for depositing and reviewing hypothesis candidates."""

from __future__ import annotations

import argparse
import json
from typing import Any

from .retrieval import build_index, retrieve_context_for_candidate
from .schemas import CANDIDATE_STATUSES, ORIGIN_TYPES, HypothesisCandidate, record_to_dict
from .store import AgenticDiscoveryStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-root", default=None, help="Override registry state directory.")
    sub = parser.add_subparsers(dest="command", required=True)

    deposit = sub.add_parser("deposit", help="Deposit a new quarantined hypothesis candidate.")
    deposit.add_argument("--title", required=True)
    deposit.add_argument("--claim", required=True)
    deposit.add_argument("--mechanism", default="")
    deposit.add_argument("--origin-type", choices=ORIGIN_TYPES, default="human")
    deposit.add_argument("--origin-agent", default="human")
    deposit.add_argument("--origin-detail", default="")
    deposit.add_argument("--artifact", action="append", default=[], dest="trigger_artifacts")
    deposit.add_argument("--expected-direction", default="")
    deposit.add_argument("--modality", action="append", default=[], dest="required_modalities")
    deposit.add_argument("--primary-outcome", default="")
    deposit.add_argument("--confounder", action="append", default=[], dest="confounders")
    deposit.add_argument("--negative-control", action="append", default=[], dest="negative_controls")
    deposit.add_argument("--leakage-risk", action="append", default=[], dest="leakage_risks")
    deposit.add_argument("--need", action="append", default=[], dest="needs")
    deposit.add_argument("--priority", type=float, default=0.5)
    deposit.add_argument("--tag", action="append", default=[], dest="tags")
    deposit.add_argument("--notes", default="")
    deposit.add_argument("--dry-run", action="store_true")

    list_cmd = sub.add_parser("list", help="List candidates.")
    list_cmd.add_argument("--status", choices=CANDIDATE_STATUSES)
    list_cmd.add_argument("--limit", type=int, default=25)
    list_cmd.add_argument("--json", action="store_true")

    show = sub.add_parser("show", help="Show one candidate.")
    show.add_argument("candidate_id")
    show.add_argument("--json", action="store_true")

    status = sub.add_parser("status", help="Update candidate status.")
    status.add_argument("candidate_id")
    status.add_argument("status", choices=CANDIDATE_STATUSES)
    status.add_argument("--note", default="")
    status.add_argument("--dry-run", action="store_true")

    context = sub.add_parser("context", help="Retrieve prior context for a candidate.")
    context.add_argument("candidate_id")
    context.add_argument("--limit", type=int, default=12)
    context.add_argument("--json", action="store_true")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    store = AgenticDiscoveryStore(args.state_root)

    if args.command == "deposit":
        candidate = HypothesisCandidate(
            title=args.title,
            claim=args.claim,
            mechanism=args.mechanism,
            origin_type=args.origin_type,
            origin_agent=args.origin_agent,
            origin_detail=args.origin_detail,
            trigger_artifacts=args.trigger_artifacts,
            expected_direction=args.expected_direction,
            required_modalities=args.required_modalities,
            primary_outcome=args.primary_outcome,
            confounders=args.confounders,
            negative_controls=args.negative_controls,
            leakage_risks=args.leakage_risks,
            needs=args.needs,
            priority=args.priority,
            tags=args.tags,
            notes=args.notes,
        )
        if args.dry_run:
            print(json.dumps(record_to_dict(candidate), indent=2, sort_keys=True))
            return 0
        candidate = store.candidates.append(candidate)
        build_index(store)
        print(f"deposited {candidate.candidate_id}: {candidate.title}")
        return 0

    if args.command == "list":
        records = store.candidates.all()
        if args.status:
            records = [record for record in records if record.status == args.status]
        records.sort(key=lambda record: (record.status, -record.priority, record.created_at))
        records = records[: args.limit]
        if args.json:
            print(json.dumps([record_to_dict(record) for record in records], indent=2, sort_keys=True))
            return 0
        for record in records:
            print(f"{record.candidate_id}\t{record.status}\tP={record.priority:.2f}\t{record.title}")
        return 0

    if args.command == "show":
        candidate = _must_get(store, args.candidate_id)
        if args.json:
            print(json.dumps(record_to_dict(candidate), indent=2, sort_keys=True))
            return 0
        print(_format_candidate(candidate))
        return 0

    if args.command == "status":
        candidate = _must_get(store, args.candidate_id)
        notes = candidate.notes
        if args.note:
            notes = f"{notes}\n{args.note}".strip()
        if args.dry_run:
            candidate.status = args.status
            candidate.notes = notes
            print(json.dumps(record_to_dict(candidate), indent=2, sort_keys=True))
            return 0
        updated = store.candidates.update(args.candidate_id, status=args.status, notes=notes)
        build_index(store)
        print(f"updated {updated.candidate_id}: {updated.status}")
        return 0

    if args.command == "context":
        context = retrieve_context_for_candidate(args.candidate_id, store=store, limit=args.limit)
        if args.json:
            print(json.dumps(context, indent=2, sort_keys=True))
            return 0
        print(_format_context(context))
        return 0

    raise AssertionError(args.command)


def _must_get(store: AgenticDiscoveryStore, candidate_id: str) -> HypothesisCandidate:
    candidate = store.candidates.get(candidate_id)
    if candidate is None:
        raise SystemExit(f"Candidate not found: {candidate_id}")
    return candidate


def _format_candidate(candidate: HypothesisCandidate) -> str:
    lines = [
        f"{candidate.candidate_id} [{candidate.status}] P={candidate.priority:.2f}",
        candidate.title,
        "",
        f"Claim: {candidate.claim}",
    ]
    if candidate.mechanism:
        lines.append(f"Mechanism: {candidate.mechanism}")
    if candidate.required_modalities:
        lines.append(f"Modalities: {', '.join(candidate.required_modalities)}")
    if candidate.primary_outcome:
        lines.append(f"Primary outcome: {candidate.primary_outcome}")
    if candidate.confounders:
        lines.append(f"Confounders: {', '.join(candidate.confounders)}")
    if candidate.negative_controls:
        lines.append(f"Negative controls: {', '.join(candidate.negative_controls)}")
    if candidate.leakage_risks:
        lines.append(f"Leakage risks: {', '.join(candidate.leakage_risks)}")
    if candidate.needs:
        lines.append(f"Needs: {', '.join(candidate.needs)}")
    return "\n".join(lines)


def _format_context(context: dict[str, Any]) -> str:
    candidate = context["candidate"]
    lines = [f"Context for {candidate['candidate_id']}: {candidate['title']}", ""]
    for hit in context["hits"]:
        lines.append(f"- {hit['doc_id']} [{hit['kind']}] {hit['title']}")
        if hit["snippet"]:
            lines.append(f"  {hit['snippet']}")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
