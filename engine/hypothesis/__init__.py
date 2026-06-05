"""Hypothesis-driven scientific discovery pipeline for AI-READI.

Agent components:
    ProposerAgent          — generates hypotheses from literature + findings
    HypothesisCriticAgent  — validates against dataset constraints
    ExecutorAgent          — generates scripts, submits Slurm, collects results
    VerifierAgent          — 9 rule-based checks + LLM interpretation

Run autonomously:
    python -m hypothesis_driven --max-cycles 5
    python -m hypothesis_driven --dry-run
"""

from .schemas import (
    CriticVerdict,
    FeasibilityAssessment,
    Hypothesis,
    HypothesisResult,
    LiteratureRef,
    SensitivityCheck,
    TestPlan,
)
from .workspace import HypothesisWorkspace
from .proposer import ProposerAgent
from .hypothesis_critic import HypothesisCriticAgent
from .executor import ExecutorAgent
from .verifier import VerifierAgent

__all__ = [
    "CriticVerdict",
    "ExecutorAgent",
    "FeasibilityAssessment",
    "Hypothesis",
    "HypothesisCriticAgent",
    "HypothesisResult",
    "HypothesisWorkspace",
    "LiteratureRef",
    "ProposerAgent",
    "SensitivityCheck",
    "TestPlan",
    "VerifierAgent",
]
