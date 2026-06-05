# JEPA Systematic Summary

Date: 2026-04-28

This note summarizes the JEPA effort from the initial project framing through the current
implementations, experiments, results, caveats, and next hypotheses.

## 1. Original Scientific Motivation

The starting concern was that earlier work was reducing a synchronized 10-day multimodal
dataset into feature summaries and then asking loosely motivated statistical questions.
That loses the core value of the dataset: dense, aligned temporal physiology.

The dataset is not only "multimodal clinical data." Its unusual asset is synchronized
5-minute-resolution monitoring across roughly 10 days for more than 2,000 participants:

- CGM glucose dynamics
- wearable heart rate, activity, sleep, calories
- personal environment streams, including light, PM2.5, temperature, humidity
- static clinical/lab features
- retinal foundation-model embeddings and ECG foundation-model embeddings
- diabetes severity labels across a clinical spectrum

The high-level scientific reframing was:

> Treat human physiology as a coupled dynamical system. Diabetes and aging may appear not
> only as abnormal organ states, but as degraded coordination between metabolic,
> autonomic, behavioral, circadian, environmental, retinal, cardiac, and clinical systems.

This framing connects to the broader network-physiology notes in
`docs/design/BRAINSTORM_NETWORK_PHYSIOLOGY.md` and the aging-clock plan in
`docs/design/STUDY_DESIGN_AGING_CLOCKS.md`.

## 2. Why JEPA Was Introduced

JEPA was introduced as a representation-learning route for asking whether synchronized
multimodal physiology contains structure beyond simple summary statistics.

The key JEPA question is:

> Can a context representation from available modalities predict the latent state of a held-out
> modality, future window, or static phenotype better when the person-time alignment is real
> than when alignment is deliberately broken?

This makes the negative controls central. The controls are not bookkeeping. They define the
evidence standard:

- `aligned`: true person-time alignment
- `wrong_day`: same participant, shifted target day/time
- `participant_shuffle`: target windows taken from other participants inside split/control constraints
- `shuffle_all` and `shuffle_sequences`: participant-level modality shuffles

If aligned data does not beat these controls, then the model may only be learning marginal
distributions or static shortcuts. If aligned data beats both wrong-day and participant-shuffle
controls, there is evidence for real person-time synchronized structure.

## 3. Implementation Layers

### 3.1 Participant-Level Sequence JEPA

Path: `foundation_jepa/sequence/`

Purpose:

- Build one representation per participant from the full 10-day sequence and static modalities.
- Test whether raw synchronized sequences add age or disease signal beyond static modalities.
- Provide ablation and sanity-check infrastructure before moving to more mechanistic temporal tasks.

Implemented modalities:

- Sequence encoders: CGM, wearable, environment
- Static encoders: clinical table, RETFound retinal embeddings, ECGFounder cardiac embeddings

Encoder choices:

- Retinal and ECG use existing pretrained foundation-model embeddings.
- Clinical is a local tabular MLP projection, not a pretrained clinical foundation encoder.
- CGM, wearable, and environment use PatchTST-style temporal Transformer encoders trained inside this project, not external pretrained time-series encoders.

Default joint loss:

```text
loss = 1.0 * JEPA_MSE + 1.0 * age_MSE_z + 0.2 * severity_CE
```

This means `full_joint` is not a pure self-supervised JEPA result. Pure JEPA runs should be
judged using frozen linear probes.

### 3.2 Window-Level Temporal JEPA

Path: `foundation_jepa/window/`

Purpose:

- Stop asking only whether a full participant embedding predicts age/severity.
- Ask whether local temporal context predicts future multimodal physiology.
- Test physiological timescales and event-specific coupling.

Default window setup:

- Context length: 24 steps = 2 hours at 5-minute resolution
- Target length: 12 steps = 1 hour
- Common horizon: 6 steps = 30 minutes
- Sequence modalities: CGM, wearable, environment
- Target modalities: CGM, wearable, environment

Objective:

