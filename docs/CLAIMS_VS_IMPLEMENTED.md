# Claims vs. Implemented — the honest map

This is the integrity ledger for LongevityOS. Use it to demo confidently without overclaiming.
Four states:

- 🟢 **Real** — implemented and runs locally now.
- 🟡 **Wrapped** — the underlying research code is present in `engine/`; the app calls it thinly
  or behind a flag. Real substance, light integration.
- 🟠 **Representative** — shown with realistic canned/synthetic outputs in the demo; the logic
  exists but isn't fully wired end-to-end.
- 🔵 **Aspirational** — described and designed, not yet built. Fair to *describe* as roadmap; do
  not imply it runs.

> Rule of thumb for the class demo: **say the vision, show the slice, label the rest.** When in
> doubt, point at `engine/` — the foundation model, agentic gates, and 27 hypotheses are real code.

## Ledger

| Capability | State | Where | Honest phrasing for the demo |
| --- | --- | --- | --- |
| Multimodal foundation model (JEPA) exists & was validated | 🟢 Real (as research) | `engine/foundation_model/` + `docs/research_engine/reports/JEPA_SYSTEMATIC_SUMMARY_20260428.md` | "Trained and validated on AI-READI: aligned windows beat wrong-day/shuffle controls across 36 runs." |
| Agentic discovery framework w/ reviewer gates | 🟢 Real (as research) | `engine/agentic/agentic_discovery/` | "A guarded multi-agent system with scientific/feasibility/mechanical gates; one live run completed." |
| Hypothesis-driven backbone (27 hypotheses) | 🟢 Real (as research) | `engine/hypothesis/hypotheses/*.json` | "27 hypotheses, propose→critique→execute→verify; 5 supported, 1 refuted." |
| Aging-clock scoring on an individual | 🟡 Wrapped | `engine/science/aging_*.py` + `model_artifacts/` | "We apply the frozen cohort clocks to your data." (Needs exported artifacts for live numbers.) |
| Per-user knowledge base (growing, versioned) | 🟡 Wrapped | `data/users/<id>/` schema + backend `knowledge_service` | "Your record grows by ingest date; we track your own baseline." |
| Backend API (users, ingest, scoring, agent, interventions) | 🟢 Real | `backend/longevityos_api/` | "FastAPI backend, live at /docs." |
| Synthetic demo user end-to-end | 🟢 Real | `data/demo_users/` + backend | "Everything you see runs on a synthetic person so nothing private is exposed." |
| FM embeddings on uploaded image/ECG | 🟠 Representative | inference path designed; weights gitignored | "With the foundation-model weights loaded locally, this OCT becomes a 1024-d embedding." |
| Live agent reasoning + intervention generation | 🟠 Representative → 🟡 with key | `agent_service` (representative mode default; live with `ANTHROPIC_API_KEY`) | "In live mode the agent reasons over your data and cites evidence cards." |
| Intervention safety/evidence/personalization gates | 🟡 Wrapped | `intervention_service` reuses `engine/agentic` gate pattern | "Every suggestion passes three gates before you see it." |
| Real upload parsers (Apple Health, Garmin, lab PDF, FHIR, omics) | 🔵 Aspirational | `ingestion/` (to build) | "Roadmap: connect your own exports. Today we ingest the normalized schema." |
| Polished interactive UI | 🟡 Wrapped | `frontend/` scaffold + `FRONTEND_SPEC.md` | "The product UI — built from this spec." (Finish locally.) |
| Multi-user auth / accounts | 🔵 Aspirational | — | "Single-user/local for the prototype; accounts are roadmap." |
| Outcome tracking (did the intervention work?) | 🔵 Aspirational | schema has `interventions/*.outcomes` | "Roadmap: log adherence and re-measure." |

## Guardrails when presenting

1. Never imply clinical validity for an individual. Frame as **wellness/informational**, lead
   with **within-person change**, show uncertainty.
2. Don't claim live FM/agent output if running in representative mode — say "representative" or
   load the key/weights first.
3. Keep this file updated as states flip 🔵→🟠→🟡→🟢. It is your defense against accidental
   overclaiming and a genuinely good artifact to show ("here's exactly what's real").
