# Demo Script — presenting LongevityOS to the class

A tested narrative + talking points so you can confidently speak to the **foundation model**,
**agentic framework**, and **hypothesis-driven backbone** even where the app wraps them. Target:
**6–8 minutes** demo + Q&A.

---

## Pre-flight (do before you present)

- [ ] `uvicorn longevityos_api.main:app --port 8000` running; open `/docs` in a spare tab.
- [ ] `npm run dev` running; `/dashboard` pre-loaded on the demo user.
- [ ] Know your mode: representative (safe, no key) vs agent-live (`ANTHROPIC_API_KEY` set). Say
      which you're in if asked. Don't claim live output in representative mode.
- [ ] Have `engine/` open in an editor to show real substance on demand.
- [ ] Fallback: a screen recording of the happy path in case of live failure.

## The arc (what story you're telling)

> Population research produces aging clocks and coupling findings, but a *person* can't use a
> paper. LongevityOS turns that validated knowledge into a private, growing model of **you**, and
> into **gated, evidence-linked** actions. It's the application layer on top of a real research
> engine.

## Minute-by-minute

**0:00 — Hook (30s).** "Longevity research lives in cohorts and papers. I built the layer that
brings it to an individual." One sentence on the two pieces: a multimodal foundation model +
an agentic engine, both validated on AI-READI (2,280 people).

**0:30 — Onboarding (1 min).** On `/onboarding`, drag in the demo profile (or your own Apple
Health export if you built Phase 4). Narrate the processing: "parsing streams → computing
features → scoring biological age." Land on `/dashboard`.

**1:30 — Dashboard (2 min).** Walk the **Biological Age Scorecard**: biological vs chronological
age, the AgeAccel chip, and — emphasize this — **the N-of-1 delta vs their own baseline**.
"Cohort percentile orients you; your *own trajectory* is the honest signal." Show the **system
radar** and the **coupling card** ("glucose–heart-rate coupling, blunted post-meal").

**3:30 — Knowledge base + evidence (1.5 min).** Open a knowledge card and click its **evidence
chip**. "Every interpretation is grounded — this one traces to hypothesis H-NEW13 from the
research engine." This is the trust story.

**5:00 — Intervention + gates (1.5 min).** On `/interventions`, open a recommendation. Point at
the **three gate badges** (evidence-grounded · personalized · safety). Hit **"Why this?"** to show
the agent's reasoning trace and citation. "Nothing reaches the user without passing these gates —
the same reviewer pattern the research engine uses to vet hypotheses."

**6:30 — The substance (1 min).** Switch to the editor. Show: `engine/foundation_model/` (the
JEPA), `engine/agentic/agentic_discovery/` (the gates), `engine/hypothesis/hypotheses/` (27 real
hypotheses). "This isn't a mockup over nothing — here's the validated engine underneath."

**7:30 — Close (30s).** The vision: the longer you use it, the better it models you; interventions
become a personal, evidence-grounded feedback loop. Name what's roadmap (honest), thank them.

## Talking points (have these ready)

**Foundation model (JEPA).** "A joint-embedding predictive model over synchronized multimodal
streams — glucose, heart rate, activity, environment, plus frozen retinal (RETFound) and cardiac
(ECGFounder) embeddings. Validated finding: aligned time windows are far more predictable than
wrong-day or shuffled-participant controls across 36 runs and four horizons — physiological
coupling is real and decays with time. For an individual, the same encoder turns *their* streams
into a personal embedding and flags coupling that's degraded versus their baseline." (Source:
`docs/research_engine/reports/JEPA_SYSTEMATIC_SUMMARY_20260428.md`.)

**Agentic framework.** "A guarded multi-agent system: agents never get raw shell access, only
vetted tools, and every proposal passes scientific, feasibility, and mechanical reviewer gates
before promotion. In LongevityOS I repoint that from 'vet a population hypothesis' to 'vet an
intervention for this person' — the gates become evidence-grounding, personalization, and safety."
(Source: `engine/agentic/agentic_discovery/`.)

**Hypothesis-driven backbone.** "27 hypotheses run through propose → critique → execute → verify;
5 supported, 1 refuted, the rest critiqued or in progress. Those become the *evidence cards* the
personal agent cites — so a recommendation is never a vibe, it's tied to a tested claim."
(Source: `engine/hypothesis/hypotheses/*.json`.)

**Privacy.** "Local-first. Raw data stays in the user's record; only derived features and
summaries go to the model — never raw PHI. And it's wellness-scoped, not medical advice."

**N-of-1 honesty.** "A cohort clock on one person has wide error bars — so I lead with
within-person change, which is a cleaner control. That's the scientifically honest move."

## Likely questions (and answers)

- *"Is this medical advice?"* No — wellness/informational, with a safety gate that flags anything
  needing a clinician. Framed and enforced, not just a disclaimer.
- *"How much is real vs. mocked?"* The engine, gates, and hypotheses are real research; the app
  applies their frozen outputs.
- *"Where's the data from?"* Models/findings validated on AI-READI (2,280 participants). The demo
  user is **synthetic** — no real participant data is in the app (data use agreement).
- *"Does the foundation model run live in the app?"* The encoders are inference-only here; with
  the weights loaded locally it embeds uploaded streams. In the demo I'm showing
  [representative / live — say which].
- *"What's the moat?"* The growing per-person knowledge base — it compounds.

## If something breaks

Fall back to the screen recording, then pivot to the editor and walk the real `engine/` code +
this doc set. The substance stands on its own even if the live UI hiccups.
