# Build Guide — from vertical slice to product

A phased plan to build LongevityOS locally. Each phase is independently demoable. Order is chosen
so the **science shows up early** and the frontend can progress in parallel.

Prereqs: Python 3.11, Node 20+. Optional: `ANTHROPIC_API_KEY` (agent-live), foundation-model
weights in `model_artifacts/weights/` (scoring-live).

---

## Phase 0 — Run the representative slice (½ day)

Goal: the whole app runs on the synthetic demo user, nothing private, no cluster.

```bash
cd backend && pip install -r requirements.txt
uvicorn longevityos_api.main:app --reload --port 8000   # http://localhost:8000/docs
cd ../frontend && npm install && npm run dev            # http://localhost:3000
```

Done when: dashboard renders the demo user's scorecard, knowledge base, and one intervention.

## Phase 1 — Export bridge artifacts from AI-READI (½ day, on the cluster)

Goal: real scoring numbers. In the AI-READI repo, export the *frozen* clock for individual use.

- Save the fitted aging-clock model(s) + the train-set imputer/scaler with `joblib`.
- Save train-set feature means/stds and **reference percentile tables** for AgeAccel/subtypes.
- Drop them into `LongevityOS/model_artifacts/` (weights subdir is gitignored — keep it local).

Done when: `scoring_service` loads artifacts and returns real biological-age + percentile for the
demo user. (See `model_artifacts/README.md` for the exact export checklist.)

## Phase 2 — Knowledge base + trajectories (1–2 days)

Goal: the per-user record grows and shows N-of-1 change.

- Implement the `data/users/<id>/` read/write in `knowledge_service`.
- Add a second timepoint to the demo user; compute Δ-vs-baseline in `scoring_service`.
- Frontend: trajectory charts (sparklines + a "vs your baseline" delta).

Done when: ingesting a second snapshot updates the dashboard trajectory.

## Phase 3 — Agentic reasoning + intervention gates (2–3 days)

Goal: the agent reasons over the user and proposes gated, evidence-linked interventions.

- Wire `agent_service` to `engine/agentic/agentic_discovery` (live with `ANTHROPIC_API_KEY`).
- Repoint the candidate from "population hypothesis" to "intervention for this user"; evidence
  base = `engine/knowledge_cards/` + the user's `kb.json`.
- Implement the three gates (evidence-grounding · personalization · safety) in
  `intervention_service`, reusing the `engine/agentic` reviewer pattern.
- **Send only derived features/summaries to the LLM, never raw PHI.**

Done when: a recommendation appears with gate verdicts + a cited knowledge card.

## Phase 4 — Real ingestion (2–4 days, optional for demo)

Goal: a user uploads their *own* exports.

- Build `ingestion/` parsers → the internal normalized schema:
  `apple_health/` (export.xml), `garmin/` (Connect export), `fitbit/`, `labs/` (CSV/PDF),
  `fhir/` (Bundle JSON), `omics/` (VCF/CSV).
- Start with the one export *you* can produce for the live demo (e.g., Apple Health).

Done when: your own export flows upload → normalized → scored.

## Phase 5 — Polish the UI (ongoing)

Goal: "very polished and beautiful."

- Build out screens from [`FRONTEND_SPEC.md`](FRONTEND_SPEC.md) using v0/Cursor/Claude Code.
- Match the showcase site's brand (palette, type, motion). Add empty/loading/error states,
  micro-interactions, and a confident landing page.

Done when: it looks like a product, not a class project.

---

## Suggested demo cut

If time is short, ship **Phase 0 + 1 + 3** and *describe* 2/4/5. That gives you: real scoring,
real agentic reasoning with gates and citations, on a synthetic person — the most impressive
slice for the least risk.

## Parallelization

- **You + AI frontend tool** on `frontend/` (Phase 5) — runs in parallel with everything.
- **Backend/engine wiring** (Phases 1–3) is the critical path for "real" output.
- Phase 4 is the only one that needs your personal data; do it last unless the demo hinges on it.