```text
context = temporal modalities over an observed window
target = held-out target modality over a future/offset window

loss = normalized_latent_MSE + contrastive_weight * in_batch_InfoNCE
     + static_align_weight * static_to_dynamic_alignment
```

Current defaults:

```text
contrastive_weight = 1.0
temperature = 0.1
static_align_weight = 0.0
teacher_tau = 0.99
```

The target encoder is an EMA teacher. The contrastive term was added because a first MSE-only
bounded pilot allowed participant-shuffled targets to score too well. With in-batch target
discrimination, the representation must identify the matching target latent, not just regress
to a generic target distribution.

### 3.3 Event-Enriched Window JEPA

Path: `foundation_jepa/window/`

Event modes:

- `random`
- `glucose_rise`
- `activity_bout`
- `sleep_transition`
- `dawn_proxy`
- `mixed_events`

These samplers were added because random windows validate temporal alignment, but they dilute
acute physiology. The event-centered idea is to focus the representation on windows where
cross-system coupling should be strongest.

Important caveat:

- `dawn_proxy` is not true local-clock dawn. The current cached tensors do not retain absolute
  start timestamps, so this is a daily-position proxy.

## 4. Experiment Timeline and Results

### 4.1 Participant-Level Next-Stage Ablation

Artifact:

- `foundation_jepa/sequence/artifacts/next_stage/summary.csv`
- Interpretation: `foundation_jepa/sequence/artifacts/next_stage/INTERPRETATION.md`

Seed-averaged headline test metrics:

| config | age MAE | age R2 | age corr | severity acc | frozen-probe age MAE | frozen-probe severity acc |
|---|---:|---:|---:|---:|---:|---:|
| `full_joint` | 5.272 | 0.636 | 0.804 | 0.659 | 5.354 | 0.646 |
| `static_only_joint` | 5.304 | 0.628 | 0.798 | 0.647 | 5.373 | 0.642 |
| `shuffle_sequences_joint` | 5.427 | 0.613 | 0.794 | 0.651 | 5.468 | 0.650 |
| `drop_clinical_joint` | 6.378 | 0.470 | 0.704 | 0.395 | 6.452 | 0.380 |
| `drop_imaging_joint` | 6.099 | 0.524 | 0.742 | 0.679 | 6.300 | 0.675 |
| `sequence_only_joint` | 9.215 | -0.051 | 0.355 | 0.402 | 9.081 | 0.414 |
| `full_pure_jepa` | 10.880 | -0.406 | 0.054 | 0.242 | 6.287 | 0.553 |
| `sequence_only_pure_jepa` | 9.835 | -0.084 | -0.045 | 0.255 | 8.892 | 0.394 |
| `shuffle_all_joint` | 11.188 | -0.486 | 0.025 | 0.241 | 11.150 | 0.247 |

Interpretation:

- The participant-level scaffold works technically: aligned data strongly beats fully shuffled controls.
- Static modalities dominate chronological age and coarse disease prediction.
- `static_only_joint` is essentially tied with `full_joint`.
- Shuffling only sequence modalities costs little for the age endpoint.
- Sequence-only signal exists, but it is too weak to compete with static clinical/imaging features for age/severity.
- Pure full JEPA has useful frozen-probe age signal, but much of it likely comes from static modalities.

Project decision from this result:

> Chronological age and coarse diabetes severity are not the right primary objectives for discovering the temporal physiology in this dataset. Move to window-level and event-level JEPA.

### 4.2 Aging-Clock Residual Analysis

Artifact:

- `foundation_jepa/sequence/artifacts/aging_residuals/INTERPRETATION.md`

Method:

```text
age_residual = predicted_age - E[predicted_age | chronological_age]
```

Positive residual means the clock predicts older-than-expected age after train-split age calibration.

Test-set severity association:

