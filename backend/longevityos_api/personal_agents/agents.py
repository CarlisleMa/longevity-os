"""The personalized coach agent roster.

A reasonable team for a longevity product (not the cohort research agents):
- Care Coordinator  — orchestrator that routes + coordinates
- Nutrition         — diet & glucose response
- Movement          — exercise & recovery
- Sleep & Circadian — sleep timing & rhythm (the highest-leverage domain for this user)
- Biosignals        — wearables & CGM readout
- Biomarkers        — labs & aging clocks
- Supplements       — stack & timing
- Experiments       — N-of-1 design & tracking
- Safety Reviewer   — wellness guardrail
- Synthesis         — composes the final answer
"""

from __future__ import annotations

from typing import Optional

from .base import AgentNote, PersonalAgent
from .context import coupling_line, metric_value, named_food


def _accel(ctx: dict, system: str, default: float) -> str:
    v = ctx.get("systems", {}).get(system, {}).get("age_accel", default)
    return f"{abs(v):.1f} yrs {'younger' if v < 0 else 'older'}"


# ── Specialists ──────────────────────────────────────────────────────


class Nutrition(PersonalAgent):
    key, name, title, glyph = "nutrition", "Nutrition", "Diet & glucose response", "utensils"
    keywords = ("eat", "food", "meal", "snack", "carb", "sugar", "diet", "drink",
                "breakfast", "lunch", "dinner", "protein", "calorie", "fasting")

    def contribute(self, q, ctx) -> Optional[AgentNote]:
        food = named_food(q)
        lead = (
            f"On {food}: it's carb-dense — pair it with protein, fibre and a little healthy fat, keep "
            f"the portion moderate, and lean lighter if it's within ~3 hours of bed. "
            if food
            else ""
        )
        return AgentNote(
            self.key, self.name, self.title, self.glyph,
            text=(
                f"{lead}Your time-in-range is {metric_value(ctx, 'Time in range (70–180)', '82%')} and "
                f"glucose complexity is holding up, but {coupling_line(ctx)} — so steadier evening glucose "
                f"is the goal. A 10–15 minute walk after a carb-heavier meal is your best lever."
            ),
            brief="anchor meals on protein + fibre and walk after carbs",
            citations=["KC-GLUCOSE-COMPLEXITY", "KC-NOCTURNAL-COUPLING"],
            suggestions=["Should I eat rice with dinner?", "What's a good evening snack?", "Is it too late to eat?"],
        )


class Movement(PersonalAgent):
    key, name, title, glyph = "movement", "Movement", "Exercise & recovery", "dumbbell"
    keywords = ("exercise", "workout", "work out", "run", "lift", "gym", "cardio",
                "train", "walk", "move", "yoga", "hiit", "strength", "steps")

    def contribute(self, q, ctx) -> Optional[AgentNote]:
        return AgentNote(
            self.key, self.name, self.title, self.glyph,
            text=(
                f"Your cardiac system is your strongest ({_accel(ctx, 'cardiac', -3.1)}), so keep the "
                f"strength work. To move your watch-list, add a daily 10–15 min post-dinner walk and 2× "
                f"Zone-2 cardio a week for your autonomic system — and avoid hard sessions within ~2 hours "
                f"of bed so they don't bleed into your overnight window."
            ),
            brief="keep strength; add post-dinner walks + 2× Zone-2",
            citations=["KC-NOCTURNAL-COUPLING", "KC-COUPLING-BURDEN"],
            suggestions=["What should I do tomorrow?", "Is evening exercise bad for me?", "How hard should I go?"],
        )


class Sleep(PersonalAgent):
    key, name, title, glyph = "sleep", "Sleep & Circadian", "Sleep timing & rhythm", "moon"
    keywords = ("sleep", "bed", "bedtime", "nap", "tired", "rest", "wake", "circadian",
                "evening", "light", "screen", "wind down", "melatonin", "night")

    def contribute(self, q, ctx) -> Optional[AgentNote]:
        return AgentNote(
            self.key, self.name, self.title, self.glyph,
            text=(
                f"Sleep is your highest-leverage domain right now. {coupling_line(ctx).capitalize()}, and "
                f"your evening light is elevated — both point at sleep timing. Advancing your bedtime ~30 "
                f"minutes and dimming screens after dinner is what strengthens overnight cardiometabolic "
                f"synchronization; keep your morning-light habit to protect the day–night rhythm."
            ),
            brief="advance bedtime ~30 min, dim evening screens, keep morning light",
            citations=["KC-NOCTURNAL-COUPLING", "KC-CIRCADIAN-COUPLING"],
            suggestions=["When should I go to bed?", "Why does evening light matter?", "How's my sleep been?"],
        )


class Biosignals(PersonalAgent):
    key, name, title, glyph = "signals", "Biosignals", "Wearables & CGM", "pulse"
    keywords = ("heart", "hr", "hrv", "resting", "wearable", "recovery", "metric",
                "coupling", "glucose", "cgm", "readiness", "garmin", "signal")

    def contribute(self, q, ctx) -> Optional[AgentNote]:
        return AgentNote(
            self.key, self.name, self.title, self.glyph,
            text=(
                f"Reading your wearables: resting HR {metric_value(ctx, 'Resting heart rate', '58 bpm')}, "
                f"sleep efficiency {metric_value(ctx, 'Sleep efficiency', '88%')}. The signal that stands "
                f"out is that {coupling_line(ctx)} — overnight is where your physiology is drifting, even "
                f"though daytime coupling looks stable."
            ),
            brief="RHR & sleep solid; overnight coupling is drifting",
            citations=["KC-NOCTURNAL-COUPLING", "KC-SLEEPWAKE-REORG"],
            suggestions=["Why is my coupling down?", "How's my recovery?", "How am I doing overall?"],
        )


