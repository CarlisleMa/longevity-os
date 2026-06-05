"""Agent reasoning over a user's state.

Representative mode (default): surface the salient coupling deviation and cite its evidence card —
deterministic, no key required. Agent-live mode (ANTHROPIC_API_KEY set) is where you wire the
engine's agentic_discovery runtime; only derived features/summaries should be sent to the model,
never raw PHI (see docs/BUILD_GUIDE.md Phase 3).
"""

from __future__ import annotations

from typing import Optional

from ..config import agent_live
from . import knowledge_service, store


def observations(user_id: str) -> Optional[list[dict]]:
    kb = store.load_kb(user_id)
    if kb is None:
        return None
    return kb.get("observations", [])


def generate_observation(user_id: str) -> Optional[dict]:
    """Produce one fresh observation from the user's most deviating coupling metric."""
    kb = store.load_kb(user_id)
    if kb is None:
        return None

    if agent_live():
        try:
            return _generate_live(kb)
        except Exception:
            pass  # fall back to representative; honest degradation

    coupling = kb.get("coupling", [])
    if not coupling:
        return (kb.get("observations") or [None])[-1]

    def deviation(c):
        d = c.get("delta_vs_baseline")
        return abs(d) if d is not None else 0.0

    worst = max(coupling, key=deviation)
    card_id = worst.get("evidence_card")
    card = knowledge_service.get_card(card_id) if card_id else None
    direction = "below" if (worst.get("delta_vs_baseline") or 0) < 0 else "above"
    text = (
        f"{worst.get('label', worst['key'])} is {abs(worst.get('delta_vs_baseline') or 0):.2f} "
        f"{direction} your baseline. "
    )
    if card:
        text += f"In AI-READI, {card['interpretation'].rstrip('.').lower()}."
    return {
        "id": "OBS-live",
        "text": text,
        "evidence_cards": [card_id] if card_id else [],
        "as_of": kb.get("scorecard", {}).get("as_of", ""),
    }


def _generate_live(kb: dict) -> dict:  # pragma: no cover - wiring point for Phase 3
    """Wire engine/agentic here. Send ONLY derived features/summaries, never raw PHI."""
    raise NotImplementedError("Agent-live not wired yet (Phase 3).")