| config | residual per severity class | severity residual corr | severity residual R2 |
|---|---:|---:|---:|
| `full_joint` | 0.137 | 0.023 | 0.001 |
| `static_only_joint` | -0.046 | -0.007 | 0.000 |
| `full_pure_jepa` | 0.463 | 0.079 | 0.006 |
| `drop_imaging_joint` | 0.520 | 0.076 | 0.007 |
| `sequence_only_pure_jepa` | 0.360 | 0.043 | 0.003 |

Interpretation:

- There is weak positive age-acceleration signal in some pure/drop-imaging settings.
- The association is small and not yet strong biological evidence.
- This needs covariate adjustment, bootstrapping, and comparison to clinical frailty/allostatic-load baselines before being treated as an aging-clock result.

### 4.3 Window-Level Horizon Suite

Artifact:

- `foundation_jepa/window/artifacts/horizon_suite/summary.csv`

Design:

- Horizons: 0, 30, 60, 120 minutes
- Controls: aligned, wrong-day, participant-shuffle
- Seeds: 42, 43, 44
- 36 GPU runs

Mean test JEPA loss across seeds:

| horizon | aligned | wrong-day | participant-shuffle |
|---:|---:|---:|---:|
| 0 min | 3.196 | 4.076 | 4.436 |
| 30 min | 3.458 | 4.102 | 4.429 |
| 60 min | 3.639 | 4.153 | 4.430 |
| 120 min | 3.840 | 4.204 | 4.434 |

Interpretation:

- Aligned windows are consistently easier to predict than wrong-day and participant-shuffled controls.
- Wrong-day is consistently easier than participant-shuffle, which suggests person-specific physiology remains useful even when temporal alignment is weakened.
- The aligned advantage decays as horizon increases, which is physiologically plausible.
- This is the strongest current evidence that the raw synchronized time series contain real temporal structure beyond marginal distributions.

### 4.4 Window-Level Physiology Probes

Artifact:

- `foundation_jepa/window/artifacts/probe_runs/horizon_030min_seed_42_aligned/`
- Interpretation: `foundation_jepa/window/artifacts/probe_runs/horizon_030min_seed_42_aligned/INTERPRETATION.md`

Design:

- Train the 30-minute horizon aligned window JEPA model.
- Freeze the 128-dimensional context embedding.
- Fit ridge probes on train windows and evaluate on held-out test participants.
- Compare JEPA embedding against an 18-feature simple context-window summary.

Run summary:

- Windows: 380,193
- Train/val/test windows: 262,972 / 58,000 / 59,221
- Test JEPA loss: 3.457

Selected test-set probe R2:

| target label | JEPA embedding | context summary | delta |
|---|---:|---:|---:|
| future CGM mean | 0.697 | 0.663 | +0.034 |
| future HR mean | 0.683 | 0.662 | +0.021 |
| future asleep mean | 0.546 | 0.412 | +0.133 |
| future steps mean | 0.460 | 0.420 | +0.040 |
| future calories mean | 0.644 | 0.597 | +0.047 |
| future light total | 0.709 | 0.565 | +0.144 |
| future CGM delta | 0.049 | 0.037 | +0.012 |
| future CGM rise event AUC | 0.640 | 0.609 | +0.031 |
| future PM2.5 mean | 0.289 | 0.375 | -0.085 |
| future humidity mean | 0.923 | 0.946 | -0.023 |

Interpretation:

- The learned embedding is not merely reproducing simple context means and standard deviations.
- It improves prediction of future state/phase variables, especially sleep/activity/light, and modestly improves future CGM and HR.
- Acute deltas are harder, which motivated event-enriched sampling.
- Environment autocorrelation targets such as humidity and PM2.5 should not be over-interpreted as learned physiology because simple summaries are already very strong.

### 4.5 Mixed-Events Window JEPA

Artifact:

- `foundation_jepa/window/artifacts/event_probe_runs/mixed_events_horizon_030min_seed_42_aligned/summary.json`
- Robust probes: `foundation_jepa/window/artifacts/event_probe_runs/mixed_events_horizon_030min_seed_42_aligned/robust_probes/`

Design:

