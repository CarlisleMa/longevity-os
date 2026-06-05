# LongevityOS — demo video (Remotion)

A code-defined, programmatic motion-graphics video that walks through LongevityOS and the research
engine beneath it (the **AI-READI** dataset, the **JEPA foundation model**, and the **agentic
discovery system**). Built with [Remotion](https://www.remotion.dev/docs/) — every scene is React +
SVG animated off the current frame, so it's deterministic and re-renderable.

> ~5.5 min · 1920×1080 · H.264 MP4. On-brand with the app (same palette + Playfair / Inter / JetBrains
> Mono). Narration is generated in the author's **cloned voice** via ElevenLabs and the visuals are
> auto-synced to it; the video also stands alone on mute via timed captions.

## Quickstart

```bash
cd video
npm install
npm run dev            # Remotion Studio live preview (http://localhost:3000)
npm run render         # → out/longevityos-demo.mp4
```

First render downloads a headless Chrome shell (~150 MB) once. Remotion bundles its own ffmpeg.

## Add voiceover (optional, in your own cloned voice)

1. ElevenLabs → **Voices → Add Voice → Instant Voice Cloning** (upload ~1–2 min of clean audio).
2. Get your **API key** (and optionally the cloned **voice id**).
3. Generate narration + auto-sync scene durations, then re-render:

```bash
export ELEVENLABS_API_KEY=sk_...          # required (never commit this)
export ELEVENLABS_VOICE_ID=...            # optional; auto-detects your cloned voice if omitted
npm run voiceover                          # writes public/audio/*.mp3 + src/durations.ts + manifest
npm run render
```

The script pulls each scene's narration straight from `src/script.ts`, writes one MP3 per scene, and
measures each clip (via ElevenLabs timestamp alignment) so the visuals lock to your voice. Without a
key, the video renders silently with captions — the audio drops in later with no code change.

## What's in it (and how it maps to the rubric)

| # | Scene | Rubric criterion |
|---|-------|------------------|
| 1 | Hook — "Your biology, understood" | — |
| 2 | Problem & the run-it-in-reverse insight (N-of-1) | **Problem & Insight** |
| 3 | The data: AI-READI (2,280 people · 9 synced modalities · ~4 TB) | **Evaluation & Evidence** |
| 4 | The JEPA foundation model I trained (+ adversarial controls, *Nature Aging* submission) | **Execution & Technical Work** |
| 5 | The agentic discovery system (Claude Agent SDK · 3 reviewer gates · 27 hypotheses) | **Execution & Technical Work** |
| 6 | The app: Upload → Understand → Act | **Execution & Technical Work** |
| 7 | Dashboard: biological-age scorecard · system radar · coupling | **Execution & Technical Work** |
| 8 | Evidence grounding: knowledge card → hypothesis citation | **Evaluation & Evidence** |
| 9 | Interventions: 3 gates + multi-agent care team | **Execution & Technical Work** |
| 10 | How we know it's real: control-validation · honest ledger · N-of-1 | **Evaluation & Evidence** |
| 11 | Integrity & disclosure | **Process, Integrity & Disclosure** |
| 12 | Close | **Communication & Presentation** |

Each scene shows a `RUBRIC · <criterion>` chip so a grader can see what each beat addresses.

## Editing

- **All copy + timing:** `src/script.ts` (one source of truth: `id`, `durationS`, `vo`, `caption`, `rubric`).
- **Brand tokens:** `src/theme.ts` (lifted from the app's `globals.css`).
- **Scenes:** `src/scenes/*.tsx` — animate off `useCurrentFrame()`.
- **Scene chrome (brand mark, rubric chip, caption band):** `src/components/Scene.tsx`.
- **Stitching + audio:** `src/Main.tsx`.

Change a line of narration → re-run `npm run voiceover` → `npm run render`. Durations follow the voice.

## Fast QA without watching

```bash
npm run still -- --frame=3100         # render any frame to a PNG
```
The numbers in `src/Main.tsx` (`TOTAL_FRAMES`) and the per-scene fallbacks make it easy to compute a
scene's midpoint frame; render those into one contact sheet to check layout quickly.

## Accuracy & sourcing

Figures shown are drawn from the repo's research docs — `docs/research_engine/reference/DATA.md`
(AI-READI), `docs/research_engine/reports/JEPA_SYSTEMATIC_SUMMARY_20260428.md` (control results),
`docs/research_engine/reports/agentic_results/` (coupling AUROC, clocks), and `engine/hypothesis/`
(the 27 hypotheses). See `../docs/PROVENANCE.md` for what is original vs. borrowed.

**Wellness & informational — not medical advice.** Demo data is synthetic.
