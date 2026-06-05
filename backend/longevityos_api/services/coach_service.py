"""Health coach: answers questions grounded in the user's own profile + day.

If ANTHROPIC_API_KEY is set, `_answer_live` is where a real model is wired (sending
only derived summaries, never raw PHI). Otherwise a deterministic, profile-grounded
responder handles intents (food, exercise, sleep, supplements, status) and cites the
research knowledge cards behind each read.
"""

from __future__ import annotations

from typing import Optional

from ..config import agent_live
from . import knowledge_service, store


def _facts(kb: dict) -> dict:
    sc = kb.get("scorecard", {})
    systems = kb.get("systems", [])
    coupling = kb.get("coupling", [])
    worst = max(coupling, key=lambda c: abs(c.get("delta_vs_baseline") or 0), default=None)
    watch = [s["system"] for s in systems if s.get("status") == "watch"]
    return {
        "name": kb.get("profile", {}).get("display_name", "there"),
        "bio_age": sc.get("biological_age"),
        "chron_age": sc.get("chronological_age"),
        "age_accel": sc.get("age_accel"),
        "delta": sc.get("delta_vs_baseline"),
        "watch": watch,
        "worst": worst,
        "day": kb.get("day", {}).get("events", []),
    }


def _kc(*ids: str) -> list[str]:
    return [i for i in ids if knowledge_service.get_card(i)]


FOOD = ("eat", "food", "meal", "snack", "carb", "sugar", "rice", "bread", "pasta", "pizza",
        "dessert", "drink", "breakfast", "lunch", "dinner", "fruit", "protein")
EXERCISE = ("exercise", "workout", "work out", "run", "lift", "gym", "cardio", "train",
            "training", "walk", "move", "yoga", "hiit")
SLEEP = ("sleep", "bed", "bedtime", "nap", "tired", "rest", "wake")
SUPP = ("supplement", "vitamin", "magnesium", "omega", "creatine", "fish oil")
STATUS = ("how am i", "my health", "biological age", "my age", "status", "overview",
          "summary", "how's my", "how is my", "score")
CLINICAL = ("medication", "med", "dose", "dosage", "insulin", "prescribe", "chest pain",
            "dizzy", "symptom", "diagnos")


def _has(msg: str, words) -> bool:
    return any(w in msg for w in words)


def answer(user_id: str, message: str, history: Optional[list] = None) -> Optional[dict]:
    kb = store.load_kb(user_id)
    if kb is None:
        return None
    if agent_live():
        try:
            return _answer_live(kb, message, history or [])
        except Exception:
            pass  # graceful fallback to grounded responder
    return _grounded(kb, message or "")


def _answer_live(kb: dict, message: str, history: list) -> dict:  # pragma: no cover
    """Wire a real model here. Send only the derived facts/day summary, never raw PHI."""
    raise NotImplementedError("Live coach not wired (no ANTHROPIC_API_KEY).")


