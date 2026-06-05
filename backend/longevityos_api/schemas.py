"""Pydantic response models — the API contract the frontend builds against."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class SystemScore(BaseModel):
    system: str            # e.g. "cardiac", "metabolic", "retinal"
    age_accel: float       # years; negative = younger than chronological
    percentile: Optional[float] = None
    status: str = "good"   # good | watch | risk


class CouplingMetric(BaseModel):
    key: str               # e.g. "glucose_hr_coupling"
    label: str
    value: float
    baseline: Optional[float] = None     # the user's own prior value
    delta_vs_baseline: Optional[float] = None
    unit: Optional[str] = None
    read: Optional[str] = None           # one-line plain-language interpretation
    evidence_card: Optional[str] = None  # KC-* id


class ScoreCard(BaseModel):
    chronological_age: float
    biological_age: float
    age_accel: float                     # biological - chronological
    age_accel_percentile: Optional[float] = None
    delta_vs_baseline: Optional[float] = None  # N-of-1 change in biological age
    as_of: str
    status: str = "good"


class GateVerdict(BaseModel):
    gate: str              # evidence_grounding | personalization | safety
    passed: bool
    note: str


class Observation(BaseModel):
    id: str
    text: str
    evidence_cards: List[str] = []
    as_of: str


class Intervention(BaseModel):
    id: str
    title: str
    rationale: str
    evidence_cards: List[str] = []
    gates: List[GateVerdict] = []
    expected_benefit: Optional[str] = None
    effort: Optional[str] = None         # low | medium | high
    status: str = "new"                  # new | accepted | dismissed | tracking
    reasoning_trace: Optional[str] = None


class KnowledgeCard(BaseModel):
    id: str
    title: str
    finding: str
    interpretation: str
    individual_application: str
    evidence_strength: str
    source: dict
    modalities: List[str] = []
    metrics: List[str] = []
    caveats: Optional[str] = None


class TimelineEvent(BaseModel):
    timestamp: str
    label: str
    biological_age: Optional[float] = None
    modalities_present: List[str] = []


class DashboardResponse(BaseModel):
    user_id: str
    display_name: str
    scorecard: ScoreCard
    systems: List[SystemScore] = []
    coupling: List[CouplingMetric] = []
    latest_observation: Optional[Observation] = None
    top_intervention: Optional[Intervention] = None


class UserSummary(BaseModel):
    user_id: str
    display_name: str
    is_demo: bool = False
    created_at: Optional[str] = None


class MetaResponse(BaseModel):
    version: str
    run_modes: dict
    knowledge_cards: int
    note: str
