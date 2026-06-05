"""Persistent memory system for the agent system.

Four memory types (inspired by BioMedAgent):
  - Workflow: successful analysis patterns
  - Finding: validated statistical results
  - Domain: clinical thresholds, guidelines
  - Constraint: dataset limitations

Memory persists across sessions as JSON in results/agent_memory/.
"""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from . import config


@dataclass
class WorkflowEntry:
    description: str
    code_pattern: str
    tags: list[str] = field(default_factory=list)
    uses: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class FindingEntry:
    feature: str
    summary: str
    pvalue: float
    effect_size: float
    critic_status: str          # "PASS", "CONCERN", "FAIL"
    session_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class DomainEntry:
    topic: str
    content: str
    source: str = ""            # citation or reference
    tags: list[str] = field(default_factory=list)


@dataclass
class ConstraintEntry:
    constraint: str
    reason: str
    severity: str = "hard"      # "hard" = never violate, "soft" = caveat


class Memory:
    """Persistent memory bank saved as JSON.

    Usage:
        mem = Memory()
        mem.add_workflow("Compare groups", "compare_groups(fm, feat, adjust_for=['age'])", ["cohort"])
        mem.save()
    """

    def __init__(self, memory_dir: Path | None = None):
        self.memory_dir = memory_dir or config.MEMORY_DIR
        self.memory_dir.mkdir(parents=True, exist_ok=True)

        self.workflows: list[WorkflowEntry] = []
        self.findings: list[FindingEntry] = []
        self.domain: list[DomainEntry] = []
        self.constraints: list[ConstraintEntry] = []

        self.load()

    # ── Add entries ────────────────────────────────────────────────────────

    def add_workflow(self, description: str, code_pattern: str, tags: list[str] | None = None):
        self.workflows.append(WorkflowEntry(
            description=description,
            code_pattern=code_pattern,
            tags=tags or [],
        ))

    def add_finding(self, feature: str, summary: str, pvalue: float,
                    effect_size: float, critic_status: str, session_id: str = ""):
        self.findings.append(FindingEntry(
            feature=feature, summary=summary, pvalue=pvalue,
            effect_size=effect_size, critic_status=critic_status,
            session_id=session_id,
        ))

    def add_domain(self, topic: str, content: str, source: str = "", tags: list[str] | None = None):
        self.domain.append(DomainEntry(
            topic=topic, content=content, source=source, tags=tags or [],
        ))

    def add_constraint(self, constraint: str, reason: str, severity: str = "hard"):
        self.constraints.append(ConstraintEntry(
            constraint=constraint, reason=reason, severity=severity,
        ))

    # ── Search ─────────────────────────────────────────────────────────────

    def search(self, query: str, memory_type: str | None = None) -> list[Any]:
        """Case-insensitive text search across memory entries."""
        q = query.lower()
        results = []

        if memory_type in (None, "workflow"):
            for w in self.workflows:
                if q in w.description.lower() or q in w.code_pattern.lower():
                    results.append(w)
        if memory_type in (None, "finding"):
            for f in self.findings:
                if q in f.feature.lower() or q in f.summary.lower():
                    results.append(f)
        if memory_type in (None, "domain"):
            for d in self.domain:
                if q in d.topic.lower() or q in d.content.lower():
                    results.append(d)
        if memory_type in (None, "constraint"):
            for c in self.constraints:
                if q in c.constraint.lower() or q in c.reason.lower():
                    results.append(c)
        return results

    def get_relevant(self, question: str, top_k: int = 5) -> str:
        """Get memory entries relevant to a question, formatted for prompt injection."""
        results = self.search(question)[:top_k]
        if not results:
            return ""

        parts = ["=== Relevant Memory ==="]
        for r in results:
            if isinstance(r, WorkflowEntry):
                parts.append(f"  [workflow] {r.description}: {r.code_pattern}")
            elif isinstance(r, FindingEntry):
                parts.append(f"  [finding] {r.feature}: {r.summary} (p={r.pvalue:.2e}, critic={r.critic_status})")
            elif isinstance(r, DomainEntry):
                parts.append(f"  [domain] {r.topic}: {r.content}")
            elif isinstance(r, ConstraintEntry):
                parts.append(f"  [constraint/{r.severity}] {r.constraint}: {r.reason}")
        return "\n".join(parts)

    # ── Persistence ────────────────────────────────────────────────────────

    def save(self):
        """Save all memory to JSON files."""
        for name, entries in [
            ("workflows", self.workflows),
            ("findings", self.findings),
            ("domain", self.domain),
            ("constraints", self.constraints),
        ]:
            path = self.memory_dir / f"{name}.json"
            path.write_text(json.dumps([asdict(e) for e in entries], indent=2))

    def load(self):
        """Load memory from JSON files if they exist."""
        mapping = {
            "workflows": (self.workflows, WorkflowEntry),
            "findings": (self.findings, FindingEntry),
            "domain": (self.domain, DomainEntry),
            "constraints": (self.constraints, ConstraintEntry),
        }
        for name, (target_list, cls) in mapping.items():
            path = self.memory_dir / f"{name}.json"
            if path.exists():
                data = json.loads(path.read_text())
                target_list.clear()
                target_list.extend(cls(**entry) for entry in data)

    # ── Summary ────────────────────────────────────────────────────────────

    def summary(self) -> str:
        return (
            f"Memory: {len(self.workflows)} workflows, {len(self.findings)} findings, "
            f"{len(self.domain)} domain entries, {len(self.constraints)} constraints"
        )


