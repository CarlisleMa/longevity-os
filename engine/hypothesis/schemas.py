"""Structured schemas for hypothesis-driven scientific discovery.

This module defines the data model for the full hypothesis lifecycle:
  proposed -> critiqued -> validated/rejected -> queued -> executing -> completed -> verified

Each hypothesis is a self-contained scientific claim with:
  - Mechanistic grounding (why we expect this)
  - Literature support (prior work)
  - Feasibility assessment (can we test this with AI-READI?)
  - Test plan (how to test)
  - Results (what we found)
  - Critic verdict (is this rigorous?)
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Literature & Feasibility
# ---------------------------------------------------------------------------

@dataclass
class LiteratureRef:
    """A supporting paper for a hypothesis."""
    title: str
    authors: str  # "First et al."
    journal: str
    year: int
    key_finding: str
    relevance: str  # How it supports or informs this hypothesis
    doi: str = ""
    url: str = ""


@dataclass
class FeasibilityAssessment:
    """Assessment of whether a hypothesis is testable with AI-READI."""
    required_modalities: list[str] = field(default_factory=list)
    participant_coverage: float = 0.0  # estimated fraction with required data
    time_resolution_needed: str = ""  # "5-min", "hourly", "daily"
    analysis_timescale: str = ""  # "acute (5-60min)", "circadian (12-36h)", "multi-day (2-10d)"
    computational_cost: str = "medium"  # low/medium/high
    statistical_power: str = ""  # assessment of N sufficiency
    key_challenges: list[str] = field(default_factory=list)
    dataset_limitations: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Test Plan & Results
# ---------------------------------------------------------------------------

@dataclass
class TestPlan:
    """Concrete plan for testing a hypothesis."""
    primary_method: str  # The main analytical method
    implementation_steps: list[str] = field(default_factory=list)
    confounders_to_adjust: list[str] = field(default_factory=list)
    time_window: str = ""  # Which temporal window to analyze
    frequency_bands: list[str] = field(default_factory=list)  # For multi-scale analyses
    expected_effect_size: str = ""
    success_criterion: str = ""  # What would support the hypothesis
    refutation_criterion: str = ""  # What would refute it
    sensitivity_checks: list[str] = field(default_factory=list)
    secondary_methods: list[str] = field(default_factory=list)


@dataclass
class SensitivityCheck:
    """A robustness check on a result."""
    name: str  # e.g., "Adjusted for HbA1c + BMI"
    passed: bool = False
    effect_preserved: bool = False  # Does the effect survive this adjustment?
    details: str = ""


@dataclass
class HypothesisResult:
    """Structured results from testing a hypothesis."""
    method_used: str = ""
    sample_size: int = 0
    # Primary result
    primary_metric: str = ""  # e.g., "Spearman r", "AUROC", "Cohen's d"
    primary_value: float = 0.0
    effect_size: float = 0.0
    effect_size_type: str = ""  # "cohen_d", "r", "eta_squared", "auroc"
    p_value: float = 1.0
    fdr_p_value: float = 1.0
    confidence_interval: tuple[float, float] | None = None
    # Context
    confounders_adjusted: list[str] = field(default_factory=list)
    sensitivity_checks: list[SensitivityCheck] = field(default_factory=list)
    # Subgroup results (diabetes severity gradient)
    group_values: dict[str, float] = field(default_factory=dict)  # group -> metric
    group_ns: dict[str, int] = field(default_factory=dict)  # group -> N
    # Interpretation
    interpretation: str = ""
    surprises: str = ""  # What was unexpected
    # Artifacts
    output_files: list[str] = field(default_factory=list)
    figure_paths: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Critic Verdict
# ---------------------------------------------------------------------------

@dataclass
class CriticVerdict:
    """A critic agent's assessment of a hypothesis result."""
    verdict: str = "pending"  # PASS, CONCERN, FAIL
    # Dimensional scores (0-1)
    statistical_rigor: float = 0.0
    biological_plausibility: float = 0.0
    novelty: float = 0.0
    importance: float = 0.0
    reproducibility: float = 0.0
    # Issues and suggestions
    issues: list[str] = field(default_factory=list)
    confounders_missed: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    # Composite ranking
    overall_score: float = 0.0  # Weighted composite, 0-1


