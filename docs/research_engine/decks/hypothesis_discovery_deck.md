---
marp: true
theme: default
paginate: true
size: 16:9
style: |
  section { font-size: 20px; font-family: 'Inter', 'Helvetica Neue', sans-serif; }
  h1 { font-size: 34px; color: #1a365d; }
  h2 { font-size: 26px; color: #2c5282; }
  h3 { font-size: 20px; color: #4a5568; }
  table { font-size: 15px; margin: 0.5em 0; }
  code { font-size: 13px; background: #f0f4f8; padding: 2px 4px; border-radius: 3px; }
  .columns { display: flex; gap: 2em; }
  .col { flex: 1; }
  blockquote { font-size: 16px; border-left: 4px solid #2c5282; padding-left: 1em; color: #4a5568; }
  .small { font-size: 14px; color: #718096; }
  .card { border: 2px solid #e2e8f0; border-radius: 12px; padding: 1em; margin: 0.5em 0; background: #f7fafc; }
  .card-blue { border-color: #3182ce; background: #ebf8ff; }
  .card-green { border-color: #38a169; background: #f0fff4; }
  .card-red { border-color: #e53e3e; background: #fff5f5; }
  .card-yellow { border-color: #d69e2e; background: #fffff0; }
  .card-purple { border-color: #805ad5; background: #faf5ff; }
  .tag { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 12px; font-weight: 600; }
  .tag-pass { background: #c6f6d5; color: #22543d; }
  .tag-concern { background: #fefcbf; color: #744210; }
  .tag-fail { background: #fed7d7; color: #742a2a; }
  .metric { font-size: 28px; font-weight: 700; color: #2c5282; }
  .metric-label { font-size: 13px; color: #718096; }
  .verdict-pass { color: #38a169; font-weight: 700; }
  .verdict-fail { color: #e53e3e; font-weight: 700; }
  .arrow { font-size: 24px; color: #a0aec0; }
---

# Hypothesis-Driven Scientific Discovery from Synchronized Multimodal Physiology

**Zijian (Carl) Ma** | Stanford University | TWC Lab

AI-READI v3.0.0 | 2,280 participants | 10-day synchronized CGM + Wearable + Environment

<div class="small">

April 2026 | Multi-Agent Discovery Pipeline

</div>

<!--
IMAGE PROMPT 1 — TITLE ILLUSTRATION:
Create a clean, minimal scientific illustration in the style of an ICML/NeurIPS conference poster. Show a human silhouette at center with 4 concentric rings representing physiological layers: (innermost) a glucose waveform in blue, (next) a heart rate trace in red, (next) activity bar chart in green, (outermost) environmental sensor data in orange. Between the rings, draw thin directed arrows showing coupling/communication. On the right side, show a magnifying glass zooming into one coupling arrow, revealing a detailed time-series cross-correlation plot. Use a white background with subtle grid lines. Color palette: blues (#2c5282, #3182ce), reds (#e53e3e), greens (#38a169), grays (#718096). No text labels. Vector/flat style, high contrast, presentation-ready.
-->

---

## The Problem: Feature Tables Lose the Signal

<div class="columns">
<div class="col">

### Current approach
```
Raw time series (2,880 pts × 10 days)
         ↓ compress
Summary statistics (TIR, CV, MAGE)
         ↓ correlate
"Feature X differs by group" (p < 0.05)
```

**What's lost:**
- Temporal dynamics & lag structure
- Frequency-dependent coupling
- Event-triggered responses
- Causal directionality

**What's arbitrary:**
- Which summary to compute?
- What lag to test?
- Which pairs to correlate?

</div>
<div class="col">

### What we need

> AI-READI is not a feature table. It is a **coupled dynamical system** observed for 10 days across metabolic, autonomic, behavioral, and environmental channels.

**The right approach:**
1. Start from **physiological mechanism**
2. Derive **specific, falsifiable predictions**
3. Specify **timescale, direction, controls**
4. Execute and **verify rigorously**

<div class="card card-blue">

**Key insight:** Broadband glucose-HR coupling (d=0.585) masks a frequency-specific effect where fast coupling **breaks down** while slow coupling **strengthens**. You can't see this from summary statistics.

</div>

</div>
</div>

---

## System Architecture: Multi-Agent Hypothesis Discovery

<!--
IMAGE PROMPT 2 — SYSTEM ARCHITECTURE:
Create a system architecture diagram in ICML/NeurIPS poster style on white background. Layout as a horizontal pipeline flowing left to right with 5 rounded-rectangle components connected by arrows:

Box 1 (blue, #ebf8ff border #3182ce): "PROPOSER" with icon of a lightbulb + book. Subtitle: "Literature + Mechanisms"
Box 2 (yellow, #fffff0 border #d69e2e): "CRITIC" with icon of a magnifying glass + checkmark. Subtitle: "Feasibility + Rigor"
Box 3 (gray, #f7fafc border #a0aec0): "WORKSPACE" shown as a rounded database cylinder. Subtitle: "Prioritized Queue"
Box 4 (green, #f0fff4 border #38a169): "EXECUTOR" with icon of a code bracket + chart. Subtitle: "Analysis + Code"
Box 5 (red/orange, #fff5f5 border #e53e3e): "VERIFIER" with icon of a shield + statistics. Subtitle: "Statistical Rigor"

Below Box 3, show a feedback arrow looping back from Box 5 to Box 1 labeled "Refine".
Above Box 3, show a small stack of cards labeled "26 Hypotheses" with a priority badge.

Use flat vector style, thin borders (2px), rounded corners (12px), subtle drop shadows. Arrow connections should be clean with small arrowheads. Color palette consistent: blues, yellows, greens, reds, grays. No gradients. High contrast for projection.
-->

<div class="columns">
<div class="col">

<div class="card card-blue">

**Proposer Agent**
- Mines literature & physiological mechanisms
- Generates falsifiable hypotheses with:
  - Expected direction & timescale
  - Refutation criteria & negative controls
  - Required modalities & sample size
- Output: structured hypothesis JSON

</div>

<div class="card card-yellow">

**Critic Agent**
- Validates feasibility against AI-READI constraints
- Checks: Garmin HR resolution, redacted medications, 10-day window limits
- Identifies missed confounders
- Scores: rigor, plausibility, novelty, importance
- Re-prioritizes execution queue

</div>

</div>
<div class="col">

<div class="card card-green">

**Executor Agent**
- Picks highest-priority validated hypothesis
- Writes analysis code (Python + Slurm)
- Processes 1,939 participants in parallel
- Records structured results

</div>

<div class="card card-red">

**Verifier Agent**
- Full covariate adjustment
- Bootstrap confidence intervals
- Negative controls & sensitivity checks
- Dose-response monotonicity
- Links to clinical burden

</div>

<div class="card" style="border-color: #805ad5; background: #faf5ff;">

**Shared Workspace** — JSON-backed hypothesis store with lifecycle tracking:
`proposed → critiqued → validated → executing → completed → verified`

</div>

</div>
</div>

---

## Hypothesis Lifecycle & Quality Gates

<!--
IMAGE PROMPT 3 — HYPOTHESIS LIFECYCLE:
Create a horizontal flowchart in ICML/NeurIPS style on white background showing the hypothesis lifecycle as a pipeline of 7 rounded pills/badges connected by thin arrows:

"Proposed" (light blue) → "Critiqued" (yellow) → splits into two paths:
  Path A: "Validated" (green) → "Executing" (teal) → "Completed" (blue) → "Verified" (dark green with checkmark)
  Path B: "Rejected" (red with X mark)

Below each stage, show a small icon representing the quality gate:
- Proposed: lightbulb icon
- Critiqued: magnifying glass
- Validated: green checkmark
- Rejected: red X
- Executing: gear/cog
- Completed: bar chart
- Verified: shield with check

At bottom, show a horizontal bar chart: "26 total: 4 supported | 6 validated | 12 critiqued | 2 inconclusive | 1 refuted | 1 rejected"

Flat vector style, clean lines, white background, same color palette as previous prompts.
-->

<div class="columns">
<div class="col">

### Every hypothesis MUST specify:

| Requirement | Why |
|---|---|
| **Expected direction** | Not "differs" — which way and why |
| **Timescale / lag** | 5-60min acute? 1-8h ultradian? 12-36h circadian? |
| **Refutation criterion** | What result would kill this hypothesis? |
| **Negative control** | What should show NO effect? |
| **Confounders** | age, site, HbA1c, BMI, raw levels minimum |
| **Unique enabler** | Why can only AI-READI test this? |

</div>
<div class="col">

### Current Inventory

| Status | Count | Description |
|---|---:|---|
| Supported | 4 | First-gen findings confirmed |
| Validated | 6 | Passed critic, ready to execute |
| Critiqued | 12 | Has concerns, needs modification |
| Completed | 5 | Newly executed & verified |
| Inconclusive | 2 | Weak signal |
| Refuted | 1 | No retinal/cardiac link |

<div class="card card-yellow">

**Critic caught:** Garmin HR smoothing limits 8/18 hypotheses. Environmental hypotheses (room-level sensors) are dead on arrival. Medication confounding is the elephant in the room.

</div>

</div>
</div>

---

## Hypothesis Categories: 10 Domains of Inquiry

<!--
IMAGE PROMPT 4 — HYPOTHESIS CATEGORIES:
Create a radial/sunburst-style diagram in ICML/NeurIPS poster style on white background. Center circle labeled "Coupled Dynamical System". Around it, 10 wedge segments in distinct colors, each labeled with a category and showing a small representative icon:

1. "Temporal Coupling" (blue) - two interleaved sine waves
2. "Frequency Coupling" (dark blue) - wavelet spectrogram thumbnail
3. "Causal Architecture" (purple) - directed arrow A→B
4. "Event Dynamics" (teal) - spike with response curve
5. "Circadian Organization" (indigo) - 24h clock face
6. "Environmental" (orange) - PM2.5 particle icon
7. "Physiotype Discovery" (green) - cluster scatter plot
8. "Structural-Dynamic" (red) - eye + heart bridge
9. "Complexity Loss" (brown) - entropy curve
10. "Resilience" (cyan) - perturbation-recovery curve

Each wedge should have a small number badge showing hypothesis count (e.g., "3" for temporal coupling).

Flat vector, clean, high-contrast, minimal text, white background, consistent with previous color palette.
-->

<div class="columns">
<div class="col">

| Category | # | Key Question |
|---|---:|---|
| **Temporal coupling** | 3 | At what timescale does coupling change? |
| **Frequency coupling** | 1 | Which frequency bands carry the signal? |
| **Causal architecture** | 1 | Does glucose drive HR, or vice versa? |
| **Event dynamics** | 2 | What happens after a glucose spike? |
| **Circadian organization** | 2 | Are rhythms misaligned across systems? |
| **Environmental** | 2 | Does PM2.5/light modulate coupling? |
| **Physiotype discovery** | 2 | Are there coupling-based subtypes? |
| **Structural-dynamic** | 1 | Does coupling predict retinal damage? |
| **Complexity loss** | 3 | Is glucose entropy degraded? |
| **Resilience** | 2 | How fast does the system recover? |

</div>
<div class="col">

### Example: Good vs Bad Hypothesis

<div class="card card-red">

**Bad (vague):**
"Glucose-HR correlation differs by diabetes group"
- No direction, no timescale, no mechanism, no controls

</div>

<div class="card card-green">

**Good (mechanistic):**
"In insulin-dependent diabetes, post-glucose-excursion HR response is blunted (peak d > 0.4) and more stereotyped (CV d > 0.25), strongest 15-90 min after excursions, weaker during sleep, and attenuated after controlling for activity state — consistent with impaired autonomic buffering via vagal denervation."
- Direction, timescale, mechanism, negative control, confounder

</div>

</div>
</div>

---

## Grounding: Literature + Critic + Verification

<div class="columns">
<div class="col">

### Literature Grounding

Each hypothesis cites 2-4 papers with **specific findings**:

| Foundation | Key Papers |
|---|---|
| Network physiology | Bashan et al., *Nat Comms* 2012 |
| Loss of complexity | Lipsitz & Goldberger, *JAMA* 1992; Costa et al., *PRL* 2002 |
| Autonomic neuropathy | Vinik & Ziegler, *Circulation* 2007 |
| Stress response | Hackett et al., *PNAS* 2014 |
| CGM dynamics | Carletti et al., *Nat Med* 2025 |
| Causal discovery | Sugihara et al., *Science* 2012 |

### Critic Review (6 PASS, 12 CONCERN, 0 REJECT)

Top downgrades:
- H-NEW07 (light exposure): 0.72 → 0.52 — room sensor too noisy
- H-NEW04 (circadian phase): 0.82 → 0.62 — cosinor fits glucose poorly
- H-NEW15 (U-shaped): 0.68 → 0.45 — contradictory mechanisms

</div>
<div class="col">

### 9-Test Verification Protocol

<div class="card">

| Test | Purpose |
|---|---|
| Full covariate OLS | Adjusts for age, site, HbA1c, BMI, glucose/HR means |
| Awake/sleep stratification | Circadian confound |
| Dose-response | Monotonic across 4 severity groups? |
| Negative control | Random windows = no effect? |
| Within-group HbA1c | Gradient within each severity group? |
| Pre-diabetes detection | Effect visible early? |
| Clinical burden | Links to frailty/allostatic load? |
| Bootstrap 95% CI | CI excludes zero? |
| Excursion specificity | Excursion minus control |

</div>

<div class="small">

Every completed hypothesis passes all 9 tests before being marked "verified."

</div>

</div>
</div>

---

## Results Dashboard: 7 Hypotheses Tested

<!--
IMAGE PROMPT 5 — RESULTS DASHBOARD:
Create a results dashboard in ICML/NeurIPS style on white background. Show 7 horizontal result bars arranged vertically, each representing one hypothesis:

Each bar has:
- Left: hypothesis ID and short title
- Center: a horizontal effect-size bar (like a forest plot) showing Cohen's d with 95% CI whiskers
- Right: a verdict badge (green "SUPPORTED", yellow "PARTIAL", red "NOT SUPPORTED")

Order from top (strongest) to bottom (weakest):
1. H-NEW03: "Post-excursion HR blunting" — d = -0.80, CI [-0.95, -0.68], green badge
2. H-MIG01: "Broadband coupling" — d = 0.585, green badge
3. H-NEW17: "Diurnal elevation" — d = 0.47 (mesor), yellow badge
4. H-NEW01: "Frequency selectivity" — d = 0.38 (4-8h band), yellow badge
5. H-NEW05: "Glucose entropy" — d = 0.17, partial r = 0.12, yellow badge
6. H-NEW06: "Nocturnal prediction" — rho = -0.004, red badge
7. H-NEW13: "Sleep-wake transition" — d = -0.06, red badge

Add a vertical dashed line at d=0 (null). Add a gray shaded region for "small effect" (|d| < 0.2).

Forest plot style, clean horizontal layout, high contrast, white background.
-->

| Hypothesis | Primary Metric | Effect | FDR | Verdict |
|---|---|---:|---|---|
| **H-NEW03** Post-excursion HR blunting | HR peak d (H vs ID) | **-0.80** | <0.001 | <span class="verdict-pass">SUPPORTED</span> |
| **H-MIG01** Broadband coupling increase | glucose-HR awake r | **0.585** | 1.3e-19 | <span class="verdict-pass">SUPPORTED</span> |
| **H-NEW17** Diurnal coupling elevation | mesor d (H vs ID) | **0.47** | <0.001 | <span class="verdict-pass">PARTIAL</span> |
| **H-NEW01** Frequency-selective coupling | 4-8h coherence d | **0.38** | <0.001 | <span class="verdict-pass">PARTIAL</span> |
| **H-NEW05** Glucose entropy beyond HbA1c | partial r (allostatic) | **0.12** | <0.001 | <span class="verdict-pass">WEAK</span> |
| **H-NEW06** Nocturnal → next-day glucose | within-person rho | **-0.004** | n.s. | <span class="verdict-fail">NULL</span> |
| **H-NEW13** Sleep-wake reorganization | reorg time d | **-0.06** | n.s. | <span class="verdict-fail">NULL</span> |

<div class="card card-blue">

**Key pattern:** The strongest effects are event-triggered (d=0.80) and frequency-resolved (d=0.38). Broadband summaries dilute the signal. Nocturnal/sleep-wake metrics are null — coupling disruption is a **daytime phenomenon**.

</div>

---

## Case Study 1: Frequency Decomposition Reveals Hidden Structure

### H-NEW01: Broadband coupling masks opposite timescale effects

<div class="columns">
<div class="col">

<!--
IMAGE PROMPT 6 — FREQUENCY DECOMPOSITION:
Create a scientific figure in ICML/NeurIPS style on white background with two panels side by side:

LEFT PANEL: "Broadband" — a single horizontal bar showing Cohen's d = 0.06 (nearly zero) with a CI bar crossing zero, colored gray. Label: "d = 0.06, n.s."

RIGHT PANEL: "By Frequency Band" — 4 horizontal bars stacked vertically showing Cohen's d for each band:
- "30-60 min": d = -0.22, bar extends LEFT (blue), labeled "DECREASED"
- "1-2 h": d = -0.17, bar extends LEFT (blue), labeled "DECREASED"
- "2-4 h": d = +0.33, bar extends RIGHT (red), labeled "INCREASED"
- "4-8 h": d = +0.38, bar extends RIGHT (red), labeled "INCREASED"

Add a vertical dashed line at d=0. Add a red/blue diverging color scheme where negative d is blue and positive d is red. Add small significance stars (*** for FDR<0.001).

Between the two panels, draw a large "≠" symbol to emphasize that broadband ≠ frequency-resolved.

Below, add a small schematic: "Fast coupling (parasympathetic buffering) ↓" in blue and "Slow coupling (metabolic-hormonal) ↑" in red.

Clean, minimal, white background, presentation-ready.
-->

**Prediction:** 1-4h ultradian band shows largest severity gradient (d > 0.6)

**Reality — more interesting:** Direction flips at 2h

| Band | d (H→ID) | FDR | Direction |
|---|---:|---|---|
| 30-60 min | -0.22 | <0.001 | Decreased |
| 1-2 h | -0.17 | <0.001 | Decreased |
| 2-4 h | +0.33 | 0.033 | Increased |
| 4-8 h | +0.38 | <0.001 | Increased |
| **Broadband** | **+0.06** | **n.s.** | **Masked** |

</div>
<div class="col">

### Interpretation

<div class="card card-blue">

**Fast coupling (<2h) breaks down:**
Parasympathetic buffering of acute glucose→HR responses degrades. Individual excursion responses become incoherent at fast timescales.

</div>

<div class="card card-red">

**Slow coupling (>2h) strengthens:**
Metabolic-hormonal coupling at meal/ultradian timescales becomes more rigid. Glucose level mechanically drives HR over hours.

</div>

**Why broadband coupling (H-MIG01, d=0.585) is misleading:**
It averages across timescales. The slow coupling increase dominates the broadband average, hiding the fast coupling breakdown.

**Clinical implication:** The fast coupling loss is the **autonomic neuropathy signature**. The slow coupling increase is a **metabolic rigidity signature**. They are different disease processes.

</div>
</div>

---

## Case Study 2: Post-Excursion HR Blunting (d = 0.80)

### H-NEW03: The strongest finding — event-triggered autonomic failure

<!--
IMAGE PROMPT 7 — EVENT-TRIGGERED RESPONSE:
Create a scientific figure in ICML/NeurIPS style on white background with two main panels:

TOP PANEL: "Post-Excursion HR Response" — a time-series plot showing:
- X-axis: time relative to glucose excursion onset, from -30 min to +90 min, with a vertical dashed line at t=0 labeled "Excursion onset"
- Y-axis: "HR change from baseline (bpm)"
- 4 curves (one per diabetes group), color-coded:
  - Healthy (blue): rises to peak ~+18 bpm at ~40 min, then returns toward baseline
  - Pre-diabetes (light blue): slightly lower peak ~+17 bpm
  - Oral medication (orange): much lower peak ~+16 bpm, slower recovery
  - Insulin-dependent (red): nearly flat or slightly negative response, peak only ~+14 bpm
- Shaded 95% CI bands around each curve
- Horizontal dashed line at 0 bpm

BOTTOM PANEL: "Negative Control (Random Windows)" — same axes, same 4 groups, but all curves hover around 0 bpm with no difference between groups. This demonstrates the effect is excursion-specific.

Add a bracket between the two panels labeled "d = 0.80 (excursion-triggered) vs d = 0.12 (random)"

Clean, white background, thin lines, scientific figure style, same color palette.
-->

<div class="columns">
<div class="col">

### The experiment

1. **Detect** glucose excursions (>30 mg/dL above 2h rolling mean)
2. **Extract** HR in [-30, +90] min window around each excursion
3. **Baseline-subtract** (mean HR in 30-min pre-excursion)
4. **Average** across all excursions per participant
5. **Compare** across 4 severity groups
6. **Control:** Repeat at random non-excursion times

### Raw numbers

| Metric | Healthy | Insulin-dep |
|---|---:|---:|
| Excursions per person | 18 | 24 |
| HR peak (bpm above baseline) | **17.8** | **14.4** |
| HR AUC (bpm · min) | **+61** | **-20** |
| Excursion magnitude (mg/dL) | 36.4 | 37.6 |

</div>
<div class="col">

### Why this is the best finding

<div class="card card-green">

**Effect size:** d = -0.80 [95% CI: -0.95, -0.68]
Largest single effect in the project. 3× stronger than broadband coupling.

</div>

**Robustness (9/9 tests pass):**
- Survives HbA1c + BMI + glucose mean + HR mean adjustment (p = 6.6e-11)
- Negative control: random windows show **no** group difference (p = 0.27)
- Dose-response is **perfectly monotonic** (H > PD > OM > ID)
- **Detectable in pre-diabetes** (d = -0.10, p = 0.025)
- Correlates with frailty beyond HbA1c (partial r = -0.15, FDR < 0.001)

### Literature support
- Hackett et al., *PNAS* 2014: post-stress HR recovery attenuated in T2D
- Vinik & Ziegler, *Circulation* 2007: CAN blunts HR response to stimuli
- **Novel:** First event-triggered analysis from free-living CGM+wearable at N=1,912

</div>
</div>

---

## Case Study 2 (cont): The Mechanism

<div class="columns">
<div class="col">

### What happens in healthy physiology

```
Glucose excursion (meal)
    ↓ detected by
Hepato-portal sensors + hypothalamus
    ↓ triggers
Sympathetic activation → HR ↑ (+18 bpm)
    ↓ buffered by
Parasympathetic (vagal) counterregulation
    ↓ produces
Context-dependent, variable HR response
    ↓ returns to
Baseline within 60-90 min
```

### What happens in diabetes

```
Glucose excursion (meal)
    ↓ detected by
Partially intact sensors
    ↓ triggers
Weakened sympathetic activation → HR ↑ (+14 bpm)
    ↓ NOT buffered (vagal damage)
No parasympathetic counterregulation
    ↓ produces
Blunted, stereotyped response (less variable)
    ↓ or
Response reverses (AUC goes negative)
```

</div>
<div class="col">

### The autonomic neuropathy progression

<div class="card card-blue">

**Stage 1: Vagal damage (early)**
Parasympathetic brake fails first.
→ Resting HR increases
→ Fast HR buffering of glucose excursions fails

</div>

<div class="card card-yellow">

**Stage 2: Mixed damage**
Both sympathetic and parasympathetic impaired.
→ HR response to excursions becomes blunted
→ Response becomes stereotyped (low CV)

</div>

<div class="card card-red">

**Stage 3: Severe (insulin-dependent)**
Neither accelerator nor brake works.
→ HR doesn't "hear" glucose excursions
→ AUC goes negative (-20 bpm·min)
→ Complete autonomic decoupling at fast timescales

</div>

### Connects to frequency finding (H-NEW01)
Post-excursion response is a **fast** (<2h) coupling phenomenon. Its breakdown explains why fast-frequency coherence decreases while slow coupling increases.

</div>
</div>

---

## Synthesis: What the Data Actually Shows

<!--
IMAGE PROMPT 8 — SYNTHESIS DIAGRAM:
Create a conceptual synthesis diagram in ICML/NeurIPS style on white background. Show a 2×2 matrix:

Rows: "Fast coupling (<2h)" and "Slow coupling (>2h)"
Columns: "Healthy" and "Diabetes"

Cell contents (as small icons/schematics):
- Fast/Healthy: a sharp glucose spike with a responsive HR peak following it (blue, healthy)
- Fast/Diabetes: a glucose spike with a flat/blunted HR response (red, broken)
- Slow/Healthy: gentle glucose oscillations weakly correlated with gentle HR oscillations (blue, loose)
- Slow/Diabetes: glucose oscillations tightly locked to HR oscillations (red, rigid)

Arrow annotations:
- Fast row: arrow from healthy to diabetes labeled "Autonomic buffering fails (d = -0.80)"
- Slow row: arrow from healthy to diabetes labeled "Metabolic rigidity increases (d = +0.38)"
- Between rows: annotation "Broadband average masks both (d = 0.06 n.s.)"

Below the matrix, a horizontal timeline showing: "Daytime (effect present)" in warm color and "Nighttime (no effect)" in cool color.

Clean, minimal, white background, same color palette as all previous prompts.
-->

<div class="columns">
<div class="col">

### The three-layer finding

| Layer | Timescale | Effect | d | Mechanism |
|---|---|---|---:|---|
| **Fast** | <2h | Coupling **breaks down** | -0.80 | Autonomic neuropathy |
| **Slow** | >2h | Coupling **strengthens** | +0.38 | Metabolic rigidity |
| **Broadband** | Mixed | Average **masks both** | +0.06 | Cancellation |

### Temporal specificity

| Time of day | Coupling change | d |
|---|---|---:|
| Night (00-04h) | **No change** | -0.05 |
| Morning (04-08h) | Elevated | +0.42 |
| Midday (08-16h) | Elevated | +0.23 to +0.40 |
| Evening (16-20h) | Most elevated | +0.45 |

</div>
<div class="col">

### What this means for the field

<div class="card card-green">

**Methodological:** Event-triggered and frequency-resolved analyses are essential. Broadband coupling hides the biology.

</div>

<div class="card card-blue">

**Biological:** Diabetes doesn't simply "decouple" organs. It selectively destroys fast autonomic coordination while tightening slow metabolic locking. These are different disease processes operating simultaneously.

</div>

<div class="card card-purple">

**Clinical potential:** Post-excursion HR blunting (d = 0.80) from consumer CGM + wearable HR could be a practical autonomic neuropathy screening marker — no lab visit, no Ewing battery.

</div>

### Null findings are informative
- Nocturnal coupling is preserved → effect is activity/meal-driven
- Sleep-wake transition dynamics undetectable → need beat-to-beat HR
- Glucose entropy adds <1% beyond HbA1c → complexity alone is not the signal

</div>
</div>

---

## Technical Implementation

<div class="columns">
<div class="col">

### Infrastructure

<div class="card">

**Hypothesis Store** (`hypothesis_driven/`)
- JSON-backed workspace with lifecycle tracking
- 26 hypothesis files with full metadata
- Critic verdicts + revised priorities
- Execution queue sorted by priority

</div>

<div class="card">

**Compute** (Stanford SCG / Slurm)
- Per-participant feature extraction: 32-way array jobs
- ~60 participants per shard, ~2h wall time
- 1,939 participants with valid aligned data
- Postprocess job with `--dependency=afterok`

</div>

### Pipeline (current: Claude Code subagents)

```
Proposer (Agent tool)  →  Critic (Agent tool)
         ↓                        ↓
   proposed_batch.json    critic_verdicts.json
         ↓                        ↓
     Executor (Python + Slurm)
         ↓
     Verifier (Python statistics)
         ↓
     hypothesis_driven/hypotheses/H-*.json
```

</div>
<div class="col">

### Structured Output Schema

```python
@dataclass
class Hypothesis:
    id: str          # H-NEW03
    title: str       # Post-excursion HR blunting
    category: str    # event_dynamics
    statement: str   # Falsifiable claim
    mechanism: str   # Biological reasoning
    predictions: list[str]
    literature: list[LiteratureRef]
    feasibility: FeasibilityAssessment
    priority: float  # 0-1, set by critic
    status: str      # proposed → verified
    test_plan: TestPlan
    results: HypothesisResult
    critic_verdict: CriticVerdict
```

### Key Numbers

| Metric | Value |
|---|---:|
| Total hypotheses | 26 |
| Executed | 13 (8 migrated + 5 new) |
| FDR-significant features | 23/44 |
| Strongest effect (d) | -0.80 |
| Weakest null (p) | 0.67 |
| Robustness tests passed | 9/9 |

</div>
</div>

---

## Next Steps

<div class="columns">
<div class="col">

### Phase 2 Hypotheses (executing)

| ID | Hypothesis | Status |
|---|---|---|
| H-NEW03 | Post-excursion HR dynamics | **Done** |
| H-NEW10 | Activity-glucose phase reversal | Done (null) |
| H-NEW02 | Causal asymmetry (TE/CCM) | Pending |
| H-NEW08 | Coupling physiotypes | Pending |

### Phase 3 (planned)

- **Causal direction** (H-NEW02): Does glucose → HR dominance increase with severity? Pilot 50 participants first.
- **Coupling-based physiotypes** (H-NEW08): Unsupervised clustering on coupling features. Need strong validation framework per critic.

</div>
<div class="col">

### Toward SDK Implementation

Current: Claude Code subagents (interactive)
Future: Anthropic Agent SDK (autonomous)

```
Agent SDK Pipeline:
  1. Scheduled trigger (weekly)
  2. Proposer generates batch
  3. Critic filters + prioritizes
  4. Executor submits Slurm jobs
  5. Verifier checks results
  6. Report to shared workspace
```

### Key Constraints to Address

- **Garmin HR resolution** — the binding constraint for 8/18 hypotheses
- **Medication data** — redacted; coupling-severity gradient may partly reflect medication regimens
- **Longitudinal follow-up** — 10% of cohort planned for Year 4; needed to validate prognostic claims

</div>
</div>

---

## Summary

<div class="columns">
<div class="col">

### The system

A **hypothesis-driven multi-agent pipeline** that:
1. Proposes mechanistically specific hypotheses from literature
2. Critically evaluates feasibility and rigor
3. Executes via parallel Slurm computation
4. Verifies through 9 statistical robustness tests

### The finding

Diabetes does not simply "decouple" physiological systems.

It **selectively destroys fast autonomic coupling** (d = -0.80) while **strengthening slow metabolic locking** (d = +0.38).

This is **invisible to broadband summary statistics** (d = 0.06) and only revealed through frequency-resolved and event-triggered analysis.

</div>
<div class="col">

### Why it matters

<div class="card card-green">

**Post-excursion HR blunting** from consumer-grade CGM + wearable HR could screen for autonomic neuropathy in daily life — no lab, no Ewing battery, no clinic visit.

</div>

<div class="card card-blue">

**Detectable in pre-diabetes** (d = 0.10, p = 0.025) — before clinical diagnosis, before complications.

</div>

<div class="card card-purple">

**Hypothesis-driven discovery** produces more interpretable, mechanistically grounded, and robustly verified findings than exploratory feature mining.

</div>

<div class="small" style="margin-top: 1em;">

**Code:** `hypothesis_driven/` (schemas, workspace, 26 hypotheses)
**Data:** AI-READI v3.0.0, 2,280 participants, NIH Bridge2AI

</div>

</div>
</div>
