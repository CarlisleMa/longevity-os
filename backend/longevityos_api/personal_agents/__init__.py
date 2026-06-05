"""Personalized multi-agent coach — the "imperial court" of health agents.

These are NOT the cohort discovery/research agents in engine/agentic. They are
per-user agents: each reads *your* profile and day and contributes domain advice,
coordinated by the Imperial Physician orchestrator, gated by the Medical Censor,
and synthesized by the Court Scribe. Mirrors the agent roster on longevity-os.xyz.
"""

from .context import build_context
from .orchestrator import ROSTER, consult

__all__ = ["build_context", "consult", "ROSTER"]