# ---------------------------------------------------------------------------
# The Hypothesis (core entity)
# ---------------------------------------------------------------------------

CATEGORIES = [
    "temporal_coupling",      # Inter-organ coupling dynamics at specific timescales
    "frequency_coupling",     # Frequency-dependent (wavelet) coupling analysis
    "causal_architecture",    # Directed information flow between systems
    "event_dynamics",         # Event-triggered responses (meals, exercise, waking)
    "circadian_organization", # Phase alignment of rhythms across systems
    "environmental_modulation",  # PM2.5/temp/light modulation of physiology
    "physiotype_discovery",   # Coupling-based phenotyping and subtyping
    "structural_dynamic",     # Bridge between structural imaging and dynamic coupling
    "complexity_loss",        # Multiscale entropy and complexity degradation
    "resilience",             # Recovery dynamics, perturbation response
]

STATUSES = [
    "proposed",    # Generated by proposer agent
    "critiqued",   # Reviewed by critic agent
    "validated",   # Passed critic review, ready for execution
    "rejected",    # Failed critic review (not feasible or not grounded)
    "queued",      # In the execution queue
    "executing",   # Currently being tested
    "completed",   # Test finished, results available
    "verified",    # Results verified by critic
    "supported",   # Hypothesis supported by evidence
    "refuted",     # Hypothesis refuted by evidence
    "inconclusive",  # Evidence is ambiguous
]