- Event mode: `mixed_events`
- Horizon: 30 minutes
- Seed: 42
- Control: aligned
- Event fallback random: false

Run summary:

- Windows: 383,440
- Train/val/test windows: 265,188 / 58,451 / 59,801
- Test JEPA loss: 3.529

Event counts:

| event type | windows |
|---|---:|
| `activity_bout` | 90,954 |
| `dawn_proxy` | 89,788 |
| `glucose_rise` | 91,247 |
| `sleep_transition` | 111,451 |

Robust probe results, JEPA embedding vs clipped context summary:

| target label | JEPA embedding | context summary | delta |
|---|---:|---:|---:|
| future CGM mean R2 | 0.699 | 0.651 | +0.048 |
| future CGM delta R2 | 0.071 | 0.045 | +0.027 |
| future CGM rise AUC | 0.691 | 0.659 | +0.033 |
| future HR mean R2 | 0.692 | 0.669 | +0.023 |
| future asleep mean R2 | 0.528 | 0.364 | +0.163 |
| future steps mean R2 | 0.467 | 0.433 | +0.034 |
| future calories mean R2 | 0.639 | 0.594 | +0.045 |
| future light total R2 | 0.670 | 0.532 | +0.139 |
| future PM2.5 mean R2 | 0.192 | 0.208 | -0.016 |
| future humidity mean R2 | 0.919 | 0.942 | -0.023 |

Interpretation:

- Event sampling improves acute CGM-response probes compared with generic random windows.
- The JEPA embedding remains stronger than simple context summaries for most physiology/behavior targets.
- The environment targets remain mixed and likely partly dominated by autocorrelation.
- The first probe baseline had numerical instability in simple context summaries; the robust rerun clipped standardized features to +/-10 and should be treated as the clean comparison.

### 4.6 Mixed-Events Control Suite

Artifact:

- `foundation_jepa/window/artifacts/event_control_suite/summary.csv`

Design:

- Event mode: `mixed_events`
- Horizon: 30 minutes
- Controls: aligned, wrong-day, participant-shuffle
- Seeds: 42, 43, 44
- 9 GPU runs

Mean test JEPA loss across seeds:

| control | mean test JEPA |
|---|---:|
| aligned | 3.539 |
| wrong-day | 4.149 |
| participant-shuffle | 4.441 |

Paired gaps:

| contrast | gap |
|---|---:|
| wrong-day - aligned | +0.610 |
| participant-shuffle - aligned | +0.902 |

Interpretation:

- Event-centered aligned windows beat both controls across seeds.
- This argues that event JEPA is not just learning event marginal distributions.
- It supports the premise that physiological event windows concentrate real cross-modal temporal coupling.

### 4.7 Event-Type Control Suite

Artifact:

- `foundation_jepa/window/artifacts/event_type_control_suite/summary.csv`

Design:

- Event modes: `glucose_rise`, `activity_bout`, `dawn_proxy`, `sleep_transition`
- Horizon: 30 minutes
- Controls: aligned, wrong-day, participant-shuffle
- Seeds: 42, 43, 44
- 36 GPU runs

Mean test JEPA loss across seeds:

| event type | aligned | wrong-day | participant-shuffle | wrong-day gap | shuffle gap |
|---|---:|---:|---:|---:|---:|
| `glucose_rise` | 3.504 | 4.154 | 4.439 | +0.650 | +0.936 |
| `activity_bout` | 3.576 | 4.157 | 4.444 | +0.581 | +0.868 |
| `dawn_proxy` | 3.581 | 4.239 | 4.448 | +0.658 | +0.867 |
| `sleep_transition` | 3.595 | 4.188 | 4.448 | +0.593 | +0.853 |

Interpretation:

- All event classes validate with aligned < wrong-day < participant-shuffle.
- `glucose_rise` is the strongest/easiest aligned event and has the largest participant-shuffle gap.
- `dawn_proxy` has the largest wrong-day gap, but must be interpreted cautiously because it is not true local clock dawn.
- `sleep_transition` is harder but still validated.

