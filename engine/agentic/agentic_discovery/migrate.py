"""Controlled migration utilities for agentic discovery state."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

from .retrieval import build_index
from .schemas import HypothesisCandidate, HypothesisEdge, now_utc, record_to_dict
from .store import AgenticDiscoveryStore


REPO_ROOT = Path(__file__).resolve().parents[1]
LEGACY_HYPOTHESES_ROOT = REPO_ROOT / "hypothesis_driven" / "hypotheses"
STATE_JSONL_FILES = [
    "candidates.jsonl",
    "papers.jsonl",
    "claims.jsonl",
    "tools.jsonl",
    "datasets.jsonl",
    "surprises.jsonl",
    "edges.jsonl",
    "method_plans.jsonl",
    "runs.jsonl",
    "verifications.jsonl",
]
RUNTIME_ARTIFACT_DIRS = [
    "logs",
    "slurm_runs",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-root", default=None, help="Override registry state directory.")
    sub = parser.add_subparsers(dest="command", required=True)

    legacy = sub.add_parser("legacy-hypotheses", help="Import legacy hypothesis_driven JSON files.")
    legacy.add_argument("--source", default=str(LEGACY_HYPOTHESES_ROOT))
    legacy.add_argument("--status-policy", choices=["reset", "map"], default="reset")
    legacy.add_argument("--clear-existing", action="store_true")
    legacy.add_argument("--archive-label", default="manual_archive")
    legacy.add_argument("--dry-run", action="store_true")
    legacy.add_argument("--json", action="store_true")

    archive = sub.add_parser("archive-state", help="Archive current JSONL registry state without importing.")
    archive.add_argument("--archive-label", default="manual_archive")
    archive.add_argument("--dry-run", action="store_true")
    archive.add_argument("--json", action="store_true")

    runtime = sub.add_parser(
        "archive-runtime",
        help="Archive ignored runtime artifacts such as logs and Slurm job specs without touching JSONL state.",
    )
    runtime.add_argument("--archive-label", default="manual_runtime_archive")
    runtime.add_argument("--archive-dir", default=None, help="Existing archive directory to append to.")
    runtime.add_argument("--dry-run", action="store_true")
    runtime.add_argument("--json", action="store_true")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    store = AgenticDiscoveryStore(args.state_root)

    if args.command == "legacy-hypotheses":
        payload = import_legacy_hypotheses(
            store=store,
            source=Path(args.source),
            status_policy=args.status_policy,
            clear_existing=args.clear_existing,
            archive_label=args.archive_label,
            dry_run=args.dry_run,
        )
        return _print(payload, args.json)

    if args.command == "archive-state":
        payload = archive_state(store, args.archive_label, dry_run=args.dry_run)
        return _print(payload, args.json)

    if args.command == "archive-runtime":
        payload = archive_runtime_artifacts(
            store,
            archive_label=args.archive_label,
            archive_dir=Path(args.archive_dir) if args.archive_dir else None,
            dry_run=args.dry_run,
        )
        return _print(payload, args.json)

    raise AssertionError(args.command)


def import_legacy_hypotheses(
    store: AgenticDiscoveryStore,
    source: Path,
    status_policy: str = "reset",
    clear_existing: bool = False,
    archive_label: str = "legacy_import_archive",
    dry_run: bool = False,
) -> dict[str, Any]:
    source = source.resolve()
    legacy_records = list(_load_legacy_hypotheses(source))
    candidates = [_legacy_to_candidate(record, source, status_policy=status_policy) for record in legacy_records]
    edges = [_legacy_edge(candidate, record) for candidate, record in zip(candidates, legacy_records)]
    payload: dict[str, Any] = {
        "source": str(source),
        "dry_run": dry_run,
        "clear_existing": clear_existing,
        "status_policy": status_policy,
        "legacy_count": len(legacy_records),
        "candidate_count": len(candidates),
        "edge_count": len(edges),
        "candidates": [
            {
                "candidate_id": candidate.candidate_id,
                "legacy_id": _legacy_id(record),
                "title": candidate.title,
                "status": candidate.status,
                "priority": candidate.priority,
            }
            for candidate, record in zip(candidates, legacy_records)
        ],
    }
    if dry_run:
        return payload

    archive_payload = None
    if clear_existing:
        archive_payload = archive_state(store, archive_label, dry_run=False)
    for candidate in candidates:
        store.candidates.upsert(candidate)
    for edge in edges:
        store.edges.upsert(edge)
    if store.index_path().exists():
        store.index_path().unlink()
    build_index(store)
    payload["archive"] = archive_payload
    payload["new_counts"] = store.counts()
    return payload


def archive_state(store: AgenticDiscoveryStore, archive_label: str, dry_run: bool = False) -> dict[str, Any]:
    archive_dir = _new_archive_dir(store, archive_label)
    files = []
    for name in STATE_JSONL_FILES:
        path = store.root / name
        if path.exists():
            files.append(path)
    runtime_dirs = _runtime_artifact_dirs(store)
    payload = {
        "dry_run": dry_run,
        "archive_dir": str(archive_dir),
        "files": [str(path) for path in files],
        "runtime_dirs": [str(path) for path in runtime_dirs],
        "counts": store.counts(),
    }
    if dry_run:
        return payload
    archive_dir.mkdir(parents=True, exist_ok=True)
    for path in files:
        shutil.move(str(path), archive_dir / path.name)
    for path in runtime_dirs:
        shutil.move(str(path), archive_dir / path.name)
    if store.index_path().exists():
        store.index_path().unlink()
    manifest = {
        "created_at": now_utc(),
        "archive_label": archive_label,
        "files": [path.name for path in files],
        "runtime_dirs": [path.name for path in runtime_dirs],
        "counts_before_archive": payload["counts"],
    }
    (archive_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return payload


def archive_runtime_artifacts(
    store: AgenticDiscoveryStore,
    archive_label: str,
    archive_dir: Path | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    archive_dir = archive_dir.resolve() if archive_dir else _new_archive_dir(store, archive_label)
    runtime_dirs = _runtime_artifact_dirs(store)
    payload = {
        "dry_run": dry_run,
        "archive_dir": str(archive_dir),
        "runtime_dirs": [str(path) for path in runtime_dirs],
        "counts": store.counts(),
    }
    if dry_run:
        return payload
    archive_dir.mkdir(parents=True, exist_ok=True)
    for path in runtime_dirs:
        shutil.move(str(path), archive_dir / path.name)
    _update_archive_manifest(
        archive_dir,
        {
            "runtime_artifacts_archived_at": now_utc(),
            "runtime_artifacts_archive_label": archive_label,
            "runtime_dirs": [path.name for path in runtime_dirs],
            "counts_at_runtime_archive": payload["counts"],
        },
    )
    return payload


def _new_archive_dir(store: AgenticDiscoveryStore, archive_label: str) -> Path:
    label = "".join(char if char.isalnum() or char in "._-" else "_" for char in archive_label)
    stamp = now_utc().replace(":", "").replace("-", "").replace("Z", "")
    return store.root / "archive" / f"{stamp}_{label}"


def _runtime_artifact_dirs(store: AgenticDiscoveryStore) -> list[Path]:
    paths = []
    for name in RUNTIME_ARTIFACT_DIRS:
        path = store.root / name
        if path.exists():
            paths.append(path)
    return paths


def _update_archive_manifest(archive_dir: Path, update: dict[str, Any]) -> None:
    manifest_path = archive_dir / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    else:
        manifest = {
            "created_at": now_utc(),
            "archive_label": archive_dir.name,
        }
    manifest.update(update)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")


def _load_legacy_hypotheses(source: Path) -> list[dict[str, Any]]:
    if not source.exists():
        raise FileNotFoundError(f"Legacy hypothesis directory not found: {source}")
    records = []
    for path in sorted(source.glob("*.json")):
        if path.name.startswith("proposed_batch"):
            continue
        data = json.loads(path.read_text())
        if not isinstance(data, dict):
            continue
        data["_source_path"] = str(path)
        records.append(data)
    return records


def _legacy_to_candidate(record: dict[str, Any], source_root: Path, status_policy: str) -> HypothesisCandidate:
    legacy_id = _legacy_id(record)
    feasibility = record.get("feasibility") if isinstance(record.get("feasibility"), dict) else {}
    test_plan = record.get("test_plan") if isinstance(record.get("test_plan"), dict) else {}
    results = record.get("results") if isinstance(record.get("results"), dict) else None
    critic = record.get("critic_verdict") if isinstance(record.get("critic_verdict"), dict) else None
    source_path = Path(record.get("_source_path", "")).resolve()
    try:
        artifact = str(source_path.relative_to(REPO_ROOT))
    except ValueError:
        artifact = str(source_path)

    candidate = HypothesisCandidate(
        candidate_id=f"CAND-LEGACY-{legacy_id}",
        created_at=record.get("created") or now_utc(),
        updated_at=record.get("updated") or now_utc(),
        origin_type="legacy_migration",
        origin_agent="legacy_import",
        origin_detail=f"Imported from {artifact}",
        trigger_artifacts=[artifact],
        title=record.get("title", legacy_id),
        claim=record.get("statement", ""),
        mechanism=record.get("mechanism", ""),
        expected_direction=_expected_direction(record),
        required_modalities=list(feasibility.get("required_modalities", [])),
        primary_outcome=test_plan.get("primary_method", ""),
        confounders=list(test_plan.get("confounders_to_adjust", [])),
        negative_controls=_negative_controls(record),
        leakage_risks=_leakage_risks(record),
        status=_mapped_status(record.get("status", "proposed"), status_policy),
        priority=float(record.get("priority") or 0.5),
        needs=_needs(record),
        parent_ids=[],
        tags=[
            "legacy_import",
            f"legacy_id:{legacy_id}",
            f"legacy_status:{record.get('status', '')}",
            f"category:{record.get('category', '')}",
        ],
        notes=_notes(record, results=results, critic=critic),
    )
    return candidate


def _legacy_edge(candidate: HypothesisCandidate, record: dict[str, Any]) -> HypothesisEdge:
    legacy_id = _legacy_id(record)
    return HypothesisEdge(
        edge_id=f"EDGE-LEGACY-{legacy_id}",
        source_id=candidate.candidate_id,
        target_id=legacy_id,
        edge_type="generated_from",
        rationale="Controlled import from legacy hypothesis_driven workspace.",
        evidence_ids=[],
        confidence=1.0,
        created_by="legacy_import",
    )


def _legacy_id(record: dict[str, Any]) -> str:
    return str(record.get("id") or Path(record.get("_source_path", "legacy")).stem)


def _mapped_status(status: str, status_policy: str) -> str:
    if status_policy == "reset":
        return "candidate"
    mapping = {
        "proposed": "candidate",
        "critiqued": "critiqued",
        "validated": "feasible",
        "queued": "registered",
        "executing": "registered",
        "completed": "registered",
        "verified": "registered",
        "supported": "registered",
        "refuted": "rejected",
        "inconclusive": "critiqued",
        "rejected": "rejected",
    }
    return mapping.get(status, "candidate")


def _expected_direction(record: dict[str, Any]) -> str:
    predictions = record.get("predictions") or []
    if predictions:
        return str(predictions[0])
    return ""


def _negative_controls(record: dict[str, Any]) -> list[str]:
    out = []
    for prediction in record.get("predictions") or []:
        text = str(prediction)
        if "negative control" in text.lower():
            out.append(text)
    test_plan = record.get("test_plan") if isinstance(record.get("test_plan"), dict) else {}
    for check in test_plan.get("sensitivity_checks", []) or []:
        text = str(check)
        if "negative" in text.lower() or "random" in text.lower() or "control" in text.lower():
            out.append(text)
    return out


def _leakage_risks(record: dict[str, Any]) -> list[str]:
    feasibility = record.get("feasibility") if isinstance(record.get("feasibility"), dict) else {}
    risks = []
    for key in ("key_challenges", "dataset_limitations"):
        for item in feasibility.get(key, []) or []:
            risks.append(str(item))
    critic = record.get("critic_verdict") if isinstance(record.get("critic_verdict"), dict) else {}
    for issue in critic.get("issues", []) or []:
        risks.append(str(issue))
    return risks[:12]


def _needs(record: dict[str, Any]) -> list[str]:
    needs = []
    feasibility = record.get("feasibility") if isinstance(record.get("feasibility"), dict) else {}
    if feasibility.get("time_resolution_needed"):
        needs.append(f"time_resolution_needed: {feasibility['time_resolution_needed']}")
    if feasibility.get("analysis_timescale"):
        needs.append(f"analysis_timescale: {feasibility['analysis_timescale']}")
    if feasibility.get("statistical_power"):
        needs.append(f"statistical_power: {feasibility['statistical_power']}")
    if feasibility.get("computational_cost"):
        needs.append(f"computational_cost: {feasibility['computational_cost']}")
    return needs


def _notes(record: dict[str, Any], results: dict[str, Any] | None, critic: dict[str, Any] | None) -> str:
    lines = [
        f"Legacy ID: {_legacy_id(record)}",
        f"Legacy category: {record.get('category', '')}",
        f"Legacy status: {record.get('status', '')}",
        f"Legacy source: {record.get('source', '')}",
    ]
    if critic:
        lines.append(
            "Legacy critic verdict: "
            f"{critic.get('verdict', '')}; score={critic.get('overall_score', '')}"
        )
    if results:
        lines.append(
            "Legacy result summary: "
            f"method={results.get('method_used', '')}; "
            f"primary={results.get('primary_metric', '')} {results.get('primary_value', '')}; "
            f"p={results.get('p_value', '')}"
        )
    if record.get("notes"):
        lines.append(f"Legacy notes: {record['notes']}")
    return "\n".join(lines)


def _print(payload: dict[str, Any], json_output: bool) -> int:
    if json_output:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
