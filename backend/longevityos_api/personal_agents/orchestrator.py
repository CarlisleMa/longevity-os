"""Care Coordinator: routes a question to the right specialists, runs the safety
gate, and has Synthesis compose the final answer."""

from __future__ import annotations

from dataclasses import asdict

from .agents import (
    Biomarkers,
    Biosignals,
    CareCoordinator,
    Experiments,
    Movement,
    Nutrition,
    SafetyReviewer,
    Sleep,
    Supplements,
    Synthesis,
)

COORD = CareCoordinator()
SAFETY = SafetyReviewer()
SYNTH = Synthesis()
SPECIALISTS = [Nutrition(), Movement(), Sleep(), Biosignals(), Biomarkers(), Supplements(), Experiments()]
BY_KEY = {s.key: s for s in SPECIALISTS}

# The full team, in display order — for a "meet your care team" view.
ROSTER = [COORD, *SPECIALISTS, SAFETY, SYNTH]

STATUS = ("how am i", "overall", "summary", "status", "how is my", "how's my", "doing",
          "biological age", "my age", "score", "report", "what's wrong", "whats wrong")
GREET = ("hi", "hello", "hey", "yo", "help")
DEFAULT_SUGGESTIONS = ["What should I eat tonight?", "Best exercise for me?", "How's my sleep?", "How am I doing overall?"]


def _overview(ctx: dict) -> str:
    accel = ctx.get("age_accel") or 0
    younger = f"{abs(accel):.1f} yrs {'younger' if accel < 0 else 'older'} than your age"
    d = ctx.get("delta")
    trend = "holding steady" if not d else f"trending {'down' if d < 0 else 'up'} {abs(d):.1f} yrs"
    return (
        f"Biological age {ctx.get('bio_age')} vs {ctx.get('chron_age', 0):.0f} chronological ({younger}), "
        f"{trend} vs your own baseline. Cardiac and retinal read younger; metabolic and autonomic are on watch."
    )


def consult(ctx: dict, query: str) -> dict:
    q = (query or "").lower().strip()

    scored = sorted(((s, s.relevance(q, ctx)) for s in SPECIALISTS), key=lambda x: -x[1])
    lead = ""

    if not q or q in GREET:
        lead = _overview(ctx)
        engaged = [BY_KEY["signals"]]
    elif any(k in q for k in STATUS):
        lead = _overview(ctx)
        engaged = [BY_KEY["signals"], BY_KEY["sleep"]]
    else:
        engaged = [s for s, r in scored if r >= 0.5][:2]
        if not engaged:
            engaged = [scored[0][0]]  # best-effort single specialist

    notes = [n for s in engaged if (n := s.contribute(q, ctx))]
    safety = SAFETY.review(q, notes, ctx)
    reply = SYNTH.synthesize(q, ctx, notes, safety, lead)

    citations: list[str] = []
    for n in notes:
        for c in n.citations:
            if c not in citations:
                citations.append(c)

    # The team that participated: coordinator + engaged specialists + safety + synthesis.
    team = [COORD, *engaged, SAFETY, SYNTH]
    suggestions = notes[0].suggestions if notes else DEFAULT_SUGGESTIONS

    return {
        "reply": reply,
        "agents": [a.card() for a in team],
        "notes": [asdict(n) for n in notes],
        "citations": citations,
        "safety": safety,
        "suggestions": suggestions,
        "checked": ["biological age", "system clocks", "cross-modal coupling", "today's activities"],
    }


def roster_cards() -> list[dict]:
    return [a.card() for a in ROSTER]