## 5. Current Scientific Interpretation

The strongest current JEPA result is not age prediction. It is temporal-alignment validation.

The result pattern:

```text
aligned loss < wrong-day loss < participant-shuffle loss
```

is repeated across random windows, event windows, horizons, and event types. That is exactly
the expected pattern if the data contain real person-specific and time-specific synchronized
physiology.

The participant-level result also matters, but mostly as a warning:

- Static clinical/retinal/ECG features are powerful shortcuts for age and disease labels.
- If the project is framed only around predicting age or severity, the model can ignore most of the 10-day temporal structure.
- Therefore, the temporal JEPA work should focus first on predicting future/counterfactual physiology, event response, coupling loss, and disease-stratified synchronization rather than only age/severity endpoints.

## 6. Current Hypotheses

### Hypothesis 1: AIREADI contains real synchronized temporal physiology

Status: supported.

Evidence:

- Aligned windows beat wrong-day and participant-shuffle controls across the horizon suite.
- The same control ordering holds in mixed-event and event-type suites.

### Hypothesis 2: Cross-modal predictability decays with horizon

Status: supported.

Evidence:

- Aligned test JEPA rises from 3.196 at 0 minutes to 3.840 at 120 minutes.
- The aligned advantage remains but weakens with longer prediction horizons.

### Hypothesis 3: Event windows concentrate physiologically meaningful coupling

Status: supported but still preliminary.

Evidence:

- Event-enriched probes improve acute CGM-related targets.
- Mixed-event aligned loss is far below controls.
- Each event class validates independently.

### Hypothesis 4: Glucose-rise windows are especially informative

Status: supported.

Evidence:

- `glucose_rise` has the best aligned event-type loss and the largest participant-shuffle gap.
- Robust probes show improved CGM delta and CGM rise classification from JEPA embeddings.

### Hypothesis 5: Static phenotype dominates coarse age/disease prediction

Status: strongly supported.

Evidence:

- `static_only_joint` is essentially tied with `full_joint`.
- Shuffling sequence modalities barely changes participant-level age/severity performance.
- Dropping clinical or imaging changes performance much more.

### Hypothesis 6: JEPA-derived biological age acceleration relates to diabetes severity

Status: weak and not yet established.

Evidence:

- Some residual analyses show positive severity trends, especially `full_pure_jepa` and `drop_imaging_joint`.
- Effect sizes are small, with severity residual R2 around 0.006 in the more favorable settings.

Required next evidence:

- Covariate-adjusted severity models
- Participant-level bootstrap intervals
- Comparison to frailty, allostatic load, HbA1c, BMI, medication status if available
- Disease-stratified temporal coupling metrics

## 7. What the Current JEPA Is Not Yet

The current implementation is not yet a final foundation model.

Important limitations:

- Sequence encoders are trained from scratch on about 2,280 participants. This is too small for high-capacity modality-specific foundation encoders.
- Only retinal and ECG branches currently use true pretrained foundation embeddings.
- Clinical encoding is a local MLP projection, not a pretrained clinical encoder.
- Generic time-series pretrained encoders have not yet been integrated or validated for CGM/Garmin/environment streams.
- Static-to-dynamic alignment exists in the window model but has default weight 0.0 in the validated temporal runs.
- `dawn_proxy` lacks true absolute time.
- Event thresholds are heuristic and need sensitivity analysis.
- The JEPA loss scale is a representation-learning objective, not a direct biological effect size.
- Probe metrics need participant-level bootstrap and disease-stratified inference.
- Current results show predictability and alignment, not causal mechanisms.

## 8. Ideal Implementation Direction

An ideal next-generation system would separate modality encoding, temporal JEPA, static alignment,
and biological hypothesis testing.

### 8.1 Modality Encoders

Use pretrained or externally validated encoders where possible:

