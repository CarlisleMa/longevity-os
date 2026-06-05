---
marp: true
theme: default
paginate: true
size: 16:9
---

# AI-READI Progress Update

Multimodal foundation models + agentic scientific reasoning
---

## One system, four layers

<div class="image-card<img src="assets/story_map.svg)

Alt: Four-stage AI-READI story map<div class="three-cards<div class="plain-card<b>Foundation models perceive**: Encoders turn each modality into a shared biological state.<div class="plain-card<b>Agents experiment**: Specialists compute, critique, and preserve validated workflows.<div class="plain-card<b>The loop learns**: N-of-1 outcomes improve person calibration and future suggestions.

Speaker note: This is the architecture in one slide: Layer 0 data, Layer 1 foundation model perception, Layer 2 agentic science, Layer 3 Longevity OS/N-of-1 translation.
---

## Dataset: breadth plus synchrony

<div class="metric-tiles<div class="metric-tile blue<span>Cohort<b>2,280</b><small>participants</small><div class="metric-tile teal<span>Sites<b>3</b><small>UW, UAB, UCSD</small><div class="metric-tile gold<span>Groups<b>4</b><small>diabetes severity strata</small><div class="metric-tile green<span>Continuous overlap<b>8.8-9.8d</b><small>triple sensor window</small><div class="three-cards<div class="plain-card<b>Snapshot anchors**: labs, ECG, retinal imaging on visit day<div class="plain-card<b>Continuous physiology**: CGM, Garmin, environment collected concurrently<div class="plain-card<b>Result-ready tables**: 2,280 x 126 feature matrix; 2,280 x 49 multimodal matrix

Speaker note: Keep the dataset slide compact. The point is not just nine modalities; the point is that the 10-day sensor window is anchored to clinical and imaging measurements from the same visit.
---

## The 10-day window changes the science

<div class="image-card<img src="assets/ten_day_window.svg)

Alt: 10-day aligned sensor window<div class="three-cards<div class="plain-card<b>Not long-term follow-up**: micro-longitudinal physiology<div class="plain-card<b>Within-person tests**: lags, coupling, mediation<div class="plain-card<b>Trial-readable outcomes**: TIR, sleep, HR, light, activity

Speaker note: Say explicitly: this is not a longitudinal disease-outcome cohort. It is a short, synchronized within-person window that enables causal hypotheses and N-of-1 trial design.
---

## Foundation model layer

<div class="image-card<img src="assets/foundation_model_layer.svg)

Alt: Foundation model integration diagram<div class="three-cards<div class="plain-card<b>Frozen encoders**: RETFound, ECG embeddings, wearable-style tokens<div class="plain-card<b>Cross-modal JEPA**: predict missing modality state in embedding space<div class="plain-card<b>Agent substrate**: computed latent state, not LLM memory

Speaker note: Foundation models provide perception: retinal/cardiac embeddings, future wearable/CGM/environment encoders, and cross-modal reconstruction. Agents reason over these computed representations.
---

## Agent system layer

<div class="image-card<img src="assets/agent_workspace_visual.png)

Alt: Layer 2 multi-agent scientific reasoning schematic

Speaker note: The generated image is a visual metaphor. The scientific implementation is concrete: agents are scoped code-generating analysts over scripts, a shared workspace, memory, and critic checks.
---

## What each agent group makes computable

<div class="image-card<img src="assets/agent_tasks.svg)

Alt: Agent task map<div class="three-cards<div class="plain-card<b>Clinical + glucose**: dynamic metabolism beyond HbA1c<div class="plain-card<b>Wearable + environment**: modifiable daily physiology<div class="plain-card<b>Cardiac + retinal**: organ aging discordance

Speaker note: This replaces the long per-agent text slides. In narration, expand each group: ClinicalAgent handles OMOP and disease gradients; GlucoseAgent handles CGM metrics; Wearable and Environment agents make the 10-day inference layer; Cardiac and Retinal agents provide high-value organ readouts; reasoning agents test and critique.
---

## Latest results, regenerated from current artifacts

