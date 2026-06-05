# LongevityOS

**A personal longevity operating system.** Upload your own wearable, clinical, omics, and
imaging data; LongevityOS builds a growing, private knowledge base about *you*, scores your
multimodal biological aging, and recommends evidence-grounded interventions — powered by a
multimodal foundation model and an agentic discovery engine validated on the AI-READI cohort.

---

## The idea in one picture

```
   AI-READI research engine                LongevityOS (this repo)
   (population → knowledge)                 (knowledge → the individual)
  ┌───────────────────────────┐           ┌──────────────────────────────┐
  │ • Foundation model (JEPA) │  export   │ engine/   research substance  │
  │ • Agentic discovery       │ ───────▶  │ backend/  FastAPI app layer   │
  │ • Hypothesis backbone     │ artifacts │ frontend/ polished personal UI│
  │ • Validated findings      │  + cards  │ data/     YOUR growing record │
  └───────────────────────────┘           └──────────────────────────────┘
```

The companion **showcase website** (`vector-longevityos`) presents the *research engine*.
**This repo** is the *interactive product*: an app a real person uses to understand and act on
their own data.

## Two surfaces

| Surface | What it is | Where |
| --- | --- | --- |
| **Showcase site** | Marketing/explainer for the research engine and science | separate repo |
| **Interactive app** | Upload → personal knowledge base → scores → interventions | `frontend/` + `backend/` here |

## Repository layout

```text
LongevityOS/
  engine/                 Research substance copied from AI-READI (the "knows about it" core)
    foundation_model/     Multimodal JEPA encoders (inference-only here; trained on the cluster)
    agentic/              Agentic discovery framework (agentic_discovery + agents)
    hypothesis/           Hypothesis-driven backbone + 27 stored hypotheses
    science/              Loaders, feature formulas, coupling, aging-clock scoring
    knowledge_cards/      Validated findings distilled as evidence priors the agent cites
  backend/                FastAPI app: users, ingest, knowledge base, scoring, agent, interventions
  frontend/               Next.js + Tailwind + shadcn/ui interactive app (build locally)
  data/
    demo_users/           Synthetic sample users so the app runs without the AI-READI dataset
  model_artifacts/        Exported frozen models + reference distributions (weights gitignored)
  docs/                   Architecture, build guide, frontend spec, demo script, claims map
```

## Quickstart (local)

```bash
# 1. Backend (Python)
cd backend
pip install -r requirements.txt
uvicorn longevityos_api.main:app --reload --port 8000
# open http://localhost:8000/docs  (interactive API)

# 2. Frontend (Node 20+)
cd ../frontend
npm install
npm run dev
# open http://localhost:3000
```

The backend serves a synthetic demo user out of the box, so the frontend has real-shaped data
to render before you wire in your own uploads.

## Documentation

- **[docs/BRAINSTORM.md](docs/BRAINSTORM.md)** — vision, the research→individual reframe, design rationale
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** — components, data flow, per-user knowledge base
- **[docs/BUILD_GUIDE.md](docs/BUILD_GUIDE.md)** — phased plan to take this from slice to product
- **[docs/FRONTEND_SPEC.md](docs/FRONTEND_SPEC.md)** — detailed spec for the polished UI (for v0 / Cursor / Claude Code)
- **[docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md)** — what to show the class + talking points for FM / agentic / hypothesis
- **[docs/PROVENANCE.md](docs/PROVENANCE.md)** — exactly what was copied from AI-READI and at which commit
- **[docs/research_engine/](docs/research_engine/)** — the original research design docs (FM, agentic, hypothesis)

## Provenance & data ethics

`engine/` is a curated copy of the AI-READI research workspace at commit `1530e4c`
(2026-05-21). **No AI-READI participant data is included** — only source code, design docs, and
distilled findings. Demo users are synthetic. Do not commit real personal health data; `data/`
upload paths are gitignored.
