"""Structured records for the hypothesis-first agentic discovery system.

These schemas are deliberately separate from ``hypothesis_driven.schemas``.
The older package remains the legacy prototype; this package adds durable
registries for candidates, literature, tools, datasets, surprises, evidence,
and graph relationships that future agents can retrieve before reasoning.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields, is_dataclass
from datetime import datetime, timezone
from typing import Any, TypeVar


T = TypeVar("T")


CANDIDATE_STATUSES = [
    "candidate",
    "enriched",
    "critiqued",
    "feasible",
    "method_planned",
    "registered",
    "rejected",
    "archived_duplicate",
]

ORIGIN_TYPES = [
    "human",
    "literature",
    "data_analysis",
    "critic",
    "surprise",
    "tool",
    "dataset",
    "agent_round",
    "legacy_migration",
]

EDGE_TYPES = [
    "supports",
    "contradicts",
    "refines",
    "extends",
    "duplicates",
    "depends_on",
    "follows_up",
    "generated_from",
    "uses_evidence",
]

VERDICTS = ["pass", "concern", "fail", "inconclusive", "not_checked"]
RUN_STATUSES = ["planned", "submitted", "running", "completed", "failed", "verified", "archived"]
PLAN_STATUSES = ["draft", "registered", "ready", "rejected", "obsolete"]


def now_utc() -> str:
    """Return a stable UTC timestamp for persisted JSON records."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def record_to_dict(record: Any) -> dict[str, Any]:
    if is_dataclass(record):
        return asdict(record)
    if isinstance(record, dict):
        return dict(record)
    raise TypeError(f"Unsupported record type: {type(record)!r}")


def record_from_dict(cls: type[T], data: dict[str, Any]) -> T:
    valid = {field.name for field in fields(cls)}
    return cls(**{key: value for key, value in data.items() if key in valid})


@dataclass
class HypothesisCandidate:
    """A quarantined hypothesis idea before it becomes executable."""

    candidate_id: str = ""
    created_at: str = field(default_factory=now_utc)
    updated_at: str = field(default_factory=now_utc)
    origin_type: str = "human"
    origin_agent: str = "human"
    origin_detail: str = ""
    trigger_artifacts: list[str] = field(default_factory=list)

    title: str = ""
    claim: str = ""
    mechanism: str = ""
    expected_direction: str = ""
    required_modalities: list[str] = field(default_factory=list)
    primary_outcome: str = ""
    confounders: list[str] = field(default_factory=list)
    negative_controls: list[str] = field(default_factory=list)
    leakage_risks: list[str] = field(default_factory=list)

    status: str = "candidate"
    priority: float = 0.5
    needs: list[str] = field(default_factory=list)
    related_papers: list[str] = field(default_factory=list)
    related_claims: list[str] = field(default_factory=list)
    related_tools: list[str] = field(default_factory=list)
    related_datasets: list[str] = field(default_factory=list)
    parent_ids: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    notes: str = ""

    def search_text(self) -> str:
        parts = [
            self.title,
            self.claim,
            self.mechanism,
            self.expected_direction,
            self.primary_outcome,
            " ".join(self.required_modalities),
            " ".join(self.confounders),
            " ".join(self.negative_controls),
            " ".join(self.leakage_risks),
            " ".join(self.needs),
            " ".join(self.tags),
            self.notes,
        ]
        return " ".join(part for part in parts if part)


@dataclass
class PaperRecord:
    paper_id: str = ""
    created_at: str = field(default_factory=now_utc)
    updated_at: str = field(default_factory=now_utc)
    title: str = ""
    authors: list[str] = field(default_factory=list)
    year: int | None = None
    venue: str = ""
    doi: str = ""
    url: str = ""
    abstract: str = ""
    topics: list[str] = field(default_factory=list)
    modalities: list[str] = field(default_factory=list)
    aging_relevance: str = ""
    disease_relevance: str = ""
    evidence_level: str = ""
    source: str = ""
    tags: list[str] = field(default_factory=list)
    notes: str = ""

    def search_text(self) -> str:
        return " ".join(
            part
            for part in [
                self.title,
                " ".join(self.authors),
                str(self.year or ""),
                self.venue,
                self.doi,
                self.abstract,
                " ".join(self.topics),
                " ".join(self.modalities),
                self.aging_relevance,
                self.disease_relevance,
                self.evidence_level,
                " ".join(self.tags),
                self.notes,
            ]
            if part
        )


@dataclass
class ExtractedClaim:
    claim_id: str = ""
    created_at: str = field(default_factory=now_utc)
    updated_at: str = field(default_factory=now_utc)
    paper_id: str = ""
    statement: str = ""
    direction: str = ""
    population: str = ""
    modality: str = ""
    outcome: str = ""
    mechanism: str = ""
    methods: list[str] = field(default_factory=list)
    caveats: list[str] = field(default_factory=list)
    supports_hypotheses: list[str] = field(default_factory=list)
    contradicts_hypotheses: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)

    def search_text(self) -> str:
        return " ".join(
            part
            for part in [
                self.statement,
                self.direction,
                self.population,
                self.modality,
                self.outcome,
                self.mechanism,
                " ".join(self.methods),
                " ".join(self.caveats),
                " ".join(self.tags),
            ]
            if part
        )