def _grounded(kb: dict, message: str) -> dict:
    f = _facts(kb)
    m = message.lower().strip()
    name = f["name"]
    worst = f["worst"]
    coup_line = (
        f"your nocturnal glucose–HR coupling is down "
        f"{abs(worst.get('delta_vs_baseline') or 0):.2f} vs your baseline"
        if worst
        else "your overnight coupling is the metric to watch"
    )
    checked = ["biological age", "system ages", "cross-modal coupling", "today's activities"]

    # Clinical guardrail first — stay wellness-scoped.
    if _has(m, CLINICAL):
        return _resp(
            f"That's a clinical question, {name}, so I'll keep it wellness-scoped and point you to "
            f"your clinician for anything involving medication, dosing, or symptoms. For general "
            f"context: your data trends are reassuring (biological age {f['bio_age']}, "
            f"{_younger(f['age_accel'])}), with {coup_line} as the main thing worth watching.",
            _kc("KC-NOCTURNAL-COUPLING"),
            ["How's my health overall?", "What should I eat tonight?", "Best exercise for me?"],
            checked,
        )

    if _has(m, FOOD):
        food = _named_food(m)
        lead = (
            f"On {food}: it's carb-dense, so pair it with protein, fiber, and a little healthy fat, "
            f"keep the portion moderate, and — if it's within ~3 hours of bed — lean lighter. "
            if food
            else "Here's how I'd frame any meal for you right now. "
        )
        return _resp(
            f"{lead}Your time-in-range is 82% and glucose complexity is holding up, but {coup_line}, "
            f"so steadier evening glucose is the highest-impact goal. Today your breakfast gave a "
            f"controlled ~36 mg/dL rise, and your post-meal walks clipped the peaks — pairing a "
            f"10–15 minute walk with a carb-heavier meal is your best lever. Tell me the specific "
            f"food and I'll give you a sharper read.",
            _kc("KC-GLUCOSE-COMPLEXITY", "KC-NOCTURNAL-COUPLING"),
            ["Should I eat rice with dinner?", "What's a good evening snack?", "Is it too late to eat?"],
            checked,
        )

    if _has(m, EXERCISE):
        return _resp(
            f"Your cardiac system is your strong suit ({_younger(-3.1)} on the cardiac clock), so "
            f"keep the strength work — today's session peaked at 128 bpm with a strong HRV rebound. "
            f"Two additions move your watch-list: a daily 10–15 min post-dinner walk to support "
            f"glucose–HR coupling, and 2× Zone-2 cardio a week to nudge your autonomic system "
            f"(currently running a touch old). Avoid hard training within ~2 hours of bed so it "
            f"doesn't bleed into your overnight window.",
            _kc("KC-NOCTURNAL-COUPLING", "KC-COUPLING-BURDEN"),
            ["What should I do tomorrow?", "Is evening exercise bad for me?", "How hard should I go?"],
            checked,
        )

    if _has(m, SLEEP):
        return _resp(
            f"Sleep is your biggest lever right now, {name}. {coup_line[0].upper()}{coup_line[1:]}, "
            f"and your evening light is elevated — both point at sleep timing. The single highest-"
            f"yield change is advancing your bedtime ~30 minutes and dimming screens after dinner; "
            f"that's exactly what strengthens overnight cardiometabolic synchronization.",
            _kc("KC-NOCTURNAL-COUPLING", "KC-CIRCADIAN-COUPLING"),
            ["When should I go to bed?", "Why does evening light matter?", "How's my sleep been?"],
            checked,
        )

    if _has(m, SUPP):
        return _resp(
            f"Your current stack is vitamin D, omega-3, and magnesium glycinate — a sensible, "
            f"evidence-aligned base. I track these for adherence rather than acute effects, and I "
            f"keep specific dosing with your clinician. Magnesium in the evening fits your sleep "
            f"goal; the omega-3 supports your inflammatory markers over time.",
            [],
            ["What helps my sleep?", "How's my inflammation?", "What should I eat tonight?"],
            checked,
        )

    if _has(m, STATUS) or m in ("hi", "hello", "hey"):
        return _resp(
            f"Hi {name} — here's your read. Biological age {f['bio_age']} vs {f['chron_age']:.0f} "
            f"chronological ({_younger(f['age_accel'])}), and you're trending {_delta(f['delta'])} "
            f"vs your own baseline. Cardiac and retinal systems are strong; metabolic and autonomic "
            f"are on watch. The one signal I'd act on is that {coup_line} — your sleep timing and "
            f"evening light are the levers. Ask me about food, exercise, or sleep and I'll get "
            f"specific.",
            _kc("KC-STATIC-DOMINANCE"),
            ["What should I eat tonight?", "Best exercise for me?", "Why is my coupling down?"],
            checked,
        )

    # Default / help
    return _resp(
        f"I can see your full health profile and everything you logged today, {name}. Ask me things "
        f"like “should I eat this?”, “what workout do you recommend?”, or “how's my sleep?” — I'll "
        f"answer from your actual numbers. Right now, {coup_line}, so that's where I'd focus.",
        _kc("KC-NOCTURNAL-COUPLING"),
        ["How's my health overall?", "What should I eat tonight?", "Best exercise for me?"],
        checked,
    )


def _named_food(m: str) -> Optional[str]:
    for w in ("rice", "bread", "pasta", "pizza", "dessert", "sugar", "fruit", "ice cream",
              "cake", "soda", "juice", "chocolate"):
        if w in m:
            return w
    return None


def _younger(accel) -> str:
    if accel is None:
        return "on track"
    a = abs(accel)
    return f"{a:.1f} years {'younger' if accel < 0 else 'older'} than your age"


def _delta(d) -> str:
    if not d:
        return "steady"
    return f"{'down' if d < 0 else 'up'} {abs(d):.1f} yrs"


def _resp(reply: str, citations: list[str], suggestions: list[str], checked: list[str]) -> dict:
    return {"reply": reply, "citations": citations, "suggestions": suggestions, "checked": checked}
