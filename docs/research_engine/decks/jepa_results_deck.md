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
  .columns { display: flex; gap: 1.4em; }
  .col { flex: 1; }
  .small { font-size: 14px; color: #4a5568; }
  .tiny { font-size: 12px; color: #718096; }
  .callout { border-left: 5px solid #3182ce; padding: 0.6em 0.9em; background: #ebf8ff; }
  .warn { border-left: 5px solid #d69e2e; padding: 0.6em 0.9em; background: #fffff0; }
  .metric { font-size: 30px; font-weight: 700; color: #2c5282; }
  .good { color: #2f855a; font-weight: 700; }
  .caution { color: #975a16; font-weight: 700; }
---

# JEPA for Synchronized Multimodal Physiology

**AI-READI 10-day CGM + wearable + environment**

Zijian Ma | Stanford TWC Lab

<div class="small">

Draft results deck, 2026-04-28

</div>

---

## The Framing

AI-READI is not just a feature table. It is a 10-day observation of coupled physiology.

<div class="columns">
<div class="col">

**Continuous temporal streams**

- CGM glucose, 5 min
- wearable HR/activity/sleep/calories
- environment light/PM2.5/temp/humidity
- about 10 days per participant

</div>
<div class="col">

**Static deep phenotype**

- clinical labs and vitals
- retinal foundation embeddings
- ECG foundation embeddings
- diabetes severity spectrum

</div>
</div>

<div class="callout">

Scientific question: can synchronized person-time context predict future physiology better than broken alignment?

</div>

---

## What SOTA Papers Teach Us To Show

| publication pattern | examples | implication for our slides |
|---|---|---|
| pipeline schematic first | I-JEPA, RETFound, SleepFM, GluFormer | show context, target, controls, event windows early |
| downstream transfer and baselines | RETFound, GluFormer, SleepFM | show JEPA embedding vs simple summaries and static-only |
| control/generalization logic | SleepFM temporal/external tests; RETFound external eval | emphasize held-out participants and broken-alignment controls |
| bootstrap/CI, not only point metrics | SleepFM, RETFound | future figures need participant-level bootstrap |
| label efficiency/scaling | RETFound, SleepFM | add future slide: limited labels, pretrained encoders, static alignment |

<div class="tiny">

Source review: `docs/reports/JEPA_RESULTS_SLIDE_SOURCE_REVIEW_20260428.md`

</div>

---

## JEPA System

```text
context window: CGM + wearable + environment
       |
       v
temporal encoder -> context latent
       |
       v
predict target latent for future/offset modality window
```

Controls define the evidence:

| control | interpretation |
|---|---|
| `aligned` | true person-time context and target |
| `wrong_day` | same participant, shifted target |
| `participant_shuffle` | target from another participant |

<div class="callout">

Primary validation criterion: `aligned loss < wrong_day loss < participant_shuffle loss`.

</div>

---

## Result 1: Participant-Level JEPA Finds a Static Shortcut

![width:980px](figures/jepa_results/sequence_ablation.png)

<div class="warn">

Conclusion: `static_only_joint` is essentially tied with `full_joint`; sequence-only models are weaker on coarse age/severity endpoints.

</div>

---

## Result 2: Horizon Suite Validates Temporal Alignment

Mean held-out test JEPA loss across three seeds.

![width:900px](figures/jepa_results/horizon_suite.png)

<div class="callout">

Aligned windows are consistently easier to predict. At 30 minutes, aligned loss is 3.458 versus 4.102 wrong-day and 4.429 participant-shuffle.

</div>

---

## Result 3: The Embedding Predicts Future Physiology

Frozen ridge probes compare JEPA context embeddings against 18 simple context-summary features.

![width:940px](figures/jepa_results/probe_gains.png)

<div class="small">

Event sampling improves CGM delta and CGM rise probes; sleep/activity/light state show the largest embedding gains.

</div>

---

## Result 4: Event Windows Strengthen Acute Physiology Probes

Mixed-event 30-minute aligned run:

- 383,440 sampled windows
- event counts: glucose rise 91,247; activity bout 90,954; sleep transition 111,451; dawn proxy 89,788
- robust probes use standardized context-feature clipping

| future target | JEPA | context summary | gain |
|---|---:|---:|---:|
| CGM mean R2 | 0.699 | 0.651 | +0.048 |
| CGM delta R2 | 0.071 | 0.045 | +0.027 |
| CGM rise AUC | 0.691 | 0.659 | +0.033 |
| HR mean R2 | 0.692 | 0.669 | +0.023 |
| asleep mean R2 | 0.528 | 0.364 | +0.163 |
| calories mean R2 | 0.639 | 0.594 | +0.045 |
| light total R2 | 0.670 | 0.532 | +0.139 |

<div class="callout">

Event sampling improves acute CGM-response probes relative to generic windows.

</div>

---

## Result 5: Event-Type Controls Validate Multiple Physiological Windows

Mean test JEPA loss across three seeds.

![width:900px](figures/jepa_results/event_type_heatmap.png)

<div class="callout">

Every event type preserves the aligned < wrong-day < participant-shuffle ordering. Glucose-rise windows show the largest participant-shuffle gap.

</div>

<div class="tiny">

Note: `dawn_proxy` is daily-position proxy, not true local-clock dawn.

</div>

---

## Result 6: Aging Residual Is Not Yet the Main Claim

Age residual:

```text
predicted_age - E[predicted_age | chronological_age]
```

Test-set association with severity:

| config | residual per severity class | severity residual R2 |
|---|---:|---:|
| `full_joint` | +0.137 | 0.001 |
| `static_only_joint` | -0.046 | 0.000 |
| `full_pure_jepa` | +0.463 | 0.006 |
| `drop_imaging_joint` | +0.520 | 0.007 |

<div class="warn">

Current age-acceleration signal is weak. It should be treated as a secondary biological probe after disease-stratified temporal coupling is validated.

</div>

---

## Current Evidence Ladder

| layer | status | evidence |
|---|---|---|
| data/model scaffold | complete | sequence and window JEPA subtrees |
| participant-level ablations | complete | static shortcut identified |
| horizon controls | complete | aligned beats wrong-day and shuffle |
| mixed-event controls | complete | same ordering across seeds |
| event-type controls | complete | glucose/activity/sleep/dawn proxy validated |
| robust physiology probes | partial | mixed-event and 30-min random done |
| participant bootstrap | pending | needed for publication-grade uncertainty |
| disease stratification | pending | needed for diabetes biology claim |
| pretrained/static alignment | pending | needed for foundation-model claim |

---

## What To Generate Next For Publication-Grade Figures

1. Horizon line plot with seed points and participant bootstrap CI.
2. Event-type/control heatmap with aligned-control gaps.
3. Probe delta waterfall: JEPA minus context summary.
4. Severity-stratified event gaps: healthy to insulin-dependent.
5. Static shortcut ablation plot: full, static-only, sequence-only, shuffle.
6. Aging residual plot with covariate adjustment and bootstrap CI.
7. Label-efficiency plot: labeled participant fraction versus probe/severity metric.
8. Pretrained/static alignment ablation: temporal JEPA versus JEPA plus static alignment.

---

## Proposed Figure Story For A Paper

| figure | claim |
|---|---|
| Fig. 1 | AI-READI enables synchronized multimodal physiological JEPA |
| Fig. 2 | Person-time alignment contains predictive temporal information |
| Fig. 3 | JEPA embeddings encode future glucose, autonomic, sleep, activity, and light state |
| Fig. 4 | Event-centered windows reveal stronger acute physiological coupling |
| Fig. 5 | Diabetes severity alters coupling strength and event-response lag structure |
| Fig. 6 | Static clinical/retinal/ECG phenotype aligns with dynamic coupling and biological age residuals |

<div class="small">

Figs. 1-4 are mostly supported by current results. Figs. 5-6 require the next validation stage.

</div>

---

## One-Slide Takeaway

<div class="metric">

Aligned temporal physiology is real.

</div>

Across horizons and event types, true person-time aligned windows are easier to predict than wrong-day or participant-shuffled controls.

<div class="columns">
<div class="col">

**Supported now**

- temporal alignment signal
- event-window signal
- useful future physiology probes
- static shortcut in age/severity

</div>
<div class="col">

**Not yet proven**

- disease mechanism
- severity gradient in coupling loss
- strong JEPA aging clock residual
- final pretrained foundation-model system

</div>
</div>

---

## References Used For Slide Design

- I-JEPA: https://arxiv.org/abs/2301.08243
- V-JEPA 2: https://arxiv.org/abs/2506.09985
- GluFormer: https://www.nature.com/articles/s41586-025-09925-9
- SleepFM: https://www.nature.com/articles/s41591-025-04133-4
- RETFound: https://www.nature.com/articles/s41586-023-06555-x
- Insulin resistance from wearables and biomarkers: https://www.nature.com/articles/s41586-026-10179-2
- Network Physiology: https://www.nature.com/articles/ncomms1705