@dataclass
class Hypothesis:
    """A complete hypothesis with its full lifecycle."""
    # Identity
    id: str = field(default_factory=lambda: f"H-{str(uuid.uuid4())[:6]}")
    title: str = ""
    category: str = ""  # One of CATEGORIES
    # Scientific content
    statement: str = ""  # The specific, falsifiable claim
    mechanism: str = ""  # Proposed biological mechanism (WHY we expect this)
    predictions: list[str] = field(default_factory=list)  # Specific testable predictions
    # Grounding
    literature: list[LiteratureRef] = field(default_factory=list)
    feasibility: FeasibilityAssessment = field(default_factory=FeasibilityAssessment)
    # Priority and status
    priority: float = 0.5  # 0-1, set by critic
    status: str = "proposed"
    # Test plan (filled by executor)
    test_plan: TestPlan | None = None
    # Results (filled after execution)
    results: HypothesisResult | None = None
    # Critic verdict (filled after verification)
    critic_verdict: CriticVerdict | None = None
    # Relationships
    depends_on: list[str] = field(default_factory=list)  # Hypothesis IDs
    contradicts: list[str] = field(default_factory=list)  # Hypothesis IDs
    supports: list[str] = field(default_factory=list)  # Hypothesis IDs
    # Metadata
    source: str = ""  # "proposer", "migrated", "user"
    created: str = field(default_factory=lambda: datetime.now().isoformat())
    updated: str = field(default_factory=lambda: datetime.now().isoformat())
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Hypothesis":
        import dataclasses as _dc

        def _safe_init(klass, data: dict) -> Any:
            """Construct a dataclass, ignoring unknown keys."""
            valid = {f.name for f in _dc.fields(klass)}
            return klass(**{k: v for k, v in data.items() if k in valid})

        # Reconstruct nested dataclasses
        if d.get("literature"):
            d["literature"] = [_safe_init(LiteratureRef, r) if isinstance(r, dict) else r for r in d["literature"]]
        if d.get("feasibility") and isinstance(d["feasibility"], dict):
            d["feasibility"] = _safe_init(FeasibilityAssessment, d["feasibility"])
        if d.get("test_plan") and isinstance(d["test_plan"], dict):
            d["test_plan"] = _safe_init(TestPlan, d["test_plan"])
        if d.get("results") and isinstance(d["results"], dict):
            if d["results"].get("sensitivity_checks"):
                d["results"]["sensitivity_checks"] = [
                    _safe_init(SensitivityCheck, s) if isinstance(s, dict) else s
                    for s in d["results"]["sensitivity_checks"]
                ]
            if d["results"].get("confidence_interval"):
                d["results"]["confidence_interval"] = tuple(d["results"]["confidence_interval"])
            d["results"] = _safe_init(HypothesisResult, d["results"])
        if d.get("critic_verdict") and isinstance(d["critic_verdict"], dict):
            d["critic_verdict"] = _safe_init(CriticVerdict, d["critic_verdict"])

        # Filter unknown top-level keys too
        valid_top = {f.name for f in _dc.fields(cls)}
        return cls(**{k: v for k, v in d.items() if k in valid_top})

    def summary(self) -> str:
        """One-line summary for display."""
        prio = f"P={self.priority:.2f}" if self.priority else ""
        verdict = ""
        if self.critic_verdict:
            verdict = f" [{self.critic_verdict.verdict}:{self.critic_verdict.overall_score:.2f}]"
        return f"[{self.id}] [{self.status}] {prio} {self.title}{verdict}"

    def full_report(self) -> str:
        """Multi-line structured report."""
        lines = [
            f"# {self.title}",
            f"**ID:** {self.id}  |  **Category:** {self.category}  |  **Status:** {self.status}  |  **Priority:** {self.priority:.2f}",
            "",
            f"## Hypothesis",
            self.statement,
            "",
            f"## Mechanism",
            self.mechanism,
            "",
        ]
        if self.predictions:
            lines.append("## Predictions")
            for i, p in enumerate(self.predictions, 1):
                lines.append(f"{i}. {p}")
            lines.append("")
        if self.literature:
            lines.append(f"## Literature ({len(self.literature)} refs)")
            for ref in self.literature:
                lines.append(f"- {ref.authors} ({ref.year}), {ref.journal}: {ref.key_finding}")
            lines.append("")
        if self.test_plan:
            lines.append("## Test Plan")
            lines.append(f"**Method:** {self.test_plan.primary_method}")
            lines.append(f"**Time window:** {self.test_plan.time_window}")
            lines.append(f"**Confounders:** {', '.join(self.test_plan.confounders_to_adjust)}")
            lines.append(f"**Success criterion:** {self.test_plan.success_criterion}")
            lines.append("")
        if self.results:
            lines.append("## Results")
            lines.append(f"**Method:** {self.results.method_used}")
            lines.append(f"**N:** {self.results.sample_size}")
            lines.append(f"**{self.results.primary_metric}:** {self.results.primary_value}")
            lines.append(f"**Effect size ({self.results.effect_size_type}):** {self.results.effect_size}")
            lines.append(f"**p-value:** {self.results.p_value:.2e} (FDR: {self.results.fdr_p_value:.2e})")
            if self.results.group_values:
                lines.append("**By group:**")
                for g, v in self.results.group_values.items():
                    lines.append(f"  - {g}: {v:.4f}")
            lines.append(f"**Interpretation:** {self.results.interpretation}")
            lines.append("")
        if self.critic_verdict:
            lines.append("## Critic Verdict")
            lines.append(f"**Verdict:** {self.critic_verdict.verdict}")
            lines.append(f"**Scores:** rigor={self.critic_verdict.statistical_rigor:.2f}, "
                         f"novelty={self.critic_verdict.novelty:.2f}, "
                         f"importance={self.critic_verdict.importance:.2f}, "
                         f"overall={self.critic_verdict.overall_score:.2f}")
            if self.critic_verdict.issues:
                lines.append("**Issues:**")
                for issue in self.critic_verdict.issues:
                    lines.append(f"  - {issue}")
            lines.append("")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------

def save_hypothesis(h: Hypothesis, directory: str | Path) -> Path:
    """Save a hypothesis to a JSON file."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{h.id}.json"
    with open(path, "w") as f:
        json.dump(h.to_dict(), f, indent=2, default=str)
    return path


def load_hypothesis(path: str | Path) -> Hypothesis:
    """Load a hypothesis from a JSON file."""
    with open(path) as f:
        return Hypothesis.from_dict(json.load(f))


def load_all_hypotheses(directory: str | Path) -> list[Hypothesis]:
    """Load all hypotheses from a directory."""
    directory = Path(directory)
    hypotheses = []
    for path in sorted(directory.glob("H-*.json")):
        hypotheses.append(load_hypothesis(path))
    return hypotheses
