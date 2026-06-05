// Single source of truth for the narration + scene timing.
//
// Each scene has:
//   id        — stable key, also the audio filename (public/audio/<id>.mp3)
//   rubric    — which rubric criterion this beat primarily serves (shown as a chip)
//   durationS — fallback duration in seconds (used until real VO audio exists)
//   vo        — the voiceover script (fed to ElevenLabs in your cloned voice)
//   caption   — on-screen subtitle (so the video stands alone, silent)
//
// When real narration is generated, scripts/generate-voiceover.mjs measures each
// clip and writes the measured durations to src/durations.json, which overrides
// durationS so the visuals lock exactly to your voice.

export type RubricTag =
  | "Problem & Insight"
  | "Execution & Technical Work"
  | "Evaluation & Evidence"
  | "Communication & Presentation"
  | "Process, Integrity & Disclosure";

export interface SceneDef {
  id: string;
  rubric?: RubricTag;
  durationS: number;
  vo: string;
  caption: string;
}

export const SCENES: SceneDef[] = [
  // ── ACT 1 — Problem & insight ──
  {
    id: "title",
    durationS: 14,
    vo: "Longevity research lives in cohorts and papers. But a person can't act on a paper. LongevityOS is the layer that brings validated longevity science to a single individual. Your biology, finally understood.",
    caption: "LongevityOS — bringing validated longevity science to one person: you.",
  },
  {
    id: "problem",
    rubric: "Problem & Insight",
    durationS: 32,
    vo: "Here's the problem. Population studies turn thousands of people into knowledge — aging clocks, biomarkers, cross-system patterns. But that knowledge stops at the journal. The insight behind LongevityOS is to run that engine in reverse: take models validated on a population, and turn them onto one person's own data. And because a cohort clock on a single person has wide error bars, we lead with the honest signal — how you're changing against your own baseline. An N-of-1 control.",
    caption:
      "Research turns a population into knowledge — but it stops at the journal. We run the engine in reverse, onto one person, and lead with within-person change.",
  },

  // ── ACT 2 — The research engine (dataset → foundation model → agentic system) ──
  {
    id: "dataset",
    rubric: "Evaluation & Evidence",
    durationS: 34,
    vo: "It starts with the data. AI-READI — the Artificial Intelligence Ready and Exploratory Atlas for Diabetes Insights — is an N.I.H. Bridge-to-A.I. flagship cohort: two thousand two hundred and eighty people, across three clinical sites, spanning the full spectrum from healthy to insulin-dependent diabetes. For each person, nine synchronized modalities — clinical labs, a twelve-lead E.C.G., four kinds of retinal imaging, plus a ten-day window of continuous glucose, wearable, and home-environment streams sampled as often as every five seconds. Roughly four terabytes of densely aligned human physiology.",
    caption:
      "AI-READI — NIH Bridge2AI cohort · 2,280 people · 3 sites · 9 synchronized modalities · ~10-day continuous glucose + wearable + environment · ~4 TB.",
  },
  {
    id: "jepa",
    rubric: "Execution & Technical Work",
    durationS: 44,
    vo: "Most models squash those ten days into summary statistics — throwing the physiology away. So I trained a foundation model that doesn't. It's a joint-embedding predictive architecture — a JEPA — that treats the body as one coupled dynamical system, and learns whether the recent past of your glucose, heart rate, activity, and environment can predict their own near future. The test is adversarial. Real, time-aligned windows have to beat windows from the wrong day, and from the wrong person. Across thirty-six G.P.U. runs and four time horizons, they did — every time. Aligned physiology is genuinely more predictable, and the advantage decays with time, exactly as real biology should. This foundation-model work is currently under submission to Nature Aging.",
    caption:
      "A JEPA foundation model over synchronized physiology · aligned windows beat wrong-day & wrong-person across 36 GPU runs × 4 horizons · under submission to Nature Aging.",
  },
  {
    id: "agentic",
    rubric: "Execution & Technical Work",
    durationS: 38,
    vo: "Discovering those signals is the job of an agentic system I built on the Claude Agent SDK. A team of specialist agents — literature, hypothesis, critic, feasibility, execution, verification — proposes scientific hypotheses, runs the analyses, and checks the results. But the agents never get raw shell access — only guarded, vetted tools. And nothing is promoted until it clears three reviewer gates: a scientific critic, a feasibility-and-leakage check, and a mechanical verifier. That pipeline produced twenty-seven hypotheses, and a coupling atlas — where glucose-to-heart-rate coordination alone separates insulin-dependent from healthy at an AUROC of point eight.",
    caption:
      "Agentic discovery on the Claude Agent SDK · guarded tools, no raw shell · 3 reviewer gates · 27 hypotheses + a coupling atlas (AUROC 0.80).",
  },

  // ── ACT 3 — The application (LongevityOS) ──
  {
    id: "howitworks",
    rubric: "Execution & Technical Work",
    durationS: 20,
    vo: "LongevityOS turns that engine onto you, in three moves. Upload your wearable, lab, imaging, and clinical data — private and local-first. Understand it: a growing knowledge base scores your multimodal biological age and the coupling between your systems. And act: evidence-grounded interventions, each one gated for safety.",
    caption: "The app: Upload → Understand → Act. A private, growing model of you.",
  },
  {
    id: "dashboard",
    rubric: "Execution & Technical Work",
    durationS: 32,
    vo: "This is the dashboard. Your biological age — forty-four point seven against a chronological forty-seven — two point three years younger, and trending down versus your own baseline. The system radar breaks it down: cardiac, metabolic, retinal, and more. And the coupling card surfaces something a single number can't: your glucose-heart-rate coupling is blunted after meals — a cross-system signal straight out of the foundation model.",
    caption:
      "Biological age 44.7 vs 47 chronological · −2.3 yrs, trending down vs your baseline · system radar · glucose–HR coupling, blunted post-meal.",
  },
  {
    id: "evidence",
    rubric: "Evaluation & Evidence",
    durationS: 22,
    vo: "Every interpretation is grounded. Open any knowledge card and click its evidence chip — this one traces straight back to a hypothesis from the research engine. Nothing here is a vibe. Each claim is tied to a tested finding you can inspect.",
    caption: "Every interpretation traces to a tested finding — e.g. hypothesis H-NEW13.",
  },
  {
    id: "interventions",
    rubric: "Execution & Technical Work",
    durationS: 30,
    vo: "When LongevityOS recommends an action, it passes three gates: evidence-grounded, personalized to your data, and safety-checked. Hit 'Why this?' and you see the agent's reasoning, and its citation. Behind it, a multi-agent care team debates the recommendation — the same guarded reviewer pattern the research engine uses to vet hypotheses — before anything reaches you.",
    caption:
      "Every recommendation passes three gates — evidence · personalized · safety — vetted by a multi-agent care team.",
  },

  // ── ACT 4 — Evidence, integrity, close ──
  {
    id: "evaluation",
    rubric: "Evaluation & Evidence",
    durationS: 30,
    vo: "How do we know any of it is real? Three ways. The foundation model is control-validated — aligned beats wrong-day, beats wrong-person, repeatedly. Every hypothesis runs through propose, critique, and verify — and the honest negatives stay in: of twenty-seven, some supported, some refuted, most still open. And on a single person, instead of leaning on a shaky cohort percentile, we lead with the cleaner signal — how you're changing against your own baseline.",
    caption:
      "Validation: control-tested foundation model · 27 hypotheses, negatives kept · N-of-1 — within-person change over cohort percentile.",
  },
  {
    id: "disclosure",
    rubric: "Process, Integrity & Disclosure",
    durationS: 32,
    vo: "Full disclosure. The research engine is curated from my own AI-READI workspace, cited by commit hash and DOI; the retinal and cardiac encoders are the published RETFound and ECGFounder models. No real participant data ships — the demo user is synthetic, per the data-use agreement. This application, and this very video, were built with Claude Code, and the foundation-model paper is my own work. It's wellness and informational — not medical advice. The repository, with its full commit history, is public.",
    caption:
      "Disclosure: engine from AI-READI (DOI 10.60775/fairhub.3) · RETFound + ECGFounder · synthetic data · built with Claude Code · not medical advice · public repo.",
  },
  {
    id: "close",
    rubric: "Communication & Presentation",
    durationS: 14,
    vo: "LongevityOS. The longer you use it, the better it knows you — turning validated science into a private, evidence-grounded feedback loop for your own healthspan.",
    caption: "LongevityOS — validated science, turned into a private feedback loop for your healthspan.",
  },
];
