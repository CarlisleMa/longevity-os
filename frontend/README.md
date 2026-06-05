# LongevityOS Frontend

Polished interactive app (Next.js 14 + Tailwind + TanStack Query). This is a **runnable
starting point** wired to the backend — the landing page and dashboard work end-to-end against
the demo user. Build out the remaining screens from [`../docs/FRONTEND_SPEC.md`](../docs/FRONTEND_SPEC.md)
using v0 / Cursor / Claude Code.

## Run

```bash
cp .env.local.example .env.local      # NEXT_PUBLIC_API_BASE=http://localhost:8000
npm install
npm run dev                           # http://localhost:3000
```

The backend must be running (`uvicorn longevityos_api.main:app --port 8000`). With it up, `/` is
the landing page and `/dashboard` renders the demo user's scorecard, coupling, agent insight, and
gated interventions from the live API.

## What's here

- `app/` — App Router pages: `/` (landing), `/dashboard` (centerpiece). Routes named in
  `components/nav.tsx` (`/knowledge-base`, `/interventions`, `/timeline`, `/about`) are **stubs to
  build** per the spec.
- `components/` — signature components already built: `BiologicalAgeScorecard`, `CouplingCard`,
  `InterventionCard` (with the 3-gate row), `EvidenceChip`.
- `lib/` — `api.ts` (typed client), `types.ts` (mirrors the backend schema), `utils.ts`.
- Design system — palette/typography/motion tokens in `app/globals.css` + `tailwind.config.ts`.

## Design system

Dark-first, teal (`--vital`) + violet (`--ai`) accents, mono numerals for metrics. See the full
palette and component spec in [`../docs/FRONTEND_SPEC.md`](../docs/FRONTEND_SPEC.md). To match the
showcase site, port its exact brand tokens into `globals.css`.

## Next screens to build (from the spec)

1. `/onboarding` — upload dropzone + "explore demo profile".
2. `/knowledge-base` — grouped knowledge cards with evidence chips (API: `/api/users/:id/knowledge-base`).
3. `/interventions` — full list (reuse `InterventionCard`).
4. `/timeline` — N-of-1 trajectories (API: `/api/users/:id/timeline`, use Recharts).
5. `/about` — how it works; mirror `../docs/CLAIMS_VS_IMPLEMENTED.md`.

Consider adding shadcn/ui (`npx shadcn@latest init`) for richer primitives — the tokens here are
already shadcn-compatible.
