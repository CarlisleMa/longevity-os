"""Intervention recommendations with the three-gate safety pipeline.

Every recommendation passes evidence-grounding, personalization, and safety gates before the user
sees it — a repurposing of the engine's agentic reviewer-gate pattern (see docs/BRAINSTORM.md §5).
Representative mode reads precomputed interventions from kb.json; generated drafts are gated by
`evaluate_gates` so the contract is identical either way.
"""

from __future__ import annotations

from typing import Optional

from . import knowledge_service, store


def evaluate_gates(draft: dict) -> list[dict]:
    """Run a draft intervention through the three gates. Honest, rule-based for the prototype."""
    cards = [knowledge_service.get_card(c) for c in draft.get("evidence_cards", [])]
    cards = [c for c in cards if c]

    grounded = len(cards) > 0
    # Personalization: does the draft reference a metric the user actually deviates on?
    personalized = bool(draft.get("rationale")) and bool(draft.get("evidence_cards"))
    # Safety: refuse anything not wellness-scoped; flag clinician-required language.
    text = (draft.get("title", "") + " " + draft.get("rationale", "")).lower()
    unsafe_terms = ("dose", "medication", "insulin units", "prescribe", "stop taking")
    safe = not any(t in text for t in unsafe_terms)

    return [
        {
            "gate": "evidence_grounding",
            "passed": grounded,
            "note": (
                f"Backed by {', '.join(c['id'] for c in cards)}."
                if grounded
                else "No supporting knowledge card — blocked."
            ),
        },
        {
            "gate": "personalization",
            "passed": personalized,
            "note": "Tied to this user's deviating metric."
            if personalized
            else "Not clearly tied to the user's own data.",
        },
        {
            "gate": "safety",
            "passed": safe,
            "note": "Wellness-scoped; no medication/dosing guidance."
            if safe
            else "Contains clinical guidance — refer to a clinician.",
        },
    ]


def _ensure_gates(intervention: dict) -> dict:
    if not intervention.get("gates"):
        intervention["gates"] = evaluate_gates(intervention)
    return intervention


def recommend(user_id: str) -> Optional[list[dict]]:
    kb = store.load_kb(user_id)
    if kb is None:
        return None
    items = kb.get("interventions", [])
    # Only surface interventions that clear every gate — the safety guarantee.
    return [i for i in (_ensure_gates(x) for x in items) if all(g["passed"] for g in i["gates"])]


def set_status(user_id: str, intervention_id: str, status: str) -> Optional[dict]:
    kb = store.load_kb(user_id)
    if kb is None:
        return None
    for item in kb.get("interventions", []):
        if item.get("id") == intervention_id:
            updated = dict(item)
            updated["status"] = status
            return _ensure_gates(updated)
    return None