- Retinal: RETFound or stronger retinal foundation embeddings
- ECG: ECGFounder or validated ECG-age/foundation embeddings
- Clinical/labs: regularized tabular encoder, possibly self-supervised EHR/lab embedding if available, but with strict leakage control
- CGM: time-series encoder pretrained or self-supervised on larger CGM collections if available; otherwise keep small PatchTST-style encoders with strong controls
- Wearable: pretrained wearable/sleep/activity encoder if available; otherwise local temporal encoder
- Environment: likely local encoder, with careful handling of autocorrelation and location/time confounding

Given the sample size, high-capacity encoders should generally be frozen or adapter-tuned, not trained from scratch end to end.

### 8.2 Static-Dynamic Alignment

Static information should be aligned with temporal physiology without becoming a shortcut:

- Learn a temporal state embedding from CGM/wearable/environment windows.
- Learn static embeddings from clinical/retina/ECG.
- Add a static-to-dynamic prediction or contrastive alignment objective.
- Evaluate whether static phenotypes predict temporal coupling loss or event response.
- Keep age/severity heads secondary so they do not dominate the temporal objective.

### 8.3 Event Curriculum

Train and evaluate on a physiological curriculum:

1. Random windows for alignment validation.
2. Glucose-rise windows for metabolic/autonomic response.
3. Activity-bout windows for exercise/recovery physiology.
4. Sleep-transition and overnight windows for circadian/autonomic coupling.
5. True dawn windows after absolute timestamps are added.
6. Disease-stratified event coupling and residual aging analyses.

## 9. Recommended Next Experiments

1. Disease-stratified event JEPA/probes

   Test whether aligned-control gaps, probe R2, and event-response embeddings vary monotonically
   across diabetes severity. This is the most direct bridge from JEPA validation to a diabetes
   physiology paper.

2. Event-specific robust probe suite

   Rerun robust probes separately for `glucose_rise`, `activity_bout`, `sleep_transition`, and
   `dawn_proxy`, not only mixed events. Report CGM, HR, sleep/activity, and environment targets
   by event type.

3. Horizon x event grid

   Start with `glucose_rise` and `sleep_transition` across 0, 30, 60, 120 minutes. This tests
   mechanism-specific lag structure without exploding the run matrix.

4. True clock-time cache

   Extend the 10-day cache to retain absolute/local timestamps. Replace `dawn_proxy` with true
   early-morning, nocturnal, and post-wake windows.

5. Participant-level statistical inference

   Bootstrap by participant, not by window. Report confidence intervals for aligned-control gaps,
   probe deltas, and disease-stratified trends.

6. Static alignment run

   Enable small static alignment weights after temporal validation:

   ```text
   static_align_weight = 0.05 or 0.1
   ```

   Evaluate whether clinical/retina/ECG embeddings predict dynamic coupling without collapsing
   the model into static shortcuts.

7. Aging-clock integration

   Treat age as one biological probe, not the main JEPA target. Build:

   - chronological age head from temporal JEPA embeddings
   - residual age acceleration after age calibration
   - association of residuals with disease severity and coupling loss
   - comparison against frailty/allostatic-load/clinical aging baselines

8. Pretrained encoder integration

   Replace or augment local MLP/static branches with externally pretrained embeddings where possible,
   especially retinal and ECG. Consider frozen adapters before end-to-end fine tuning.

## 10. Bottom Line

The JEPA effort has already produced a useful scientific redirect.

The participant-level work showed that age and severity endpoints are dominated by static clinical,
retinal, and ECG information. That is important, but it is not the central opportunity.

The window-level and event-level work shows repeated, control-validated evidence that synchronized
10-day CGM, wearable, and environment streams contain real temporal structure. The strongest current
claim is:

> AI-READI contains person-specific, time-specific multimodal physiological coupling that is
> measurable by JEPA and is strongest in aligned event windows.

The next scientific step is to turn that representation evidence into disease biology:

> Does diabetes severity degrade cross-system temporal coupling, alter event-response lag structure,
> or produce biological-age residuals beyond static clinical phenotype?