def create_default_memory() -> Memory:
    """Create memory pre-seeded with AI-READI domain knowledge and constraints."""
    mem = Memory()

    # Only seed if empty (fresh install)
    if mem.constraints:
        return mem

    # ── Dataset constraints ────────────────────────────────────────────────
    mem.add_constraint(
        "Sex is redacted in the public AI-READI release",
        "Cannot compute eGFR (CKD-EPI 2021), MetS (ATP III), ASCVD risk, "
        "or any metric with sex-specific thresholds.",
        severity="hard",
    )
    mem.add_constraint(
        "Cross-sectional design: 1 visit per participant",
        "No longitudinal trajectories. The ~10-day continuous monitoring window "
        "enables within-person time-series analysis but not multi-visit tracking.",
        severity="hard",
    )
    mem.add_constraint(
        "3 clinical sites with potential confounding",
        "UW (Seattle), UCSD (San Diego), UAB (Birmingham). Always check site bias "
        "with site_bias_check() or stratify by clinical_site.",
        severity="soft",
    )
    mem.add_constraint(
        "Age confounds most group comparisons",
        "Insulin-dependent participants are older on average. Always adjust for age "
        "when comparing across study_group.",
        severity="soft",
    )

    # ── Domain knowledge ───────────────────────────────────────────────────
    mem.add_domain(
        "CGM consensus targets",
        "TIR >70%, TBR <4% (level 1) / <1% (level 2), TAR <25% (level 1) / <5% (level 2). "
        "CV >=36% = unstable glycemia. GRI 0-100 composite.",
        source="Battelino et al., Diabetes Care 2023",
        tags=["cgm", "glycemia"],
    )
    mem.add_domain(
        "HRV from ultra-short ECG",
        "RMSSD validated for 10-sec strips (r=0.85 vs 5-min, Munoz 2015). "
        "SDNN unreliable at 11 seconds. LF/HF ratio not meaningful. HF power marginal.",
        source="Munoz 2015 PLOS ONE; Shaffer & Ginsberg 2017 Front Public Health",
        tags=["ecg", "hrv"],
    )
    mem.add_domain(
        "Circadian rhythm metrics",
        "IS (interdaily stability): 0=random, 1=identical daily pattern. "
        "IV (intradaily variability): higher=more fragmented. "
        "RA (relative amplitude): (M10-L5)/(M10+L5), closer to 1 = stronger rhythm. "
        "RA declines with aging and disease.",
        source="Witting 1990; Van Someren 1999",
        tags=["wearable", "circadian"],
    )
    mem.add_domain(
        "Insulin resistance indices",
        "HOMA-IR = (insulin * glucose) / 405 (>2.5 = IR). "
        "QUICKI = 1/(log10(insulin) + log10(glucose)). "
        "TyG = ln(TG * glucose) / 2 (>8.5 = IR; /2 is OUTSIDE the ln per 2020 correction). "
        "HOMA-beta denominator requires glucose in mmol/L (divide mg/dL by 18.0182).",
        source="Matthews 1985; Katz 2000; Simental-Mendia 2008",
        tags=["clinical", "insulin"],
    )
    mem.add_domain(
        "Garmin sleep staging limitations",
        "Consumer-grade, NOT PSG-equivalent. Moderate TST accuracy but poor epoch-by-epoch "
        "stage agreement with PSG (specificity 29-52%). Not FDA-cleared for diagnostics.",
        source="Nunez-Cortes 2024 JMIR; Menghini 2025 Sleep Advances",
        tags=["wearable", "sleep"],
    )
    mem.add_domain(
        "PM2.5 air quality thresholds",
        "EPA AQI breakpoints (May 2024): Good <=9.0 ug/m3, Moderate <=35.4, "
        "USG <=55.4, Unhealthy <=125.4. WHO 2021 24-h guideline: 15 ug/m3. "
        "WHO annual guideline: 5 ug/m3.",
        source="EPA 2024; WHO 2021 Global AQGs",
        tags=["environment", "air_quality"],
    )
    mem.add_domain(
        "Retinal aging",
        "Retinal age gap (RAG) = predicted retinal age - chronological age. "
        "+1y RAG associated with higher mortality, CVD, dementia risk. "
        "MAE of fundus-based models: 2.78-3.39 years.",
        source="Zhu 2023 Br J Ophthalmol; Nusinovici 2022 Age Ageing",
        tags=["retinal", "aging"],
    )

    # ── Workflow patterns ──────────────────────────────────────────────────
    mem.add_workflow(
        "Compare a feature across diabetes groups",
        "from scripts.features import load_feature_matrix\n"
        "from scripts.cohort import compare_groups\n"
        "fm = load_feature_matrix()\n"
        "result = compare_groups(fm, 'FEATURE', adjust_for=['age'])",
        tags=["comparison", "cohort"],
    )
    mem.add_workflow(
        "Check for site bias",
        "from scripts.cohort import site_bias_check\n"
        "bias = site_bias_check(fm, features=['FEATURE'])",
        tags=["validation", "site_bias"],
    )
    mem.add_workflow(
        "Load aligned multimodal time series for one participant",
        "from scripts.multimodal import get_participant\n"
        "p = get_participant('PID')\n"
        "aligned = p.aligned_timeseries(freq='5min')",
        tags=["multimodal", "timeseries"],
    )

    mem.save()
    return mem
