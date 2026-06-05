"""Health coach — a personalized multi-agent consult.

A Care Coordinator routes the question to the relevant specialist agents (Nutrition,
Movement, Sleep & Circadian, Biosignals, Biomarkers, Supplements, Experiments), a
Safety Reviewer gates it, and Synthesis composes the answer — all grounded in the
user's own profile and day. These are personal agents, distinct from the cohort
discovery agents in engine/agentic.

If ANTHROPIC_API_KEY is set, `_answer_live` is where each agent is backed by a real
model (sending only derived summaries, never raw PHI).
"""

from __future__ import annotations

from typing import Optional

from ..config import agent_live
from ..personal_agents import build_context, consult
from ..personal_agents.orchestrator import roster_cards
from . import store


def answer(user_id: str, message: str, history: Optional[list] = None) -> Optional[dict]:
    kb = store.load_kb(user_id)
    if kb is None:
        return None
    if agent_live():
        try:
            return _answer_live(kb, message, history or [])
        except Exception:
            pass  # graceful fallback to the grounded multi-agent consult
    return consult(build_context(kb), message or "")


def roster() -> list[dict]:
    """The full care team, for a 'meet your agents' view."""
    return roster_cards()


def _answer_live(kb: dict, message: str, history: list) -> dict:  # pragma: no cover
    """Back each agent with a real model. Send only derived facts, never raw PHI."""
    raise NotImplementedError("Live coach not wired (no ANTHROPIC_API_KEY).")
