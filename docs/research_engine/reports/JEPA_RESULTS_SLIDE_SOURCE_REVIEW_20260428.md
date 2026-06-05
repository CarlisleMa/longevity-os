# JEPA Results Slides: Source Review and Evaluation Plan

Date: 2026-04-28

Purpose: identify the figure grammar used by state-of-the-art foundation model,
physiological time-series, and biomedical representation papers, then translate that into
slides for the AI-READI JEPA results.

## 1. Source Publications Reviewed

| paper | why it matters for this deck | useful figure/evaluation pattern |
|---|---|---|
| [I-JEPA, ICCV 2023](https://arxiv.org/abs/2301.08243) | Canonical JEPA framing: predict target embeddings from context, not pixels. | Show context/target masking, latent prediction, EMA/stop-gradient target, then downstream representation probes. |
| [V-JEPA 2, arXiv 2025](https://arxiv.org/abs/2506.09985) | Strongest recent JEPA-style world-model narrative: understanding, prediction, planning. | Organize around capabilities: motion understanding, anticipation, VQA, planning. For us: temporal alignment, future physiology, event response, static alignment. |
| [GluFormer, Nature 2026](https://www.nature.com/articles/s41586-025-09925-9) | Closest CGM foundation-model comparator. | Fig. 1 architecture/training/downstream tasks; Fig. 2 CGM simulation/analysis; Fig. 3 risk stratification versus HbA1c; Fig. 4 representations versus CGM scores/GMI; Fig. 5 multimodal dietary extension. |
| [SleepFM, Nature Medicine 2026](https://www.nature.com/articles/s41591-025-04133-4) | Closest multimodal physiological foundation-model comparator. | Framework figure with dataset scale, contrastive pretraining, fine-tuning tasks, confusion matrices; disease-category dot plots with C-index/AUROC; patient-level bootstrap violins; fine-tuning/pretraining scaling curves. |
| [RETFound, Nature 2023](https://www.nature.com/articles/s41586-023-06555-x) | Strong biomedical foundation-model template already relevant to AI-READI retinal embeddings. | Pipeline schematic; internal/external evaluation; systemic disease prediction; label efficiency curves; SSL strategy ablation; saliency/interpretation panels. |
| [Insulin resistance from wearables and blood biomarkers, Nature 2026](https://www.nature.com/articles/s41586-026-10179-2) | Best recent wearable plus routine-biomarker metabolic prediction paper. | Feature-group ablations; wearable foundation model embedding versus aggregate wearable features; independent validation cohort; clinically meaningful error regions. |
| [Network Physiology, Nature Communications 2012](https://www.nature.com/articles/ncomms1705) | Scientific foundation for "health is coordination, disease is decoupling." | Network-transition figure, connectivity across physiological states, link-strength stratification, surrogate analysis. |

## 2. What SOTA Papers Put in Their Results Figures

### 2.0 Figure Style Verification

The regenerated figures follow the practical constraints emphasized by top-journal guidance:

- Nature research figure guide: use white backgrounds, labelled axes with units, standard sans-serif fonts, accessible colours, legible text, and avoid grid clutter, decorative effects, coloured text legends, and overlapping text.
- Nature final-artwork guidance: keep line art/text editable where possible; use Helvetica/Arial-style fonts; use lowercase bold panel letters; prefer vector outputs for line art.
- Cell Press/JCB graphical guidance: keep visuals simple, text sparse, and focused on one clear take-home point.

Implementation choices made in `scripts/reporting/build_jepa_results_figures.py`:

- Okabe-Ito-inspired colourblind-safe palette.
- Direct line labels for the horizon plot instead of an overlapping legend.
- Split x-axis labels in the heatmap to prevent collision.
- Legend placed above the probe plot, outside the data region.
- Participant ablation converted from crowded vertical bars to horizontal bars plus a separate severity-accuracy dot panel.
- PNG and vector PDF exports generated for every figure.

### 2.1 Pipeline First

Top papers do not start with a metric table. They first define the measurement system.

Useful pattern for us:

1. Show the 10-day synchronized data cube.
2. Show context windows, target windows, and event windows.
3. Show aligned, wrong-day, and participant-shuffle controls.
4. State the primary scientific claim before the numbers:

   ```text
   Real person-time alignment makes future physiology easier to predict.
   ```

### 2.2 Controls and Generalization Are Central

SOTA biomedical foundation papers usually include:

- internal hold-out test set
- external validation or temporal validation when available
- baseline models and ablations
- multiple seeds or bootstraps
- confidence intervals

For our JEPA work, the analogous evidence hierarchy is:

| SOTA concept | AI-READI JEPA equivalent |
|---|---|
| external validation | held-out participants plus control windows |
| baseline clinical model | simple context summaries and static-only models |
| pretraining benefit | JEPA embedding versus context-summary probes |
| label efficiency | future: performance versus labeled participant fraction |
| model scaling | future: context length, horizon, event curriculum, pretrained encoders |
| disease generalization | future: severity-stratified coupling gaps |

### 2.3 Use Patient-Level Bootstrap for Claims

SleepFM reports patient-level bootstrap distributions for disease outcomes and model comparisons.
This is directly relevant because our windows are not independent. For publication-quality
figures, window-level standard errors would be misleading.

Recommended:

- Resample participants, not windows.
- Recompute aligned-control gaps, probe deltas, and severity trends.
- Report 95% bootstrap intervals.
- Keep seed-to-seed variation visible where possible.

### 2.4 Show Model Versus Simple Baselines

RETFound and GluFormer both emphasize comparison against simpler or established baselines:

- RETFound versus ImageNet and retinal SSL baselines
- GluFormer versus HbA1c, GMI, and CGM-derived scores
- Wearable IR paper versus demographics, blood biomarkers, aggregate wearable features, and WFM embeddings

For us:

- JEPA embedding versus 18-feature context summary
- aligned versus wrong-day versus participant shuffle
- temporal JEPA versus participant-level static shortcut
- future: JEPA versus random/untrained encoder
- future: JEPA versus classical coupling features

### 2.5 Label Efficiency and Small-N Framing

RETFound-style label-efficiency plots are useful because this dataset has only about 2,280
participants but many windows. A strong future slide would show whether JEPA embeddings help
when disease/age labels are scarce:

```text
x-axis: fraction of labeled participants
y-axis: disease/age/coupling-probe metric
curves: static baseline, temporal summary, JEPA embedding, JEPA plus static alignment
```

## 3. Recommended Main Results Figure Set

### Figure 1: Dataset and JEPA System

Goal: make the study legible in one panel.

Panels:

- 10-day synchronized streams: CGM, wearable, environment
- static phenotypes: clinical, retina, ECG
- window sampling: context, horizon, target
- controls: aligned, wrong-day, participant-shuffle
- event samplers: glucose rise, activity bout, sleep transition, dawn proxy

Use this as slide 2 or 3, not buried in methods.

### Figure 2: Core Temporal Alignment Result

Goal: make the strongest current result unmistakable.

Plot:

- x-axis: horizon, 0/30/60/120 min
- y-axis: test JEPA loss
- lines: aligned, wrong-day, participant-shuffle
- add shaded seed variation if available

Message:

```text
Aligned person-time windows are consistently easier to predict.
```

### Figure 3: Event-Type Validation Heatmap

Goal: show physiology is not limited to random windows.

Plot:

- rows: glucose rise, activity bout, dawn proxy, sleep transition
- columns: aligned, wrong-day, participant-shuffle
- color: test JEPA loss
- side bar: aligned-control gap

Message:

```text
Every event type preserves the aligned < wrong-day < participant-shuffle ordering.
```

### Figure 4: Probe Interpretability

Goal: show what the representation contains.

Plot:

- horizontal bars for probe improvement over context summary
- targets: CGM mean, CGM delta, CGM rise AUC, HR mean, asleep mean, steps, calories, light, PM2.5, humidity
- separate random-window and mixed-event panels

Message:

```text
JEPA embeddings improve future physiology probes, especially sleep/activity/light and event CGM response.
```

### Figure 5: Static Shortcut and Participant-Level Ablation

Goal: prevent overclaiming age/severity.

Plot:

- participant-level age MAE or disease accuracy by config
- highlight `full_joint`, `static_only_joint`, `sequence_only_joint`, `shuffle_all_joint`

Message:

```text
Static clinical/retina/ECG phenotype dominates coarse age and severity prediction.
Temporal JEPA should target coupling, event response, and disease-stratified dynamics.
```

### Figure 6: Aging Residual as Secondary Probe

Goal: frame aging clock correctly.

Plot:

- age residual by severity group for selected configs
- show small effect and confidence intervals when bootstrapped

Message:

```text
Current age-acceleration evidence is weak; disease-stratified temporal coupling is the stronger near-term biology.
```

### Figure 7: Next Validation Ladder

Goal: give reviewers confidence that this is becoming science, not just representation learning.

Ladder:

1. Alignment controls complete.
2. Event controls complete.
3. Robust probes partially complete.
4. Participant bootstrap pending.
5. Disease-stratified coupling pending.
6. True dawn timestamp cache pending.
7. Pretrained/static encoder alignment pending.

## 4. Slide Narrative

Recommended 12-slide results sequence:

1. Title: JEPA for synchronized multimodal physiology
2. Motivation: AI-READI is a 10-day coupled dynamical system
3. SOTA framing: what top foundation-model papers evaluate
4. Method: window JEPA with controls
5. Result 1: participant-level ablation reveals static shortcut
6. Result 2: horizon suite validates temporal alignment
7. Result 3: probe suite shows representation content
8. Result 4: mixed-event JEPA improves acute physiology probes
9. Result 5: event-type suite validates glucose/activity/sleep/dawn windows
10. Aging clock: useful but weak current residual evidence
11. What would make this publication-grade
12. Next experiments and figure roadmap

## 5. Evaluation Checklist Before Presentation

Minimum credible deck:

- Show held-out participant splits.
- Show all three controls.
- Show seed averages or seed points.
- Mention that windows are not independent.
- Report that disease/age endpoints are static-dominated.
- Separate "validated alignment" from "biological mechanism."

Publication-grade deck:

- Participant-level bootstrap intervals.
- Disease-severity stratified aligned-control gaps.
- Event-specific robust probes, not only mixed events.
- Random/untrained encoder baseline.
- Classical coupling baseline.
- True clock-time dawn windows.
- Static alignment ablation.
- Label-efficiency curves.
- Pretrained encoder integration or clear rationale for local encoders.

## 6. Practical Design Notes

- Use line charts for horizon decay.
- Use heatmaps for event-type/control matrices.
- Use horizontal delta bars for JEPA-versus-summary probe gains.
- Use a small "claim status" badge on each slide:
  - Supported
  - Preliminary
  - Not yet proven
- Do not present participant-level age MAE as the main win.
- Keep the strongest headline as:

  ```text
  Synchronized person-time alignment carries predictive physiological information.
  ```
