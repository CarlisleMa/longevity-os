# Frontend Spec — the polished interactive app

A concrete, build-ready spec for the LongevityOS user app. Detailed enough to hand to **v0,
Cursor, or Claude Code** and get a beautiful, consistent result. Build locally in `frontend/`.

> North star: it should feel like a **premium health product** — calm, trustworthy, data-dense
> but uncluttered — and visually continuous with the showcase site.

---

## 1. Stack

- **Next.js 14** (App Router, TypeScript, RSC where natural)
- **Tailwind CSS** + **shadcn/ui** (Radix primitives)
- **Framer Motion** for transitions/micro-interactions
- **Recharts** (or visx) for trajectories, radar, sparklines
- **lucide-react** icons
- **TanStack Query** for backend data fetching (REST against `http://localhost:8000`)
- State: keep it simple — server state via Query, light UI state via React.

## 2. Design system

**Brand voice:** clinical-grade calm meets optimistic vitality. Confident, never hypey. "Your
biology, understood." Avoid fear-based framing.

**Palette (dark-first, with a light mode):**

```
--bg            #0B0F17   near-black ink (app background)
--surface       #121826   cards
--surface-2     #1A2233   elevated / hover
--border        #232C3D
--text          #E6EAF2   primary text
--text-muted    #9AA7BD   secondary text
--vital         #14B8A6   primary accent — vitality / "good" (teal)
--vital-soft    #0E7E72
--ai            #7C6CF6   secondary accent — AI / agentic elements (violet)
--good          #34D399   score: healthy
--watch         #FBBF24   score: monitor
--risk          #F87171   score: attention
```

