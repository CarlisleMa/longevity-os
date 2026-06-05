# LongevityOS Frontend

Polished interactive app (Next.js 14 + Tailwind + TanStack Query + Recharts + Framer Motion),
wired to the backend and running on the synthetic demo user end-to-end.

## Run

```bash
cp .env.local.example .env.local      # NEXT_PUBLIC_API_BASE=http://localhost:8000
npm install
npm run dev                           # http://localhost:3000
```

The backend should be running (`uvicorn longevityos_api.main:app --port 8000`). The app degrades
gracefully and shows a clear "start the backend" state if the API is unreachable.

## Pages (all built)

- `/` — landing: editorial hero, animated scorecard preview, how-it-works, research strip.
- `/onboarding` — upload dropzone + source tiles (honest "coming soon") + demo-profile path.
- `/dashboard` — centerpiece: biological-age scorecard (count-up), **system radar**, coupling,
  cited agent insight (re-observe), and gated intervention cards.
- `/knowledge-base` — your record by modality + the **evidence library** (research knowledge
  cards the `EvidenceChip`s link to via `#KC-…` anchors).
- `/interventions` — Recommended / Tracking tabs; each card shows the **three safety gates**.
- `/timeline` — N-of-1 trajectory (Recharts) with a baseline band + per-ingest detail.
- `/about` — how it works + an honest "what's real vs roadmap" ledger.

## Design system

Warm, editorial, science-journal aesthetic — **matched to the showcase site
(longevity-os.xyz)**: ivory paper background (`--bg #FCFBF8`), near-black ink, warm greige
hairlines, a vivid **orange** primary (`--vital`), **indigo** for agentic/AI elements (`--ai`),
and muted sage / terracotta status. Display in **Playfair Display** (serif), body in **Inter**,
metrics in **JetBrains Mono** — all via `next/font` (see `app/fonts.ts`). Tokens live in
`app/globals.css` + `tailwind.config.ts`; a `.dark` variant is wired for a future toggle.

## Structure

- `app/` — App Router pages + `fonts.ts`, `providers.tsx`, `globals.css`.
- `components/` — signature pieces: `BiologicalAgeScorecard`, `SystemRadar`, `TrajectoryChart`,
  `CouplingCard`, `InterventionCard` (3-gate row), `KnowledgeCard`, `EvidenceChip`, plus
  `ui/` primitives (`button`, `badge`, `card`) and `motion` (`Reveal`, `CountUp`).
- `lib/` — `api.ts` (typed client), `types.ts` (mirrors the backend schema), `utils.ts`.
