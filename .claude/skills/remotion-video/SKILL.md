---
name: remotion-video
description: Build programmatic motion-graphics videos with Remotion (React → MP4). Use when the user wants to create a demo video, explainer, product tour, animated video, or "make a video" from code; render to MP4; add AI voiceover/narration; or sync visuals to audio. Covers project scaffolding, scene composition, brand theming, OFFLINE fonts (critical in CI/sandboxes), ElevenLabs voiceover with auto duration-sync, captions, and rendering in restricted/TLS-intercepting environments.
---

# Remotion video skill

Build a polished, code-defined video and render it to MP4. Remotion renders a React
app frame-by-frame in headless Chrome, so everything is normal React + CSS + SVG, driven
by the current frame.

## When to use
- "Make a demo/explainer/launch video", "animate this", "turn my project into a video".
- Class/demo submissions that should map to a rubric (put rubric tags on-screen).
- Any time you need a deterministic, re-renderable video instead of screen-recording.

## Mental model (the 5 APIs you actually need)
- `useCurrentFrame()` — current frame **relative to the enclosing `<Sequence>`** (0 at its start).
- `useVideoConfig()` — `{fps, width, height, durationInFrames}` of the **composition** (NOT the sequence — a common bug; pass a scene's own length down as a prop if a child needs it).
- `interpolate(frame, [inFrames], [outValues], {extrapolateLeft/Right:'clamp', easing})` — map frames → any value.
- `spring({frame, fps, config})` — natural motion (entrances, scale stamps).
- `<Sequence>` / `<Series>` / `<AbsoluteFill>` / `<Audio>` / `staticFile()` — layout, timeline, audio, public assets.

## Project layout that works
```
video/
  package.json          # remotion, @remotion/cli, react, react-dom, typescript
  tsconfig.json         # jsx: react-jsx, moduleResolution: Bundler, strict
  remotion.config.ts    # codec h264, crf ~18, pixelFormat yuv420p
  src/
    index.ts            # registerRoot(RemotionRoot)
    Root.tsx            # <Composition id=... durationInFrames=... fps width height/>
    Main.tsx            # stitches scenes with <Series>, plays per-scene audio
    theme.ts            # colors/fonts/fps tokens (match the product's brand!)
    fonts.ts            # SELF-HOSTED fonts (see gotcha below)
    script.ts           # one source of truth: scene id, duration, voiceover, caption
    scenes/*.tsx        # one component per scene; animate off useCurrentFrame()
    components/*.tsx     # reusable Card/Chip/Scene-chrome
  scripts/generate-voiceover.mjs   # optional: ElevenLabs narration + duration sync
  public/audio/*.mp3    # generated narration (gitignore these)
```

## CRITICAL gotcha #1 — fonts must be OFFLINE
`@remotion/google-fonts` fetches woff2 from `fonts.gstatic.com` **inside the render browser**.
In CI / Claude Code on the web / corporate networks, the proxy does TLS interception and the
bundled Chromium rejects the cert (`net::ERR_CERT_AUTHORITY_INVALID`) → the render fails even
though `curl` works (different CA store). **Fix: self-host via `@fontsource`:**
```ts
import "@fontsource/inter/600.css";          // bundled by webpack, no network at render
export const fontCssVars = { "--font-sans": "'Inter', sans-serif" } as React.CSSProperties;
```
Apply the CSS vars on a top-level `<AbsoluteFill style={fontCssVars}>`.

## CRITICAL gotcha #2 — headless Chrome
First render downloads "Chrome Headless Shell" (~150 MB) from Remotion's CDN — needs egress once.
Remotion bundles its own ffmpeg, so a system `ffmpeg` is NOT required. If GL errors appear, set
`Config.setChromiumOpenGlRenderer("angle")` in `remotion.config.ts`.

## Pattern — audio-driven timing (do this for narrated videos)
Don't hand-guess scene lengths. Put the narration text in `script.ts`, generate audio, **measure
each clip**, and set each scene's `durationInFrames` from the measured length (+ ~0.8s tail). Keep
a `durations.ts` + `audioManifest.ts` that the voiceover script overwrites, so visuals lock to voice
and the video still works silently (captions only) before any audio exists.

## Pattern — ElevenLabs voiceover (incl. cloned voice)
- `api.elevenlabs.io` is usually reachable even where other hosts are blocked.
- User clones their voice (Instant Voice Cloning) → gets a `voice_id` + API key.
- Use `POST /v1/text-to-speech/{voice_id}/with-timestamps?output_format=mp3_44100_128`. The response
  has `audio_base64` (write to mp3) **and** `alignment.character_end_times_seconds` whose last value
  ≈ clip duration — so you get durations WITHOUT needing ffprobe.
- Never commit API keys; read from env; gitignore the generated mp3s.
- No key available? Build the captioned + music-bed version and a timed VO script so the user records
  or generates narration later; wire `<Audio>` so it drops in with no code change.

## Pattern — captions / stands-alone-on-mute
Render a bottom subtitle band per scene that fades in/out using the scene's OWN duration (pass it as a
prop — see gotcha on `useVideoConfig`). Lets the video communicate even with sound off (accessibility +
grading).

## Pattern — rubric/criteria chips (class & grant demos)
If the work is graded, show it. Put a small "RUBRIC · <criterion>" chip in a corner of each scene so a
grader can see exactly which requirement each beat satisfies, and add explicit Disclosure + Evaluation
scenes (AI usage, citations, limitations, validation).

## Design tips that read well at 1080p
- Steal the product's real palette + fonts (parse its CSS) so the video feels native to the app.
- Body text ≥ 22px, headlines 48–96px; keep scene content inside a safe area above the caption band.
- Recreate real UI (scorecards, charts, chips) as components and animate them in with `spring`/stagger,
  rather than slapping bullet points on slides.
- Stagger entrances ~3–6 frames apart; prefer `spring` damping ~200 for calm motion.

## Commands
```bash
npm install
npm run dev                 # remotion studio — live preview while editing
npm run still -- --frame=N  # spot-check one frame to a PNG (fast QA; build a contact sheet)
npm run render              # → out/<name>.mp4
ELEVENLABS_API_KEY=... node scripts/generate-voiceover.mjs   # narrate, then re-render
```

## QA loop without watching the video
Render stills at each scene's midpoint and tile them into one contact-sheet PNG (Pillow) to verify
layout/overflow fast. Tighten any scene whose content collides with the caption band, then full-render.
Render time scales with frame count × resolution; use `--concurrency` ≈ CPU cores.