Light mode: invert to off-white surfaces (#FFFFFF / #F6F8FB), ink text (#0B0F17), same accents.

**Typography:** Geist Sans (UI) + Geist Mono (numbers/metrics). Optional serif (e.g., Newsreader)
for hero headline only. Big, confident metric numerals in mono.

**Shape & depth:** radius `xl` (16px) on cards, soft shadows, 1px hairline borders, generous
whitespace, subtle gradient glows behind hero metrics (teal→violet at ~8% opacity).

**Motion:** 150–250ms ease-out; cards fade+rise 8px on mount; numbers count up; gate verdicts
stamp in. Respect `prefers-reduced-motion`.

## 3. Information architecture (routes)

```
/                      Landing (product story; CTA → /onboarding)
/onboarding            Upload / connect data; pick or create a user
/dashboard             The home surface: biological-age scorecard + highlights
/knowledge-base        Everything known about you, by modality, growing over time
/knowledge-base/[topic]  Drill-down (e.g., glucose–HR coupling) with the evidence cards
/interventions         Recommended actions, each with gates + cited evidence
/timeline              N-of-1 trajectories across ingest events
/about                 How it works (links the research engine / FM / agentic / hypotheses)
```

## 4. Screens

### 4.1 Landing `/`
Hero: headline ("Your biology, understood."), subhead, primary CTA. Below: a 3-step "how it
works" (Upload → Understand → Act), a tasteful animated metric preview (faux scorecard), and a
strip linking to the research engine ("Backed by a multimodal foundation model validated on
2,280 participants"). Footer with the **not-medical-advice** line.

### 4.2 Onboarding `/onboarding`
- Big drag-drop upload zone (accepts wearable export, labs, image files).
- "Connect a source" tiles (Apple Health, Garmin, Fitbit, Upload labs) — tiles that aren't built
  yet show a subtle "Coming soon" badge (honest).
- "Or explore with a demo profile" → loads the synthetic user. **Default path for the demo.**
- On submit: a friendly processing state (parsing → computing features → scoring → done),
  then route to `/dashboard`.

### 4.3 Dashboard `/dashboard` — the centerpiece
Layout: a hero scorecard + a responsive grid of insight cards.

- **Biological Age Scorecard** (hero): big mono numeral for biological age, chronological age
  beside it, an **AgeAccel** delta chip (e.g., "−2.3 yrs younger"), a percentile context line,
  and the **N-of-1 delta** ("↓ 0.4 yrs vs your 90-day baseline"). Subtle teal→violet glow.
- **System radar**: per-system aging (cardiac, metabolic, retinal, etc.) as a radar/spider chart.
- **Coupling card**: cross-modal coupling metrics (e.g., glucose–HR), with a "vs baseline"
  trend and a one-line plain-language read.
- **Latest agent insight**: a short, cited observation from the agent ("Your glucose–HR coupling
  is blunted in post-meal windows — see evidence") linking to the knowledge base.
- **Top intervention**: one recommended action card (see 4.5) surfaced here.

States: skeleton loaders; empty state ("Upload data to begin"); error toast.

### 4.4 Knowledge Base `/knowledge-base`
"Everything LongevityOS knows about you." Grouped by modality (Wearable, Glucose, Cardiac,
Retinal, Clinical, Environment). Each item is a **knowledge card**:
- a metric/finding about the user, its value + trend,
- the **evidence chip** (which research knowledge card / hypothesis backs the interpretation),
- a confidence indicator and "as of <date>".
Drill-down `[topic]` shows the trajectory, the raw-ish derived features, and the full evidence
(pulls from `engine/knowledge_cards/` via the backend).

### 4.5 Interventions `/interventions`
List of recommendation cards. **Each card must show the gates** — this is the signature UI:
```
┌────────────────────────────────────────────────┐
│ Shift carbs earlier in the day            ● new │
│ Rationale: post-meal glucose–HR coupling is     │
│ blunted in your evening windows.                │
│ Evidence: [card] H-NEW13 sleep-wake coupling    │
│ Gates:  ✓ Evidence-grounded  ✓ Personalized     │
│         ✓ Safety (wellness-scoped)              │
│ Expected: better overnight HRV  ·  Effort: low  │
│ [ Accept ]  [ Dismiss ]  [ Why this? ]          │
└────────────────────────────────────────────────┘
```
"Why this?" opens a sheet with the agent's reasoning trace + the cited evidence. Accepted
interventions move to a "Tracking" tab (outcome logging is roadmap — label it).

### 4.6 Timeline `/timeline`
Horizontal time axis of ingest events; selecting two compares scorecards (the N-of-1 story).
Trajectory line charts per key metric with the user's own baseline band.

### 4.7 About `/about`
Plain-language "how it works," and an honest "what's real vs roadmap" (mirror
`CLAIMS_VS_IMPLEMENTED.md`). Link to the showcase site and name the substance: foundation model
(JEPA), agentic gates, 27 hypotheses.

## 5. Signature components (build these first)

1. `BiologicalAgeScorecard` — hero metric with AgeAccel + N-of-1 delta.
2. `SystemRadar` — per-system aging radar.
3. `TrajectorySparkline` / `BaselineDeltaChip` — the N-of-1 primitives.
4. `EvidenceChip` — links a UI claim to a research knowledge card (the trust primitive).
5. `InterventionCard` — with the three gate badges.
6. `AgentReasoningSheet` — streamed reasoning trace (SSE-ready), citations inline.
7. `UploadDropzone` — drag-drop + source tiles.

## 6. API contract (backend at `:8000`)

See `backend/longevityos_api/` and `/docs`. Expected endpoints (representative mode returns the
demo user):

```
GET  /api/users                       → list users (incl. demo)
POST /api/users                       → create user
POST /api/ingest/{user_id}            → upload files (multipart) → ingest event
GET  /api/users/{id}/dashboard        → scorecard + system scores + highlights
GET  /api/users/{id}/knowledge-base   → grouped knowledge cards (+ evidence refs)
GET  /api/users/{id}/timeline         → ingest events + trajectories
GET  /api/knowledge-cards             → research evidence priors (for EvidenceChip)
POST /api/users/{id}/agent/observe    → run agent over current state → observations (SSE optional)
GET  /api/users/{id}/interventions    → recommendations w/ gate verdicts + evidence
POST /api/users/{id}/interventions/{iid}:accept
```

Use TanStack Query; show optimistic UI on accept/dismiss. Stream agent output via SSE if present,
else render the final payload.

## 7. Quality bar

Responsive (mobile → desktop), full dark/light, skeleton + empty + error states everywhere,
keyboard-accessible (Radix gives most of this), `prefers-reduced-motion` honored, Lighthouse
≥ 90. No lorem ipsum in the demo — use the demo user's real-shaped values from the backend.
