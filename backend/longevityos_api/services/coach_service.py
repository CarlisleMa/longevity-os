"""Health coach — a personalized multi-agent consult, grounded in the user's data.

A Care Coordinator routes the question to the relevant specialists (Nutrition,
Movement, Sleep & Circadian, Biosignals, Biomarkers, Supplements, Experiments), a
Safety Reviewer gates it, and Synthesis composes the answer. These are personal
agents, distinct from the cohort discovery agents in engine/agentic.

Modes:
- grounded (default, offline): agents fill grounded, cited contributions.
- live (ANTHROPIC_API_KEY set): each agent is backed by a real model. The streaming
  debate (`debate`) generates each turn live; `_answer_live` LLM-synthesizes the
  single-shot answer. Only derived summaries are sent to the model — never raw PHI.
"""

from __future__ import annotations

from typing import Optional

from ..config import agent_live
from ..personal_agents import build_context, consult
from ..personal_agents.debate import MODEL, _facts_blurb, stream_debate
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


def debate(user_id: str, message: str):
    """Return an async generator of debate events, or None for an unknown user."""
    kb = store.load_kb(user_id)
    if kb is None:
        return None
    return stream_debate(build_context(kb), message or "")


def roster() -> list[dict]:
    return roster_cards()


def _answer_live(kb: dict, message: str, history: list) -> dict:
    """Live single-shot answer: deterministic routing + notes, LLM-composed reply."""
    import anthropic

    ctx = build_context(kb)
    base = consult(ctx, message or "")  # routing, per-agent notes, safety, citations
    notes_txt = "\n".join(f"- {n['name']} ({n['title']}): {n['text']}" for n in base["notes"]) or "(none)"
    client = anthropic.Anthropic()
    system = (
        "You are the Synthesis agent for a personalized longevity coaching team. Compose a single "
        "cohesive, warm, specific answer to the user from the specialists' notes below. Keep it "
        "wellness-scoped and defer medication/dosing/diagnosis to a clinician. 2–4 sentences.\n\n"
        f"User's derived data: {_facts_blurb(ctx)}"
    )
    msg = client.messages.create(
        model=MODEL,
        max_tokens=400,
        system=system,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Question: {message}\n\nSpecialist notes:\n{notes_txt}\n\n"
                    f"Safety: {base['safety']['note']}\n\nWrite the final answer."
                ),
            }
        ],
    )
    text = next((b.text for b in msg.content if b.type == "text"), None)
    if text:
        base["reply"] = text.strip()
    return base
