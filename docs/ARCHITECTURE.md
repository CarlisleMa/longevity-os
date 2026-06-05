# LongevityOS — Architecture

How the pieces fit, the per-user data model, and how `engine/` maps to the running app.

---

## System diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│  frontend/  (Next.js + Tailwind + shadcn/ui)                              │
│  Landing · Onboarding/Upload · Dashboard · Knowledge Base · Interventions │
└───────────────────────────────┬─────────────────────────────────────────┘
                                 │ REST / SSE (JSON)
┌───────────────────────────────▼─────────────────────────────────────────┐
│  backend/  (FastAPI)                                                      │
│  routers:  users · ingest · knowledge_base · scoring · agent · interventions
│  services: scoring_service · knowledge_service · agent_service · intervention_service
└───────────────────────────────┬─────────────────────────────────────────┘
                                 │ in-process Python calls
┌───────────────────────────────▼─────────────────────────────────────────┐
│  engine/  (research substance, copied from AI-READI)                     │
│  science/         loaders, feature formulas, coupling, aging-clock scoring│
│  foundation_model/ JEPA encoders (inference-only)                         │
│  agentic/         discovery framework + reviewer gates                    │
│  hypothesis/      27 stored hypotheses (evidence)                         │
│  knowledge_cards/ distilled findings the agent cites                      │
└───────────────────────────────┬─────────────────────────────────────────┘
                                 │ reads/writes
┌───────────────────────────────▼─────────────────────────────────────────┐
│  data/users/<user_id>/   (gitignored; per-user growing knowledge base)   │
│  model_artifacts/        (frozen models + reference distributions)        │
└───────────────────────────────────────────────────────────────────────────┘
```

## Per-user knowledge base (the core data model)

Each user is a directory; the knowledge base grows append-only by ingest date.

```text
data/users/<user_id>/
  profile.json                 # id, created_at, demographics the user volunteered, units
  uploads/                     # raw files as uploaded (gitignored)
    2026-06-04_garmin.zip
    2026-06-04_labs.pdf
    2026-06-04_oct.dcm
  normalized/                  # uploads parsed into the internal schema
    cgm.parquet                # timestamp, glucose_mg_dl
    wearable.parquet           # timestamp, hr, steps, asleep, active_calories
    environment.parquet        # timestamp, pm25, temp, humidity, light_*
    clinical.parquet           # labs/vitals (long: concept, value, unit, date)
    retinal/  cardiac/         # image/waveform pointers + extracted embeddings
  timeline/                    # one snapshot per ingest event — enables N-of-1 trajectories
    2026-06-04T1200/
      features.json            # derived feature vector at this timepoint
      scores.json              # biological age, AgeAccel, coupling metrics (+ percentile + Δ vs baseline)
      embeddings.parquet       # frozen FM embeddings
      observations.json        # agent-written notes citing knowledge cards
  interventions/
    INT-0001.json              # proposal, evidence card refs, gate verdicts, status, outcomes
  kb.json                      # index/manifest over the above (fast retrieval)
```

**Why this shape:** trajectories fall out naturally (diff `timeline/*/scores.json`); the agent
retrieves over `kb.json` + `engine/knowledge_cards/`; raw PHI stays in `uploads/` and never goes
to the LLM (only `features.json`/`scores.json` summaries do).

## Data flow: one ingest event

```
upload ─▶ ingestion parser ─▶ normalized/*.parquet
       ─▶ engine/science feature formulas ─▶ features.json
       ─▶ engine/science frozen clocks (model_artifacts) ─▶ scores.json (+ percentile + Δ baseline)
       ─▶ engine/foundation_model encoders ─▶ embeddings.parquet
       ─▶ engine/agentic agent reads features+scores+knowledge_cards ─▶ observations.json
       ─▶ intervention_service proposes → 3 gates → interventions/INT-*.json
       ─▶ kb.json updated; frontend re-renders dashboard + trajectory
```

## Backend ↔ engine mapping

| Backend service | Calls into `engine/` | Notes |
| --- | --- | --- |
| `scoring_service` | `science/aging_scores.py`, `science/features*.py`, frozen clocks | Apply, never train. Loads `model_artifacts/`. |
| `knowledge_service` | `knowledge_cards/`, `hypothesis/hypotheses/` | Retrieval over evidence priors. |
| `agent_service` | `agentic/agentic_discovery` runtime | Live mode needs `ANTHROPIC_API_KEY`; otherwise representative mode. |
| `intervention_service` | `agentic/` reviewer-gate pattern | evidence-grounding · personalization · safety gates. |
| `ingest` router | `ingestion/` parsers (to build) + `science/loaders` | Apple Health/Garmin/labs → internal schema. |

## Foundation-model inference path

The JEPA encoders in `engine/foundation_model/` were *trained* on the cluster. Here they run
**inference-only**: load frozen weights from `model_artifacts/weights/` (gitignored), encode a
single user's aligned streams into a personal embedding, and (optionally) compute personal
coupling-degradation signals. If weights are absent, `scoring_service` returns clock-based scores
only and flags FM embeddings as unavailable — the app still works.

## Agentic layer: cohort discovery → personal reasoning

`engine/agentic` shipped as a *cohort* discovery system (propose hypotheses across 2,280 people).
For LongevityOS it is repointed to a *single person*: the same guarded-tool + reviewer-gate
runtime, but the "candidate" is an **intervention for this user** rather than a population
hypothesis, and the evidence base is `knowledge_cards/` + the user's own `kb.json`. The reviewer
gates become evidence/personalization/safety checks (see [BRAINSTORM.md](BRAINSTORM.md) §5).

## Run modes

| Mode | Requires | Behavior |
| --- | --- | --- |
| **Representative** (default) | nothing | Backend serves the synthetic demo user; agent/interventions use canned-but-realistic outputs. Frontend fully functional. |
| **Scoring-live** | `model_artifacts/` + Python deps | Real clock scoring + FM embeddings on uploaded data. |
| **Agent-live** | `ANTHROPIC_API_KEY` | Real agent reasoning + intervention generation through the gates. |

This staging lets the demo run anywhere, then light up real capability as you wire each piece.
