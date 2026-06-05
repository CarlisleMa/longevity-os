"""Persistent JSONL stores for agentic discovery records."""

from __future__ import annotations

import json
import re
from dataclasses import fields
from pathlib import Path
from typing import Any

from .schemas import (
    CANDIDATE_STATUSES,
    EDGE_TYPES,
    ORIGIN_TYPES,
    PLAN_STATUSES,
    RUN_STATUSES,
    VERDICTS,
    DatasetRecord,
    ExecutionRun,
    ExtractedClaim,
    HypothesisCandidate,
    HypothesisEdge,
    MethodPlanRecord,
    PaperRecord,
    SurpriseRecord,
    ToolRecord,
    VerificationRecord,
    now_utc,
    record_from_dict,
    record_to_dict,
)


PACKAGE_ROOT = Path(__file__).resolve().parent
DEFAULT_STATE_ROOT = PACKAGE_ROOT / "state"


class JsonlCollection:
    """Append/update collection backed by one JSON object per line."""

    def __init__(self, path: Path, record_cls: type, id_field: str, id_prefix: str):
        self.path = path
        self.record_cls = record_cls
        self.id_field = id_field
        self.id_prefix = id_prefix
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._field_names = {field.name for field in fields(record_cls)}

    def all(self) -> list[Any]:
        if not self.path.exists():
            return []
        records = []
        for line_number, line in enumerate(self.path.read_text().splitlines(), 1):
            if not line.strip():
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON in {self.path}:{line_number}: {exc}") from exc
            records.append(record_from_dict(self.record_cls, data))
        return records

    def get(self, record_id: str) -> Any | None:
        for record in self.all():
            if getattr(record, self.id_field) == record_id:
                return record
        return None

    def append(self, record: Any) -> Any:
        if not getattr(record, self.id_field):
            setattr(record, self.id_field, self.next_id())
        self._validate(record)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record_to_dict(record), sort_keys=True) + "\n")
        return record

    def replace(self, record: Any) -> Any:
        record_id = getattr(record, self.id_field)
        if not record_id:
            raise ValueError(f"Cannot replace record without {self.id_field}")
        self._validate(record)
        records = self.all()
        replaced = False
        for index, existing in enumerate(records):
            if getattr(existing, self.id_field) == record_id:
                records[index] = record
                replaced = True
                break
        if not replaced:
            raise KeyError(f"{record_id} not found in {self.path}")
        self._write_all(records)
        return record

    def upsert(self, record: Any) -> Any:
        record_id = getattr(record, self.id_field)
        if record_id and self.get(record_id):
            return self.replace(record)
        return self.append(record)

    def update(self, record_id: str, **updates: Any) -> Any:
        record = self.get(record_id)
        if record is None:
            raise KeyError(f"{record_id} not found in {self.path}")
        unknown = sorted(set(updates) - self._field_names)
        if unknown:
            raise KeyError(f"Unknown fields for {self.record_cls.__name__}: {unknown}")
        for key, value in updates.items():
            setattr(record, key, value)
        if "updated_at" in self._field_names and "updated_at" not in updates:
            setattr(record, "updated_at", now_utc())
        return self.replace(record)

    def next_id(self) -> str:
        date_token = now_utc()[:10].replace("-", "")
        pattern = re.compile(rf"^{re.escape(self.id_prefix)}-{date_token}-(\d+)$")
        max_seen = 0
        for record in self.all():
            record_id = getattr(record, self.id_field)
            match = pattern.match(record_id or "")
            if match:
                max_seen = max(max_seen, int(match.group(1)))
        return f"{self.id_prefix}-{date_token}-{max_seen + 1:04d}"

    def _write_all(self, records: list[Any]) -> None:
        temp_path = self.path.with_suffix(self.path.suffix + ".tmp")
        payload = "".join(json.dumps(record_to_dict(record), sort_keys=True) + "\n" for record in records)
        temp_path.write_text(payload, encoding="utf-8")
        temp_path.replace(self.path)

    def _validate(self, record: Any) -> None:
        if isinstance(record, HypothesisCandidate):
            if record.status not in CANDIDATE_STATUSES:
                raise ValueError(f"Invalid candidate status: {record.status}")
            if record.origin_type not in ORIGIN_TYPES:
                raise ValueError(f"Invalid origin_type: {record.origin_type}")
            if not record.title.strip():
                raise ValueError("HypothesisCandidate.title is required")
            if not record.claim.strip():
                raise ValueError("HypothesisCandidate.claim is required")
        if isinstance(record, HypothesisEdge):
            if record.edge_type not in EDGE_TYPES:
                raise ValueError(f"Invalid edge_type: {record.edge_type}")
            if not record.source_id or not record.target_id:
                raise ValueError("HypothesisEdge requires source_id and target_id")
        if isinstance(record, VerificationRecord) and record.verdict not in VERDICTS:
            raise ValueError(f"Invalid verification verdict: {record.verdict}")
        if isinstance(record, ExecutionRun) and record.status not in RUN_STATUSES:
            raise ValueError(f"Invalid run status: {record.status}")
        if isinstance(record, MethodPlanRecord) and record.status not in PLAN_STATUSES:
            raise ValueError(f"Invalid method plan status: {record.status}")


class AgenticDiscoveryStore:
    """Registry root for the hypothesis-first discovery system."""

    def __init__(self, root: str | Path | None = None):
        self.root = Path(root) if root is not None else DEFAULT_STATE_ROOT
        self.root.mkdir(parents=True, exist_ok=True)
        self.candidates = JsonlCollection(
            self.root / "candidates.jsonl", HypothesisCandidate, "candidate_id", "CAND"
        )
        self.papers = JsonlCollection(self.root / "papers.jsonl", PaperRecord, "paper_id", "PAPER")
        self.claims = JsonlCollection(self.root / "claims.jsonl", ExtractedClaim, "claim_id", "CLAIM")
        self.tools = JsonlCollection(self.root / "tools.jsonl", ToolRecord, "tool_id", "TOOL")
        self.datasets = JsonlCollection(
            self.root / "datasets.jsonl", DatasetRecord, "dataset_id", "DATASET"
        )
        self.surprises = JsonlCollection(
            self.root / "surprises.jsonl", SurpriseRecord, "surprise_id", "SURPRISE"
        )
        self.edges = JsonlCollection(self.root / "edges.jsonl", HypothesisEdge, "edge_id", "EDGE")
        self.method_plans = JsonlCollection(
            self.root / "method_plans.jsonl", MethodPlanRecord, "plan_id", "PLAN"
        )
        self.runs = JsonlCollection(self.root / "runs.jsonl", ExecutionRun, "run_id", "RUN")
        self.verifications = JsonlCollection(
            self.root / "verifications.jsonl", VerificationRecord, "verification_id", "VERIFY"
        )
        self._collections = {
            "candidates": self.candidates,
            "papers": self.papers,
            "claims": self.claims,
            "tools": self.tools,
            "datasets": self.datasets,
            "surprises": self.surprises,
            "edges": self.edges,
            "method_plans": self.method_plans,
            "runs": self.runs,
            "verifications": self.verifications,
        }

    def collection(self, name: str) -> JsonlCollection:
        try:
            return self._collections[name]
        except KeyError as exc:
            raise KeyError(f"Unknown collection {name!r}; valid: {sorted(self._collections)}") from exc

    def counts(self) -> dict[str, int]:
        return {name: len(collection.all()) for name, collection in self._collections.items()}

    def index_path(self) -> Path:
        return self.root / "retrieval_index.sqlite"

    def state_files(self) -> dict[str, Path]:
        return {name: collection.path for name, collection in self._collections.items()}