<table class="result-table<thead><tr><th>Newest result artifact</th><th>Modified</th><th>Size</th></tr></thead><tbody><tr><td>fig6_radar.png</td><td>2026-04-30 14:43</td><td>754.4 KB</td></tr><tr><td>study_summary.json</td><td>2026-04-30 14:43</td><td>6.5 KB</td></tr><tr><td>fig5_unified.png</td><td>2026-04-30 14:43</td><td>337.0 KB</td></tr><tr><td>fig4_gradient.png</td><td>2026-04-30 14:43</td><td>145.4 KB</td></tr><tr><td>fig3_subtypes.png</td><td>2026-04-30 14:43</td><td>1181.8 KB</td></tr><tr><td>fig2_concordance.png</td><td>2026-04-30 14:43</td><td>828.9 KB</td></tr><tr><td>table1_enhanced.csv</td><td>2026-04-30 14:43</td><td>3.0 KB</td></tr><tr><td>multimodal_clock_age_accel.parquet</td><td>2026-04-30 14:43</td><td>61.2 KB</td></tr><tr><td>multimodal_clock_feature_importance.csv</td><td>2026-04-30 14:43</td><td>141.0 KB</td></tr></tbody></table><div class="large-cautionThe deck is generated from the live result artifacts; source timestamps are recorded in sources.json.

Speaker note: This slide addresses provenance. It uses the latest result files and records exact paths and timestamps in sources.json.
---

## Aging-clock progress

<div class="image-card<img src="assets/clock_performance.svg)

Alt: Aging-clock MAE and R2 bar chart

Speaker note: This is an informative chart from clock_performance.csv. The key message is that the infrastructure now supports many aging dimensions; current performance varies and should be treated as preliminary.
---

## Cross-system concordance

<div class="image-card<img src="assets/concordance_pairs.svg)

Alt: Top aging-dimension concordance pairs

Speaker note: This replaces a dense heatmap with the top concordance pairs. It shows strong blood/inflammatory coupling and a circadian-autonomic-physical axis, with weaker cross-system coupling elsewhere.
---

## Diabetes-stage gradient

<div class="image-card<img src="assets/diabetes_gradient.svg)

Alt: Aging dimension effect sizes across diabetes severity

Speaker note: This chart comes from diabetes_gradient.csv. It makes the current diabetes-stage signals explicit, especially the CGM-metabolic and clinical metabolic dimensions.
---

## Digital biomarker signal

<div class="image-card<img src="assets/biomarker_features.svg)

Alt: Top features for best biomarker screen

Speaker note: This chart comes from the latest biomarker_panel.csv. It shows which features drive the strongest current screen. Interpret as a model-development signal, not a clinical biomarker claim.
---

## 10-day causal signal: environment and HR

<div class="image-card<img src="assets/pm25_hr_lags.svg)

Alt: PM2.5 heart-rate lag model summary

Speaker note: This chart uses the latest, enlarged causal_pm25_hr.csv. It summarizes cohort-scale lag-model output and is still nominal until the Critic applies multiple-comparison control, confounder checks, and site sensitivity.
---

## New problems this architecture can solve

<div class="problem-grid<div><b>Cross-modal aging**: Which organs age together, and which are discordant?<div><b>10-day causality**: Sleep, activity, glucose, HR, PM2.5, and light with lag structure.<div><b>Digital biomarkers**: Non-invasive signals for HbA1c, HOMA-IR, retinal damage, and AgeAccel.<div><b>Personal trial targets**: Which lever should this person test first?

Speaker note: These are the scientific problems that require the whole architecture. A single modality or a generic LLM cannot solve them cleanly.
---

## N-of-1 and test-time learning

<div class="image-card<img src="assets/n_of_1_visual.png)

Alt: Layer 3 N-of-1 trial suggestion and test-time learning schematic

Speaker note: This is the future integration vision. After the system identifies a person-level phenotype, it proposes a low-risk trial, observes the response, and updates both the person-specific latent state and the agent workflow memory.
---

## Roadmap

<div class="image-card<img src="assets/roadmap.svg)

Alt: Roadmap by architecture layer<div class="closing-lineThe model learns the population; the agent learns the person; the loop learns what works.

Speaker note: Close with the plan by layers: QC and result manifests for Layer 0; encoders and cross-modal JEPA for Layer 1; agent benchmarking, critic gates, and memory for Layer 2; N-of-1 suggestion and Bayesian monitoring for Layer 3.