class Biomarkers(PersonalAgent):
    key, name, title, glyph = "labs", "Biomarkers", "Labs & aging clocks", "flask"
    keywords = ("lab", "biomarker", "hba1c", "a1c", "blood", "cholesterol", "kidney",
                "liver", "inflammation", "clock", "biological age", "renal", "metabolic")

    def contribute(self, q, ctx) -> Optional[AgentNote]:
        return AgentNote(
            self.key, self.name, self.title, self.glyph,
            text=(
                f"From your labs and aging clocks: HbA1c {metric_value(ctx, 'HbA1c', '5.6%')} (creeping up), "
                f"your metabolic clock runs ~+1.8 yrs and autonomic ~+2.4 (both on watch), while cardiac and "
                f"renal read younger. Dynamic coupling and glucose complexity add information your single lab "
                f"values miss."
            ),
            brief="HbA1c creeping; metabolic & autonomic clocks on watch",
            citations=["KC-STATIC-DOMINANCE", "KC-GLUCOSE-COMPLEXITY"],
            suggestions=["What does my HbA1c mean?", "How's my metabolic age?", "Why watch my autonomic system?"],
        )


class Supplements(PersonalAgent):
    key, name, title, glyph = "supplements", "Supplements", "Stack & timing", "leaf"
    keywords = ("supplement", "vitamin", "magnesium", "omega", "creatine", "fish oil",
                "probiotic", "stack")

    def contribute(self, q, ctx) -> Optional[AgentNote]:
        return AgentNote(
            self.key, self.name, self.title, self.glyph,
            text=(
                "Your current stack — vitamin D, omega-3, and magnesium glycinate — is a sensible base. "
                "Magnesium in the evening fits your sleep goal, and omega-3 supports your inflammatory markers "
                "over time. I track these for adherence and keep specific dosing with your clinician."
            ),
            brief="D + omega-3 + evening magnesium — a sensible base",
            citations=[],
            suggestions=["What helps my sleep?", "Should I add anything?", "How's my inflammation?"],
        )


class Experiments(PersonalAgent):
    key, name, title, glyph = "experiments", "Experiments", "N-of-1 design & tracking", "clipboard"
    keywords = ("experiment", "trial", "track", "progress", "working", "adherence",
                "intervention", "design", "n-of-1", "prove", "study", "test whether",
                "evidence", "results", "how do i know")

    def contribute(self, q, ctx) -> Optional[AgentNote]:
        ivs = ctx.get("interventions", [])
        titles = "; ".join(i["title"] for i in ivs[:3]) or "none yet"
        return AgentNote(
            self.key, self.name, self.title, self.glyph,
            text=(
                f"You have {len(ivs)} active experiments: {titles}. They all move the same metric — your "
                f"overnight glucose–HR coupling — so that's what I track. To prove it cleanly I'd run a 2-"
                f"weeks-on / 2-weeks-off bedtime crossover holding diet and training steady, then compare "
                f"nocturnal coupling between blocks. In AI-READI, overnight coupling predicted next-day "
                f"glycemic control, so it's a measurable, well-powered target for one person."
            ),
            brief="2×2-week bedtime crossover; measure overnight coupling",
            citations=["KC-NOCTURNAL-COUPLING", "KC-CIRCADIAN-COUPLING"],
            suggestions=["Is my bedtime change working?", "Design an experiment for sleep", "How long until results?"],
        )


# ── Governance agents ────────────────────────────────────────────────

CLINICAL = ("medication", "dose", "dosage", "insulin", "prescribe", "chest pain",
            "dizzy", "symptom", "diagnos", "disease", "treat ")


class SafetyReviewer(PersonalAgent):
    key, name, title, glyph, role = "safety", "Safety Reviewer", "Wellness guardrail", "shield", "safety"

    def review(self, q: str, notes: list[AgentNote], ctx: dict) -> dict:
        if any(w in q for w in CLINICAL):
            return {
                "passed": False,
                "note": (
                    "This touches clinical territory (medication, dosing, or symptoms) — I keep guidance "
                    "wellness-scoped and defer those to your clinician."
                ),
            }
        return {"passed": True, "note": "Wellness-scoped; no medication or dosing guidance."}


class Synthesis(PersonalAgent):
    key, name, title, glyph, role = "synthesis", "Synthesis", "Final answer", "scroll", "synthesis"

    def synthesize(self, q, ctx, notes: list[AgentNote], safety: dict, lead: str = "") -> str:
        parts: list[str] = []
        if not safety.get("passed", True):
            parts.append(safety["note"])
        if lead:
            parts.append(lead)
        if notes:
            parts.append(notes[0].text)
            for n in notes[1:]:
                if n.brief:
                    parts.append(f"{n.name} adds: {n.brief}.")
        reply = " ".join(p.strip() for p in parts if p).strip()
        if not reply:
            reply = (
                f"Hi {ctx['name']} — ask me about food, exercise, sleep, supplements, or your numbers and "
                f"the right specialist will weigh in."
            )
        return reply


class CareCoordinator(PersonalAgent):
    key, name, title, glyph, role = "coordinator", "Care Coordinator", "Orchestrator", "compass", "orchestrator"