@dataclass
class ToolRecord:
    tool_id: str = ""
    created_at: str = field(default_factory=now_utc)
    updated_at: str = field(default_factory=now_utc)
    name: str = ""
    version: str = ""
    source_url: str = ""
    purpose: str = ""
    task_types: list[str] = field(default_factory=list)
    modalities: list[str] = field(default_factory=list)
    inputs: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    install_notes: str = ""
    validation_notes: str = ""
    limitations: list[str] = field(default_factory=list)
    license: str = ""
    tags: list[str] = field(default_factory=list)

    def search_text(self) -> str:
        return " ".join(
            part
            for part in [
                self.name,
                self.version,
                self.purpose,
                " ".join(self.task_types),
                " ".join(self.modalities),
                " ".join(self.inputs),
                " ".join(self.outputs),
                self.install_notes,
                self.validation_notes,
                " ".join(self.limitations),
                self.license,
                " ".join(self.tags),
            ]
            if part
        )


@dataclass
class DatasetRecord:
    dataset_id: str = ""
    created_at: str = field(default_factory=now_utc)
    updated_at: str = field(default_factory=now_utc)
    name: str = ""
    source_url: str = ""
    population: str = ""
    modalities: list[str] = field(default_factory=list)
    outcomes: list[str] = field(default_factory=list)
    access_status: str = ""
    sample_size: int | None = None
    age_range: str = ""
    disease_groups: list[str] = field(default_factory=list)
    time_resolution: str = ""
    strengths: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    leakage_risks: list[str] = field(default_factory=list)
    external_validation_uses: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    notes: str = ""

    def search_text(self) -> str:
        return " ".join(
            part
            for part in [
                self.name,
                self.population,
                " ".join(self.modalities),
                " ".join(self.outcomes),
                self.access_status,
                str(self.sample_size or ""),
                self.age_range,
                " ".join(self.disease_groups),
                self.time_resolution,
                " ".join(self.strengths),
                " ".join(self.limitations),
                " ".join(self.leakage_risks),
                " ".join(self.external_validation_uses),
                " ".join(self.tags),
                self.notes,
            ]
            if part
        )


@dataclass
class SurpriseRecord:
    surprise_id: str = ""
    created_at: str = field(default_factory=now_utc)
    updated_at: str = field(default_factory=now_utc)
    origin_artifact: str = ""
    summary: str = ""
    details: str = ""
    modality: str = ""
    signal: str = ""
    candidate_ids: list[str] = field(default_factory=list)
    hypothesis_ids: list[str] = field(default_factory=list)
    severity: str = "medium"
    p_hacking_risk: str = ""
    follow_up_needed: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)

    def search_text(self) -> str:
        return " ".join(
            part
            for part in [
                self.summary,
                self.details,
                self.modality,
                self.signal,
                self.severity,
                self.p_hacking_risk,
                " ".join(self.follow_up_needed),
                " ".join(self.tags),
            ]
            if part
        )


@dataclass
class MethodPlanRecord:
    plan_id: str = ""
    created_at: str = field(default_factory=now_utc)
    updated_at: str = field(default_factory=now_utc)
    target_id: str = ""
    target_type: str = "candidate"
    objective: str = ""
    inputs: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    split_id: str = ""
    adjustment_set: list[str] = field(default_factory=list)
    negative_controls: list[str] = field(default_factory=list)
    leakage_checks: list[str] = field(default_factory=list)
    statistical_tests: list[str] = field(default_factory=list)
    execution_steps: list[str] = field(default_factory=list)
    script_path: str = ""
    command_template: str = ""
    status: str = "draft"
    created_by: str = "human"
    notes: str = ""

    def search_text(self) -> str:
        return " ".join(
            [
                self.target_id,
                self.target_type,
                self.objective,
                " ".join(self.inputs),
                " ".join(self.outputs),
                self.split_id,
                " ".join(self.adjustment_set),
                " ".join(self.negative_controls),
                " ".join(self.leakage_checks),
                " ".join(self.statistical_tests),
                " ".join(self.execution_steps),
                self.script_path,
                self.command_template,
                self.status,
                self.created_by,
                self.notes,
            ]
        )


@dataclass
class ExecutionRun:
    run_id: str = ""
    created_at: str = field(default_factory=now_utc)
    updated_at: str = field(default_factory=now_utc)
    hypothesis_id: str = ""
    candidate_id: str = ""
    split_id: str = ""
    script_path: str = ""
    command: str = ""
    artifacts: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    mechanical_checks: dict[str, Any] = field(default_factory=dict)
    status: str = "planned"
    notes: str = ""

    def search_text(self) -> str:
        return " ".join(
            [
                self.hypothesis_id,
                self.candidate_id,
                self.split_id,
                self.script_path,
                self.command,
                " ".join(self.artifacts),
                str(self.metrics),
                str(self.mechanical_checks),
                self.status,
                self.notes,
            ]
        )


@dataclass
class VerificationRecord:
    verification_id: str = ""
    created_at: str = field(default_factory=now_utc)
    updated_at: str = field(default_factory=now_utc)
    target_id: str = ""
    target_type: str = ""
    verdict: str = "not_checked"
    checks: dict[str, Any] = field(default_factory=dict)
    blockers: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    reviewer: str = ""

    def search_text(self) -> str:
        return " ".join(
            [
                self.target_id,
                self.target_type,
                self.verdict,
                str(self.checks),
                " ".join(self.blockers),
                " ".join(self.recommendations),
                self.reviewer,
            ]
        )


@dataclass
class HypothesisEdge:
    edge_id: str = ""
    created_at: str = field(default_factory=now_utc)
    updated_at: str = field(default_factory=now_utc)
    source_id: str = ""
    target_id: str = ""
    edge_type: str = ""
    rationale: str = ""
    evidence_ids: list[str] = field(default_factory=list)
    confidence: float = 0.5
    created_by: str = "human"
