"""CLI for execution runs and verification records."""

from __future__ import annotations

import argparse
import json
from typing import Any

from .retrieval import build_index
from .schemas import (
    PLAN_STATUSES,
    RUN_STATUSES,
    VERDICTS,
    ExecutionRun,
    MethodPlanRecord,
    VerificationRecord,
    record_to_dict,
)
from .store import AgenticDiscoveryStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-root", default=None, help="Override registry state directory.")
    sub = parser.add_subparsers(dest="command", required=True)

    plan = sub.add_parser("add-plan", help="Register a method plan before execution.")
    plan.add_argument("--target-id", required=True)
    plan.add_argument("--target-type", default="candidate")
    plan.add_argument("--objective", required=True)
    plan.add_argument("--input", action="append", default=[], dest="inputs")
    plan.add_argument("--output", action="append", default=[], dest="outputs")
    plan.add_argument("--split-id", default="")
    plan.add_argument("--adjust", action="append", default=[], dest="adjustment_set")
    plan.add_argument("--negative-control", action="append", default=[], dest="negative_controls")
    plan.add_argument("--leakage-check", action="append", default=[], dest="leakage_checks")
    plan.add_argument("--statistical-test", action="append", default=[], dest="statistical_tests")
    plan.add_argument("--step", action="append", default=[], dest="execution_steps")
    plan.add_argument("--script-path", default="")
    plan.add_argument("--command-template", default="")
    plan.add_argument("--status", choices=PLAN_STATUSES, default="draft")
    plan.add_argument("--created-by", default="human")
    plan.add_argument("--notes", default="")
    plan.add_argument("--dry-run", action="store_true")

    run = sub.add_parser("add-run", help="Register an execution run or planned run.")
    run.add_argument("--hypothesis-id", default="")
    run.add_argument("--candidate-id", default="")
    run.add_argument("--split-id", default="")
    run.add_argument("--script-path", default="")
    run.add_argument("--command", default="", dest="run_command")
    run.add_argument("--artifact", action="append", default=[], dest="artifacts")
    run.add_argument("--metric", action="append", default=[], dest="metrics")
    run.add_argument("--check", action="append", default=[], dest="mechanical_checks")
    run.add_argument("--status", choices=RUN_STATUSES, default="planned")
    run.add_argument("--notes", default="")
    run.add_argument("--dry-run", action="store_true")

    verify = sub.add_parser("add-verification", help="Register mechanical verification or critic outcome.")
    verify.add_argument("--target-id", required=True)
    verify.add_argument("--target-type", required=True)
    verify.add_argument("--verdict", choices=VERDICTS, default="not_checked")
    verify.add_argument("--check", action="append", default=[], dest="checks")
    verify.add_argument("--blocker", action="append", default=[], dest="blockers")
    verify.add_argument("--recommendation", action="append", default=[], dest="recommendations")
    verify.add_argument("--reviewer", default="")
    verify.add_argument("--dry-run", action="store_true")

    list_runs = sub.add_parser("list-runs", help="List execution runs.")
    list_runs.add_argument("--status", choices=RUN_STATUSES)
    list_runs.add_argument("--target-id", default="")
    list_runs.add_argument("--json", action="store_true")

    list_plans = sub.add_parser("list-plans", help="List method plans.")
    list_plans.add_argument("--status", choices=PLAN_STATUSES)
    list_plans.add_argument("--target-id", default="")
    list_plans.add_argument("--json", action="store_true")

    list_verifications = sub.add_parser("list-verifications", help="List verification records.")
    list_verifications.add_argument("--target-id", default="")
    list_verifications.add_argument("--verdict", choices=VERDICTS)
    list_verifications.add_argument("--json", action="store_true")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    store = AgenticDiscoveryStore(args.state_root)

    if args.command == "add-plan":
        record = MethodPlanRecord(
            target_id=args.target_id,
            target_type=args.target_type,
            objective=args.objective,
            inputs=args.inputs,
            outputs=args.outputs,
            split_id=args.split_id,
            adjustment_set=args.adjustment_set,
            negative_controls=args.negative_controls,
            leakage_checks=args.leakage_checks,
            statistical_tests=args.statistical_tests,
            execution_steps=args.execution_steps,
            script_path=args.script_path,
            command_template=args.command_template,
            status=args.status,
            created_by=args.created_by,
            notes=args.notes,
        )
        return _append_or_print(store, store.method_plans, record, args.dry_run)

    if args.command == "add-run":
        record = ExecutionRun(
            hypothesis_id=args.hypothesis_id,
            candidate_id=args.candidate_id,
            split_id=args.split_id,
            script_path=args.script_path,
            command=args.run_command,
            artifacts=args.artifacts,
            metrics=_parse_pairs(args.metrics),
            mechanical_checks=_parse_pairs(args.mechanical_checks),
            status=args.status,
            notes=args.notes,
        )
        return _append_or_print(store, store.runs, record, args.dry_run)

    if args.command == "add-verification":
        record = VerificationRecord(
            target_id=args.target_id,
            target_type=args.target_type,
            verdict=args.verdict,
            checks=_parse_pairs(args.checks),
            blockers=args.blockers,
            recommendations=args.recommendations,
            reviewer=args.reviewer,
        )
        return _append_or_print(store, store.verifications, record, args.dry_run)

    if args.command == "list-runs":
        records = store.runs.all()
        if args.status:
            records = [record for record in records if record.status == args.status]
        if args.target_id:
            records = [
                record
                for record in records
                if record.hypothesis_id == args.target_id or record.candidate_id == args.target_id
            ]
        return _print_records(records, args.json)

    if args.command == "list-plans":
        records = store.method_plans.all()
        if args.status:
            records = [record for record in records if record.status == args.status]
        if args.target_id:
            records = [record for record in records if record.target_id == args.target_id]
        return _print_records(records, args.json)

    if args.command == "list-verifications":
        records = store.verifications.all()
        if args.target_id:
            records = [record for record in records if record.target_id == args.target_id]
        if args.verdict:
            records = [record for record in records if record.verdict == args.verdict]
        return _print_records(records, args.json)

    raise AssertionError(args.command)


def _parse_pairs(items: list[str]) -> dict[str, Any]:
    parsed: dict[str, Any] = {}
    for item in items:
        if "=" not in item:
            raise SystemExit(f"Expected key=value, got: {item}")
        key, value = item.split("=", 1)
        parsed[key.strip()] = _coerce_value(value.strip())
    return parsed


def _coerce_value(value: str) -> Any:
    lowered = value.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


def _append_or_print(store: AgenticDiscoveryStore, collection, record, dry_run: bool) -> int:
    if dry_run:
        print(json.dumps(record_to_dict(record), indent=2, sort_keys=True))
        return 0
    record = collection.append(record)
    build_index(store)
    print(f"registered {getattr(record, collection.id_field)}")
    return 0


def _print_records(records: list[Any], json_output: bool) -> int:
    if json_output:
        print(json.dumps([record_to_dict(record) for record in records], indent=2, sort_keys=True))
        return 0
    for record in records:
        data = record_to_dict(record)
        record_id = next((value for key, value in data.items() if key.endswith("_id")), "")
        target = data.get("hypothesis_id") or data.get("candidate_id") or data.get("target_id") or ""
        status = data.get("status") or data.get("verdict") or ""
        print(f"{record_id}\t{target}\t{status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
