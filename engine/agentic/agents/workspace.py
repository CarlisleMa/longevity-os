"""Shared workspace for inter-agent communication.

All agents read from and write to the workspace using typed entries.
The workspace is the backbone of the multi-agent system — agents communicate
through structured data, not by reading each other's conversation history.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class StatisticalFinding:
    """A statistical result from comparing groups or testing associations."""
    feature: str
    groups: str                                # e.g. "study_group", "clinical_site"
    test: str                                  # e.g. "kruskal-wallis", "spearman"
    statistic: float
    pvalue: float
    effect_size: float
    effect_size_type: str                      # "eta_squared", "cohens_d", "r"
    adjusted_for: list[str] = field(default_factory=list)
    n_total: int = 0
    n_per_group: dict[str, int] = field(default_factory=dict)
    interpretation: str = ""
    agent_source: str = ""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ModalityObservation:
    """An observation from a modality agent about a participant or the cohort."""
    modality: str                              # "cgm", "ecg", "wearable", etc.
    participant_id: str | None = None           # None for population-level
    observation: str = ""                       # free text description
    metrics: dict[str, Any] = field(default_factory=dict)
    agent_source: str = ""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class Hypothesis:
    """A testable hypothesis proposed by a reasoning agent."""
    claim: str
    evidence_for: list[str] = field(default_factory=list)   # workspace entry IDs
    evidence_against: list[str] = field(default_factory=list)
    proposed_test: str = ""
    status: str = "proposed"                   # proposed, testing, supported, refuted
    agent_source: str = ""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class CausalRelation:
    """A causal relationship found between two variables."""
    cause: str
    effect: str
    method: str                                # "granger", "transfer_entropy", "pcmci"
    direction: str = "forward"                 # "forward", "reverse", "bidirectional"
    strength: float = 0.0
    pvalue: float = 1.0
    lag: str | None = None                     # e.g. "1 day", "30 min"
    participants_tested: int = 0
    agent_source: str = ""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class CouplingMeasure:
    """A pairwise coupling measurement between two physiological modalities.

    Represents a single coupling computation for one participant and one
    modality pair. Agents produce these during the coupling atlas pipeline
    and the workspace aggregates them into coupling matrices.
    """
    modality_a: str                            # "glucose", "hr", "activity", "sleep", "environment"
    modality_b: str
    participant_id: str
    method: str                                # "cross_correlation", "transfer_entropy", "wavelet_coherence", etc.
    value: float                               # coupling strength (r, R^2, bits, coherence)
    direction: str = "undirected"              # "undirected", "a_to_b", "b_to_a"
    lag: str = ""                              # optimal lag (e.g. "15 min", "1 day")
    frequency_band: str = ""                   # for wavelet: "ultra_fast", "fast", "circadian", "multi_day"
    pvalue: float | None = None
    confidence_interval: tuple[float, float] | None = None
    n_timepoints: int = 0                      # number of aligned timepoints used
    agent_source: str = ""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class CouplingNetwork:
    """A per-person physiological coupling network.

    Nodes are modalities (glucose, hr, activity, sleep, environment).
    Edges are coupling strengths from CouplingMeasure aggregation.
    Graph-theoretic biomarkers are computed from this network.
    """
    participant_id: str
    # Edge weights: dict mapping (modality_a, modality_b) -> mean coupling strength
    edges: dict[str, float] = field(default_factory=dict)
    # Graph-level biomarkers
    total_coupling_strength: float = 0.0       # mean of all edge weights
    global_efficiency: float = 0.0             # networkx global_efficiency
    modularity: float = 0.0
    graph_density: float = 0.0
    predictability_score: float = 0.0          # mean R^2 across cross-predictions (Direction B)
    coupling_asymmetry: float = 0.0            # mean |TE_fwd - TE_rev|
    # Node-level: which modality is the hub?
    node_strengths: dict[str, float] = field(default_factory=dict)
    hub_modality: str = ""                     # modality with highest node_strength
    # Coupling-based aging
    coupling_age_accel: float | None = None    # from the coupling clock (Direction C)
    agent_source: str = ""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class CriticVerdict:
    """A critic's assessment of a finding."""
    finding_id: str
    status: str                                # "PASS", "CONCERN", "FAIL"
    issues: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    raw_text: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class Workspace:
    """Shared mutable state across all agents in a session.

    Usage:
        ws = Workspace()
        fid = ws.add_finding(StatisticalFinding(feature="hba1c", ...))
        ws.get_findings(feature="hba1c")
        ws.summary()  # text summary for agent context injection
    """

    def __init__(self):
        self.findings: list[StatisticalFinding] = []
        self.observations: list[ModalityObservation] = []
        self.hypotheses: list[Hypothesis] = []
        self.causal_relations: list[CausalRelation] = []
        self.coupling_measures: list[CouplingMeasure] = []
        self.coupling_networks: list[CouplingNetwork] = []
        self.verdicts: list[CriticVerdict] = []
        self.dataframes: dict[str, Any] = {}  # named intermediate results

    def add_finding(self, f: StatisticalFinding) -> str:
        self.findings.append(f)
        return f.id

    def add_observation(self, o: ModalityObservation) -> str:
        self.observations.append(o)
        return o.id

    def add_hypothesis(self, h: Hypothesis) -> str:
        self.hypotheses.append(h)
        return h.id

    def add_causal(self, c: CausalRelation) -> str:
        self.causal_relations.append(c)
        return c.id

    def add_coupling(self, c: CouplingMeasure) -> str:
        self.coupling_measures.append(c)
        return c.id

    def add_coupling_network(self, n: CouplingNetwork) -> str:
        self.coupling_networks.append(n)
        return n.id

    def add_verdict(self, v: CriticVerdict) -> str:
        self.verdicts.append(v)
        return v.finding_id

    def get_findings(self, feature: str | None = None, agent: str | None = None) -> list[StatisticalFinding]:
        results = self.findings
        if feature:
            results = [f for f in results if f.feature == feature]
        if agent:
            results = [f for f in results if f.agent_source == agent]
        return results

    def get_observations(self, modality: str | None = None, participant_id: str | None = None) -> list[ModalityObservation]:
        results = self.observations
        if modality:
            results = [o for o in results if o.modality == modality]
        if participant_id:
            results = [o for o in results if o.participant_id == participant_id]
        return results

    def get_coupling(
        self,
        modality_a: str | None = None,
        modality_b: str | None = None,
        participant_id: str | None = None,
        method: str | None = None,
    ) -> list[CouplingMeasure]:
        """Query coupling measures with optional filters."""
        results = self.coupling_measures
        if modality_a:
            results = [c for c in results if c.modality_a == modality_a or c.modality_b == modality_a]
        if modality_b:
            results = [c for c in results if c.modality_a == modality_b or c.modality_b == modality_b]
        if participant_id:
            results = [c for c in results if c.participant_id == participant_id]
        if method:
            results = [c for c in results if c.method == method]
        return results

    def get_coupling_network(self, participant_id: str) -> CouplingNetwork | None:
        """Get the coupling network for a specific participant."""
        for n in self.coupling_networks:
            if n.participant_id == participant_id:
                return n
        return None

    def summary(self) -> str:
        """Text summary of workspace state for injection into agent prompts."""
        parts = []

        if self.findings:
            parts.append(f"=== {len(self.findings)} Statistical Findings ===")
            for f in self.findings:
                verdict = next((v for v in self.verdicts if v.finding_id == f.id), None)
                v_str = f" [{verdict.status}]" if verdict else ""
                adj = f" (adjusted for {', '.join(f.adjusted_for)})" if f.adjusted_for else ""
                parts.append(
                    f"  [{f.id}] {f.feature} by {f.groups}: "
                    f"{f.test} p={f.pvalue:.2e}, {f.effect_size_type}={f.effect_size:.3f}"
                    f"{adj}{v_str}"
                )

        if self.observations:
            parts.append(f"\n=== {len(self.observations)} Modality Observations ===")
            for o in self.observations:
                pid = f" (pid={o.participant_id})" if o.participant_id else " (cohort)"
                parts.append(f"  [{o.id}] {o.modality}{pid}: {o.observation[:120]}")

        if self.hypotheses:
            parts.append(f"\n=== {len(self.hypotheses)} Hypotheses ===")
            for h in self.hypotheses:
                parts.append(f"  [{h.id}] [{h.status}] {h.claim[:120]}")

        if self.causal_relations:
            parts.append(f"\n=== {len(self.causal_relations)} Causal Relations ===")
            for c in self.causal_relations:
                parts.append(
                    f"  [{c.id}] {c.cause} -> {c.effect} ({c.method}): "
                    f"p={c.pvalue:.2e}, strength={c.strength:.3f}"
                )

        if self.coupling_measures:
            # Summarize coupling measures by pair and method rather than listing all
            pair_counts: dict[str, int] = {}
            for cm in self.coupling_measures:
                key = f"{cm.modality_a}-{cm.modality_b}"
                pair_counts[key] = pair_counts.get(key, 0) + 1
            parts.append(f"\n=== {len(self.coupling_measures)} Coupling Measures ===")
            for pair, count in sorted(pair_counts.items()):
                parts.append(f"  {pair}: {count} measurements")

        if self.coupling_networks:
            parts.append(f"\n=== {len(self.coupling_networks)} Coupling Networks ===")
            # Show summary stats across networks
            strengths = [n.total_coupling_strength for n in self.coupling_networks]
            if strengths:
                import statistics
                parts.append(
                    f"  Total coupling strength: "
                    f"median={statistics.median(strengths):.3f}, "
                    f"range=[{min(strengths):.3f}, {max(strengths):.3f}]"
                )
            hubs = [n.hub_modality for n in self.coupling_networks if n.hub_modality]
            if hubs:
                from collections import Counter
                hub_counts = Counter(hubs).most_common(3)
                parts.append(f"  Most common hub: {hub_counts}")

        if not parts:
            return "(workspace is empty)"

        return "\n".join(parts)
