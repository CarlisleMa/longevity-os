# LongevityOS — Vision & Design Brainstorm

This document captures *why* LongevityOS is organized the way it is, so the workspace (and any
AI coding tool working in it) understands the intent. It is the thinking behind the structure.

---

## 1. The one reframe that drives everything

The AI-READI project is a **research engine**: it turns a *population* (2,280 participants) into
*knowledge* — trained aging clocks, validated cross-modal coupling findings, a multimodal
foundation model, and a corpus of critiqued hypotheses.

**LongevityOS is the inverse — an application engine**: it turns that *knowledge* back onto a
*single individual* who uploads their own data.

```
AI-READI:      many people   → models + findings        (discovery)
LongevityOS:   models + findings → one person's insight  (application)
```

The practical consequence: **we do not fork the research; we consume its outputs.** The bridge
between the two projects is *not* the dataset (we deliberately leave that behind). It is a small
set of **exported artifacts** — frozen model coefficients, normalization statistics, reference
distributions, and distilled "knowledge cards." Those are kilobytes, and they are the real value
transfer. The AI-READI repo stays the place where models are trained and findings validated;
LongevityOS imports the frozen products.

## 2. The N-of-1 insight (why this is scientifically honest)

A cohort-trained aging clock applied to one person has wide error bars. If we only ever said
"you are in the 60th percentile of biological age," that would be statistically shaky for an
individual.

The fix is to **lead with within-person change against the user's own growing baseline.** That
is a true N-of-1 control and is cleaner than cohort-relative scoring:

> "Your glucose–heart-rate coupling dropped 15% versus your own 3-month baseline"

is a stronger, more defensible statement than

> "Your coupling is below the cohort median."

So the product shows **both**: cohort context (percentile, for orientation) *and* personal
trajectory (the headline). This reuses AI-READI's existing rigor culture (train-only fitting,
negative controls, honest uncertainty) rather than abandoning it.

## 3. What we reuse, adapt, and build

| Disposition | From AI-READI | Why |
| --- | --- | --- |
| **Reuse ~as-is** | loaders, feature formulas (`aging_scores`, `features_wearable`), `coupling_features`, the per-person `multimodal` accessor | These are already **per-person** computations. A single user's upload produces the same feature vector. |
| **Adapt (train→score)** | aging clocks, retinal/cardiac/unified clocks | Split into *train* (stays in AI-READI) and *score* (here, loads a frozen model). LongevityOS never retrains; it applies. |
| **Reuse the framework** | `agentic_discovery` runtime + reviewer gates, modality/reasoning agents | The guarded-tool + 3-reviewer-gate pattern becomes the **intervention safety pipeline**. |
| **Frozen encoders** | RETFound, ECGFounder, JEPA window encoder | Pure feature extractors. Upload an OCT/ECG/CGM stream → embedding. No retraining. |
| **Distill to evidence** | 27 hypotheses, JEPA summary, coupling atlas | Become **knowledge cards** the agent cites when reasoning about a person. |
| **Leave behind** | the dataset, SLURM batch infra, cohort hypothesis loops, research figures | Cohort-scale machinery, irrelevant to an interactive single-user app. |

## 4. The central new abstraction: a growing per-person knowledge base

Everything new orbits one object — a **versioned, longitudinal per-user record**:

```
raw uploads → normalized streams → features/scores @ each timepoint
           → embeddings → agent-written observations → interventions tried + outcomes
```

Indexed by ingest date so we can show *trajectories* (their own baseline), and exposed to the
agent via retrieval over (their history + the knowledge cards). As data grows, we re-score and
surface change. **The knowledge base is the moat** — the longer someone uses LongevityOS, the
better it models them.

## 5. The intervention engine (and why the reviewer gates matter)

Given a person's current state + relevant knowledge cards + literature, an agent proposes
interventions. Critically, every suggestion passes through **safety/evidence gates** before the
user sees it — a direct repurposing of AI-READI's `agentic_discovery` reviewer pattern:

| AI-READI reviewer gate | LongevityOS intervention gate |
| --- | --- |
| scientific-critic | **evidence-grounding** — is this backed by a knowledge card or citation? |
| feasibility-leakage | **personalization** — does it fit *this* person's data, constraints, contraindications? |
| mechanical-verifier | **safety** — wellness-scoped, not medical advice; flag anything requiring a clinician |

Each recommendation ships with the evidence card behind it. This is both safer and a great
"responsible AI" story for the class.

## 6. Two frontends

- **Showcase site** (`vector-longevityos`, separate repo): explains the *research engine* — the
  foundation model, the agentic discovery system, the science. Marketing/explainer surface.
- **Interactive app** (`frontend/` here): the thing a real person *uses* — upload, dashboard,
  knowledge base, interventions. Polished, beautiful, genuinely interactive. Built locally.

They should feel like one product (shared brand, palette, typography). See
[`FRONTEND_SPEC.md`](FRONTEND_SPEC.md).

## 7. Design principles

1. **Vertical slice over breadth.** One thing working end-to-end (upload → score → one
   evidence-grounded intervention) beats ten half-features. Class projects reward the slice.
2. **Lead with real substance.** The foundation model, agentic framework, and hypothesis
   backbone are real and present in `engine/` — build the experience on them.
3. **Privacy by construction.** Local-first; send *derived features / de-identified summaries* to
   the LLM, never raw PHI. Per-user isolation.
4. **Wellness, not medicine.** Framing and the safety gate keep recommendations informational.
5. **Show the substance.** The foundation model, agentic framework, and hypothesis backbone are
   real and present in `engine/`. The demo points at real code, even where the app wraps it.

## 8. What "good" looks like for the demo

A classmate watches you:
1. Upload a (synthetic) person's wearable + labs + an OCT image.
2. Watch the knowledge base populate: biological-age scorecard, coupling metrics, retinal embedding.
3. See the agent reason over it, cite a knowledge card ("event windows concentrate glucose–HR
   coupling — yours is blunted"), and propose a gated, evidence-linked intervention.
4. Add a second timepoint and watch the *trajectory* update — the N-of-1 story.

Behind it, you can open `engine/` and show the actual JEPA model, the agentic reviewer gates, and
the 27 hypotheses that back the claims.
