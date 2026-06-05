# Network Physiology of Diabetes: Brainstorm Document

> **Date:** 2026-04-26
> **Status:** Brainstorm — bold ideas grounded in literature and our data
> **Core thesis:** The signal isn't in the organs. It's in the wires between them. Health is coordination; diabetes is decoupling. AI-READI is the first dataset that can measure the wires.

---

## Table of Contents

1. [The Reframe: Why Coupling > Individual Clocks](#1-the-reframe)
2. [Literature Foundations](#2-literature-foundations)
3. [What Our Data Uniquely Enables](#3-what-our-data-uniquely-enables)
4. [Bold Research Directions](#4-bold-research-directions)
5. [Methodology Toolkit](#5-methodology-toolkit)
6. [Concrete Study Designs](#6-concrete-study-designs)
7. [What Would Make This a Nature Paper](#7-what-would-make-this-a-nature-paper)
8. [Open Questions & Risks](#8-open-questions--risks)
9. [References](#9-references)

---

## 1. The Reframe

### What the current results tell us

Our 13 aging clocks (Ridge regression on static features) achieve R² = 0.02–0.19. The unified clock combining all 15 age-acceleration dimensions gets AUC = 0.47 for healthy vs insulin-dependent — *worse than random*. Meanwhile, the simple Frailty Index (deficit counting) gets AUC = 0.90.

**What this means:** Static per-organ features are weak age predictors in this cohort. Summing them doesn't help. But deficit *accumulation* (frailty) — which implicitly measures how many systems are failing — works well. The signal is in the *pattern of system failure*, not in any single organ's state.

### The paradigm shift: from organ state to inter-organ coupling

The field of **Network Physiology** (Ivanov et al., 2012–2026) has established that:
- Health is characterized by **coordinated interactions** between organ systems
- Each physiological state (wake, sleep stages) has a **specific network topology** of inter-organ coupling
- Networks reorganize on timescales of **seconds to minutes** — far faster than static biomarkers capture
- Disease disrupts coupling structure before it changes individual biomarker values

**Translation to AI-READI:** Instead of asking "how old does each organ look?", ask "how well do your organs talk to each other?" The 10-day synchronized window (CGM + wearable + environment) is the first dataset where we can measure this coupling across the diabetes severity spectrum in >2,000 people.

### Why this is better than what exists

| Approach | Data | Measures | Limitation |
|---|---|---|---|
| Proteomic organ clocks (Oh et al., Nature 2023) | Blood proteins | Per-organ aging rate | No dynamics, no coupling |
| MRI multi-organ clocks (Nature Med 2025) | Structural imaging | Per-organ morphology | Snapshot, no temporal coupling |
| SleepFM (Nature Med 2026) | PSG (sleep lab) | Cross-modal contrastive embeddings | Sleep-only, no glucose/environment |
| CosinorAge (npj Dig Med 2024) | Activity rhythms | Circadian rhythm quality | Single modality |
| **Our approach** | CGM + wearable + environment + ECG + retinal + clinical | Inter-system coupling dynamics | First to measure coupling across metabolic, cardiac, circadian, sleep, and environmental systems simultaneously |

---

## 2. Literature Foundations

### 2.1 Network Physiology (the field)

| Paper | Key contribution | Relevance to us |
|---|---|---|
| Bashan et al., **Nature Communications** 2012 | Founded network physiology. Showed each physiological state has a specific network topology of inter-organ coupling. Networks undergo topological transitions within minutes. | Our template: build per-person physiological networks from the 10-day window, compare topology across diabetes groups. |
| Bartsch et al., **PLoS ONE** 2015 | Introduced **Time Delay Stability (TDS)** method — identifies stable coupling by tracking constant time delays between system activations. First maps of physiological organ networks across sleep stages. | TDS is directly applicable to our aligned 5-min CGM × HR × environment time series. |
| Ivanov, **Frontiers in Network Physiology** 2021 | "Building the Human Physiolome" — proposed network-based biomarkers for disease taxonomy, next-gen monitoring, personalized health. | Our work instantiates this vision for diabetes using wearable-scale data, not PSG. |
| Bartsch & Ivanov, **Springer** 2014 | Multiple independent coupling forms coexist on different time scales. Phase transitions during state changes. | Multi-scale coupling analysis: hourly, daily, multi-day coupling may break down at different disease stages. |

### 2.2 Loss of Complexity Hypothesis

| Paper | Key contribution | Relevance to us |
|---|---|---|
| Lipsitz & Goldberger, **JAMA** 1992 | Aging = progressive loss of physiologic complexity → diminished adaptive capacity. | Our coupling measures should show complexity loss with age AND with diabetes severity. |
| Goldberger et al., **PNAS** 2002 | Healthy heartbeat is multifractal with long-range correlations. Heart failure breaks fractal structure. | Apply multiscale entropy / DFA to our HR and glucose time series. |
| Costa et al., **Phys Rev Lett** 2002 | Introduced **Multiscale Entropy (MSE)** — quantifies complexity across time scales. | Compute MSE for glucose and HR per person. Compare across groups. |
| Lipsitz, **Physical Therapy** 2012 | Extended complexity-loss to physical function: gait, posture, cardiovascular control. Loss of complex variability underlies frailty. | Connects directly to our frailty index (AUC 0.90) — frailty may be measuring complexity loss. |

### 2.3 Cross-Modal Coupling in Diabetes (directly relevant)

| Paper | Key finding | What it means for us |
|---|---|---|
| Vallat et al., **Cell Reports Medicine** 2023 | Sleep spindle–slow oscillation coupling predicts next-day fasting glucose in 600+ people. Mechanism: deep-sleep coupling → parasympathetic activation → insulin sensitivity. Replicated in N=1,900. | The coupling BETWEEN sleep microstructure and glucose is a better predictor than sleep duration alone. We have sleep + CGM — test this. |
| Heart rate–glucose coupling during sleep, **Sleep Medicine** 2023 | Cross-correlation r = −0.453 between glucose and HRV during sleep. Hyperglycemia → increased HR and decreased HRV in real time. | Our aligned_timeseries() gives exactly this data at 5-min resolution. Compute per-person, compare across groups. |
| Fabris et al., **Scientific Reports** 2022 | 1/3 to 1/2 of glucose and activity variances are shared, even during sleep. Multiple coupling modes at different time scales. | Activity-glucose coupling is substantial and multi-scale. Our wearable + CGM data can decompose this by scale. |
| HRV in sleep stages and metabolic function in T2DM, **Frontiers Physiology** 2023 | Sleep-stage-specific HRV couples more tightly with metabolic function than awake HRV. | Sleep is a privileged window for measuring metabolic-cardiac coupling. Our Garmin sleep staging (imperfect but available) can approximate this. |
| Real-time HRV and ambulatory glucose, **Frontiers Cardiovasc Med** 2023 | Continuous association between glucose levels and HRV in ambulatory diabetic patients. Poor control → lower HRV. | Bidirectional glucose-HR coupling is real and graded by disease severity. Our 10-day window captures this. |
| Ventricular-arterial coupling in diabetes, **Cardiovascular Diabetology** 2025 | Diabetes (not prediabetes alone) impairs ventricular-arterial coupling. Effect equivalent to 6 years of aging. Diabetes worsens age-related diastolic dysfunction 5-fold. | Diabetes accelerates COUPLING loss, not just organ aging. Supports our thesis. |
| Neurovascular coupling in diabetic retinopathy, **Frontiers Medicine** 2022 | Neurovascular coupling differs across retinopathy stages. Sympathetic markers show stage-dependent responses. | Retinal-autonomic coupling changes with disease. Links our retinal imaging to cardiac/autonomic data. |
| HRV predicts incident T2DM, **JCEM** 2023 | Lower HRV precedes and predicts T2DM development. Autonomic dysfunction is a PRE-disease biomarker. | Cardiac-metabolic decoupling may precede clinical diabetes. Our pre-diabetes group (N=560) is the test. |
| Multimodal correlates of glucose spikes, **Nature Medicine** 2025 | 1,137 participants with CGM + wearable + diet + microbiome. Significant differences in glucose spike metrics across diabetes states. Longer spike resolution in T2D. | Closest comparable dataset to ours. But AI-READI has 2× the participants and adds environmental sensors + retinal imaging. |

### 2.4 Organ Cross-Talk and Aging

| Paper | Key finding | What it means for us |
|---|---|---|
| Oh et al., **Nature** 2023 | Proteomic organ clocks: ~20% of people have accelerated aging in one organ. 1.7% are multi-organ agers. Accelerated heart aging → 250% higher heart failure risk. | Our analog: per-person coupling profiles. "Decoupled" individuals (weak inter-organ communication) may have worse outcomes. |
| Wang et al., **Nature Aging** 2025 | Organ-specific proteomic clocks validated across UK Biobank (43K), Chinese (4K), US (800) cohorts. Brain aging most linked to mortality. | Our clocks are functional-signal-based, not proteomic. Complementary, not competing. |
| Organ cross-talk review, **Signal Transduction & Targeted Therapy** 2025 | Comprehensive review of molecular organ cross-talk: brain-gut, brain-heart, heart-kidney, heart-liver, gut-liver axes. | Maps the biological substrate of the coupling we'd measure computationally. |
| Aging at the crossroads of organ interactions, **Circulation Research** 2025 | Heart engages in multidimensional interactions with distant organs via metabolic, mechanical, and neuroendocrine coupling. Novel biomarkers proposed based on organ network interactions. | Exactly our framing: aging is at the crossroads of organ interactions, and we can measure those interactions. |

### 2.5 Causal Discovery from Time Series

| Method | Paper | Key innovation | Applicable to our data? |
|---|---|---|---|
| **Convergent Cross Mapping (CCM)** | Sugihara et al., **Science** 2012 | Detects causality in nonlinear coupled dynamical systems via Takens' shadow manifold reconstruction. Works when Granger fails. | Yes — glucose-HR dynamics are nonlinear. CCM on 10-day aligned series per person. |
| **Latent CCM** | **ICLR** 2021 | Neural ODE + GRU-ODE-Bayes for CCM on short, noisy, irregularly-sampled series where classical CCM fails. | Potentially useful for participants with sparse wearable data. |
| **PCMCI / PCMCI+** | Runge et al., **Science Advances** 2019; Runge, **UAI** 2020 | Two-stage: PC condition selection + MCI test. PCMCI+ adds contemporaneous causal relations. Scales to large nonlinear datasets. Implementation: `tigramite` v5.2+. | Yes — the most principled method for full multivariate causal graph. |
| **LPCMCI** | Gerhardus & Runge, **NeurIPS** 2020 | High-recall causal discovery with latent confounders. | Yes — if we suspect unmeasured confounders (e.g., medication, which is redacted). |
| **Transfer entropy** | Schreiber, **Phys Rev Lett** 2000 | Information-theoretic directed coupling (bits). Model-free, captures nonlinearity. | Yes — directed information flow between every modality pair. "Physiological bandwidth." |
| **TE applied to wearables** | Kim et al., **eBioMedicine (Lancet)** 2024 | 139 patients, >40,000 patient-days. TE revealed circadian phase disturbance causally precedes mood changes — not sleep itself. | Directly validates TE on wearable data at comparable scale to ours. |
| **Wavelet coherence** | Grinsted et al., 2004; Healey et al., **PMC** 2016 | Time-frequency coupling. Healey showed strong glucose-activity wavelet coherence in T1DM at 120-340 min oscillations. | Yes — multi-scale coupling spectrogram per person per modality pair. |
| **Granger causality** | Granger, 1969; Shojaie & Fox, **Ann Rev Stats** 2022 (comprehensive review) | Linear causal prediction. Simple, interpretable. | Already computed. Baseline method. |
| **DYNOTEARS** | Pamfil et al., **AISTATS** 2020 | Continuous optimization for DAG structure learning from time series. Extends NOTEARS (NeurIPS 2018). | Possible — gives full DAG structure. |
| **CUTS** | Cheng et al., **ICLR** 2023 | Neural causal discovery from irregular time series with missing data. Jointly imputes and learns causal graph. | Critical for real-world wearable data with random missingness. |
| **Recurrence Quantification Analysis** | Webber & Zbilut; Reyes-Lagos et al., **Frontiers Physiology** 2025 | RQA on pulse-respiration quotient showed T2DM patients have more rigid, less adaptive cardiorespiratory dynamics (higher recurrence rate, prolonged trapping time). | Yes — direct evidence of coupling rigidity in T2DM. Apply cross-recurrence to glucose-HR. |

**Important benchmark caveat:** CausalRivers (ICLR 2025) — largest real-world time-series causal benchmark — found that naive baselines often matched established methods and linear VAR-based Granger was most reliable; nonlinear/deep methods did not consistently outperform. **Start simple, add complexity only if needed.**

### 2.6 Advanced Analytical Methods

| Method | Key papers | Application to our data |
|---|---|---|
| **Tensor decomposition** (CP, Tucker, NTF) | Kolda & Bader, **SIAM Review** 2009; Becker et al., **WIREs** 2023 (EHR phenotyping review); Qian et al., arXiv 2025 (smooth CP for ambulatory BP wearable data) | Stack participants × time bins × modalities into 3D tensor. Decompose to find latent physiological modes spanning modalities and patients. |
| **Topological Data Analysis (TDA)** | Carlsson, **Bull AMS** 2009; Lee et al., **J Biol Rhythms** 2024 (TDA + circadian model improved wearable sleep staging AUROC >13%); **Lopez-Caballero et al., CIABiomed 2025** (persistent homology on CGM discriminates T1D vs T2D) | Persistent homology of CGM/HR time series. TDA captures glucose dynamics shape that summary statistics miss. |
| **Dynamical glucometry (MSE)** | Costa et al., **Chaos** 2014 — the foundational paper: CGM from T2DM has lower MSE complexity than controls across scales from 5 min to 5 hours; **Frontiers of Medicine** 2023 — complexity decreases progressively from normal → impaired → T2DM (P for trend < 0.01), disposition index (beta-cell function) is the only independent predictor of complexity | Compute MSE per person for glucose AND HR. Cross-modal complexity comparison. |
| **Glucodensities** | Matabuena et al., **Stat Methods Med Res** 2021; **Scientific Reports** 2025 — distributional glucose representation outperforms traditional CGM metrics by >20% adjusted R² for predicting 5/8-year HbA1c | Represent each person's glucose as a probability density. Compare via Wasserstein distance. Richer than scalar summaries. |
| **Optimal transport / Wasserstein** | Villani, 2003; Bunne et al., **Nature Rev Methods Primers** 2024 (OT for biological data); Haviv et al., **ICML** 2024 (Wasserstein Wormhole — transformer-based linear-time OT) | Compare per-person physiological distributions. Distance between a person's glucodensity and a "healthy template." |
| **Phase-amplitude coupling** | Tort et al., **J Neurophys** 2010 | Cross-frequency coupling between modalities. E.g., does the circadian phase of activity modulate the amplitude of glucose variability? |
| **Circadian misalignment** | **Scheer et al., PNAS 2009** — landmark: 10 adults, 28-hr forced desynchrony, **3 days of misalignment pushed 3/8 healthy subjects into prediabetic glucose ranges**; Speksnijder et al., **J Pineal Res** 2024 — central vs peripheral clock misalignment both impair glucose; Schrader et al., **JCI** 2024 — CLOCK/BMAL1 dimers bind islet cell regulatory sites; Bmal1-knockout mice develop glucose intolerance | Our environment (light) + wearable (activity) + CGM (glucose) data captures the full light → circadian → metabolism pathway. |

### 2.7 Cross-Modal Prediction and Digital Phenotyping (recent high-impact)

| Paper | Key finding | Relevance |
|---|---|---|
| Karunarathna et al., **Sensors** 2025 | R²=0.73 predicting glucose from 236 wearable features (EDA, HR, temp, accel). Top predictors: sex, circadian rhythm, tonic EDA. | Validates cross-modal glucose prediction from wearables at high accuracy. |
| **Marras et al., Nature 2026** | 1,165 participants: deep neural networks on wearable (HR, HRV, sleep, steps) + blood → HOMA-IR AUROC=0.80. | Wearable signals carry metabolic information. Published in **Nature** — establishes the paradigm. |
| **Liu et al., Cell 2025** | 250+ Fitbit features from ABCD study. Wearable digital phenotypes identified 16 genetic loci and 37 genes. **Greater detection power than fMRI.** | Wearable-derived phenotypes have genuine biological grounding, not just correlations. |
| **Carletti et al., Nature Medicine 2025** | 347 deeply phenotyped: two patients with identical HbA1c can have very different multimodal risk profiles. | Supports our thesis: static biomarkers (HbA1c) miss coupling information. |
| Reyes-Lagos et al., **Frontiers Physiology** 2025 | T2DM patients show more rigid, less adaptive cardiorespiratory coupling (RQA: higher recurrence rate, prolonged trapping time, especially during paced breathing). | **Direct evidence of physiological decoupling/rigidity in T2DM.** |

---

## 3. What Our Data Uniquely Enables

### 3.1 The 10-day synchronized window

No other dataset has this. For ~2,280 participants, we have:
- **CGM:** 5-min glucose readings (~2,880 points per person)
- **Wearable HR:** ~1-min resolution (~14,400 points)
- **Wearable activity/sleep/SpO2/stress:** sub-minute to per-event
- **Environmental sensor:** 5-sec resolution (~172,800 points)
- All aligned via `aligned_timeseries()` on a common 5-min grid

This gives us the temporal resolution to measure:
- Minute-scale coupling (acute glucose-HR response)
- Hour-scale coupling (postprandial dynamics, activity-glucose patterns)
- Day-scale coupling (sleep quality → next-day glucose)
- Multi-day trends (accumulation effects)

### 3.2 The diabetes severity gradient

Four cleanly defined groups: healthy (776) → pre-diabetes (560) → oral medication (686) → insulin-dependent (258). This is a natural "dose-response" gradient for coupling disruption. If coupling measures decrease monotonically across groups, that's strong evidence.

### 3.3 The combination with single-timepoint deep phenotyping

Beyond the 10-day window, each person also has:
- 12-lead ECG (500 Hz, 11 seconds) — cardiac electrophysiology
- Retinal imaging (CFP, OCT, OCTA, FLIO) — microvascular health
- 125 clinical lab features — systemic biochemistry
- MoCA cognitive assessment

This lets us link **dynamic coupling** (from the 10-day window) to **structural damage** (from imaging) and **systemic biochemistry** (from labs). The question: does coupling breakdown predict structural damage?

### 3.4 What nobody else can do

| Question | Why only AI-READI can answer it |
|---|---|
| Does glucose-HR coupling weaken across the diabetes spectrum? | Simultaneous CGM + HR in 2,280 people across 4 severity groups |
| Does circadian coupling (activity-glucose-environment phase alignment) predict metabolic health? | Three synchronized circadian-resolution sensors |
| Does environmental exposure (PM2.5, light) causally affect glucose through autonomic pathways? | Environment + HR + CGM simultaneously |
| Do coupling measures predict retinal damage? | 10-day coupling window + retinal imaging in the same people |
| Is "physiological age" better measured by coupling than by static features? | All of the above, plus clinical labs for benchmark comparison |

---

## 4. Bold Research Directions

### Direction A: "The Physiological Coupling Atlas of Diabetes"

**One-liner:** Build the first comprehensive map of inter-organ coupling across the diabetes severity spectrum using synchronized multimodal monitoring.

**What we compute per person (from the 10-day window):**

For every modality pair (glucose ↔ HR, glucose ↔ activity, glucose ↔ sleep, glucose ↔ environment, HR ↔ activity, HR ↔ sleep, HR ↔ environment, activity ↔ sleep, activity ↔ environment, sleep ↔ environment = 10 pairs):

1. **Time-lagged cross-correlation** — at what lag is coupling strongest?
2. **Wavelet coherence** — coupling at what time scales (1h, 6h, 24h)?
3. **Transfer entropy** — directed information flow (bits/sample)
4. **Cross-predictability** (R² of predicting one from the other)
5. **Phase coherence** at the circadian frequency (~24h)

This gives a **coupling matrix** per person (10 edges × 5 measures = 50 coupling features). Then:

- Compare coupling matrices across the 4 diabetes groups (Kruskal-Wallis per edge, FDR corrected)
- Build a **physiological coupling network** per person (graph where nodes are modalities, edges are coupling strengths)
- Compute graph-theoretic biomarkers: total coupling strength, modularity, hub centrality
- Test: does **total coupling strength** predict diabetes severity better than individual aging clocks?
- Test: which **specific edges** break first in pre-diabetes? (This reveals the causal pathway.)

**Why this is a Nature paper:** First demonstration that diabetes disrupts inter-organ coupling measurable from wearable-scale sensors. Reframes diabetes from a glucose disorder to a systems coordination disorder.

---

### Direction B: "Cross-Modal Predictability as a Disease Biomarker"

**One-liner:** The ability to predict one physiological signal from another — measured over a 10-day window — is itself a biomarker of health.

**Core computation per person:**

For each participant, fit lightweight per-person models (Ridge regression, or random forest):
- **Predict glucose from HR + activity:** How well can autonomic/behavioral signals explain glucose dynamics?
- **Predict HR from glucose + activity:** How well does cardiac function track metabolic state?
- **Predict next-day glucose from overnight sleep + HR:** How well does overnight physiology forecast daytime metabolism?
- **Predict sleep quality from daytime glucose + activity:** How well does daytime metabolism forecast sleep?

The R² of each prediction is the **coupling score** for that pair.

**Hypotheses:**
1. Cross-modal predictability decreases monotonically: healthy > pre-diabetes > oral med > insulin-dependent
2. The SPECIFIC edges that lose predictability first reveal the causal sequence of metabolic deterioration
3. Composite "predictability score" (average R² across all pairs) outperforms static aging clocks for diabetes severity discrimination
4. Individuals with high HbA1c but preserved coupling ("compensated diabetes") have better prognosis markers than those with similar HbA1c but broken coupling ("decompensated diabetes")

**Why this is powerful:** It requires no foundation model, no complex methods — just per-person regressions on aligned time series. Interpretable, reproducible, and directly actionable ("your glucose is decoupled from your cardiac-activity system, suggesting impaired autonomic glucose regulation").

---

### Direction C: "Temporal Concordance Aging — A Coupling-Based Biological Age"

**One-liner:** Biological age measured not by what your organs look like, but by how well they communicate.

**The shift:** Our current clocks use static features (mean glucose, mean HR, etc.) → R² = 0.02–0.19. The coupling features capture dynamics that static summaries miss.

**Feature set for the coupling clock:**
- Glucose-HR coherence at the circadian frequency
- Transfer entropy: sleep → glucose (bits/sample)
- Activity-glucose cross-correlation peak lag (healthy = fast response)
- Circadian phase alignment across modalities (intra-individual circadian coherence)
- Multiscale entropy of glucose (complexity of glycemic dynamics)
- Multiscale entropy of HR (complexity of cardiac dynamics)
- Total physiological bandwidth (sum of transfer entropies across all directed edges)

**Train on chronological age (Ridge/ElasticNet):** Coupling features → predicted age → coupling-based AgeAccel.

**The prediction:** Coupling-based AgeAccel will discriminate diabetes severity better than static-feature-based AgeAccel (AUC for healthy vs insulin-dependent > 0.70, vs current 0.47 for unified static clock).

**Why this could be transformative:** It defines a fundamentally new kind of aging clock — one based on **how well systems integrate**, not on the state of any individual system. This aligns with the complexity-loss hypothesis (Lipsitz & Goldberger 1992) and network physiology (Ivanov 2021) but has never been computed from wearable-scale data across a diabetes cohort.

---

### Direction D: "Convergent Cross Mapping for Nonlinear Causal Physiology"

**One-liner:** Use state-space methods to detect nonlinear causal relationships between physiological systems — impossible with standard Granger causality.

**Why CCM over Granger:** Glucose regulation involves threshold effects (insulin release at glucose ~100 mg/dL), saturation (max insulin response), and feedback loops (glucose → insulin → glucose). These are inherently nonlinear. Granger causality assumes linearity and can miss or reverse causal direction in coupled nonlinear systems (Sugihara et al., Science 2012).

**Per-person CCM analysis:**
1. Embed glucose and HR time series in delay-coordinate space (Takens embedding)
2. Test convergent cross mapping in both directions: glucose → HR and HR → glucose
3. CCM skill (correlation coefficient) at different library lengths reveals causal coupling strength
4. Compare directional coupling across diabetes groups

**Key prediction:** In healthy individuals, glucose → HR coupling is strong (autonomic response to glucose) and HR → glucose is weak (HR doesn't drive glucose). In insulin-dependent diabetes, glucose → HR weakens (autonomic neuropathy) and the directional asymmetry disappears. This would be the first demonstration of **nonlinear causal decoupling** in diabetes from wearable data.

**Extension: CCM on the full multivariate system** — build per-person causal networks where edge weights are CCM skill. Compare network topology across groups. Are there "causal hub" organs that drive the others?

---

### Direction E: "Multi-Scale Coupling Spectrograms"

**One-liner:** Different physiological processes couple at different time scales. Disease disrupts coupling scale-selectively.

**Method:** Wavelet coherence between each modality pair, decomposed into frequency bands:
- Ultra-fast (5–30 min): acute glucose excursions ↔ HR response
- Fast (30 min–3 h): postprandial dynamics ↔ activity patterns
- Circadian (12–36 h): daily rhythms across all modalities
- Multi-day (2–10 days): slow trends, recovery patterns

**Per-person coupling spectrogram:** A 2D image (modality pair × frequency band) showing coupling strength at each scale.

**Hypotheses:**
1. **Pre-diabetes** shows preserved circadian coupling but broken ultra-fast coupling (acute glucose-HR response is impaired while daily rhythms are intact)
2. **Oral medication** shows circadian coupling partially restored by treatment but ultra-fast still broken
3. **Insulin-dependent** shows breakdown at ALL scales — circadian, fast, and ultra-fast
4. The **scale at which coupling first breaks** differs between individuals and predicts which complications develop

**Why this is novel:** Nobody has decomposed physiological coupling by time scale in diabetes. This gives a much richer picture than single-scale measures and directly connects to the multi-scale nature of diabetes pathophysiology.

---

### Direction F: "Environmental-Physiological Coupling: The Exposome-Metabolism Axis"

**One-liner:** Personal environmental exposure (PM2.5, light, temperature) causally affects glucose and cardiac function through autonomic pathways — and this coupling weakens with diabetes severity.

AI-READI's Anura environmental sensor gives personal (not population-average) exposure at 5-second resolution. Nobody else has this synchronized with CGM + HR.

**Causal pathway to test:**

```
PM2.5 exposure → autonomic stress (HR↑, HRV↓) → glucose dysregulation
                                                       ↓
Evening blue light → circadian delay → late sleep onset → poor glucose next day
                                                       ↓
Temperature extremes → physiological stress → glucose variability ↑
```

**Method:** Lagged causal analysis (PCMCI) with environment as exogenous forcing, HR as mediator, glucose as outcome.

**Key question:** Is the environment-glucose coupling mediated entirely by autonomic pathways (HR/HRV), or is there a direct metabolic effect? Mediation analysis with bootstrap confidence intervals.

**Why unique:** This is the first test of whether personal environmental exposure causally affects glucose dynamics in diabetes, with HR as a measured mediator. Population-level air quality studies (EPA, WHO) can't do within-person causal inference.

---

### Direction G: "Tensor Decomposition: Discovering Latent Physiological Modes"

**One-liner:** Stack the multimodal time series into a 3D tensor and decompose to find latent temporal patterns spanning modalities.

**Setup:**
- Tensor: 2,280 participants × T time bins × M modalities
- Time bins: aggregate the 10-day window into, e.g., 6-hour blocks (40 bins) or daily blocks (10 bins)
- Modalities: mean glucose, mean HR, activity level, sleep state, PM2.5, light exposure

Apply **non-negative CP decomposition** (or Tucker decomposition) to factor into K components, each with:
- A participant loading (who expresses this pattern?)
- A temporal profile (when does this pattern occur?)
- A modality profile (which signals participate?)

**What we might discover:**
- **Factor 1:** "Coordinated circadian" — strong 24h rhythm in all modalities, high loading in healthy participants
- **Factor 2:** "Nocturnal metabolic stress" — elevated nighttime glucose + elevated nocturnal HR + poor deep sleep, high loading in insulin-dependent
- **Factor 3:** "Environmental sensitivity" — PM2.5 correlated with HR and glucose, characterizing a susceptible subgroup
- **Factor 4:** "Activity-glucose responders" — strong coupling of physical activity → glucose reduction, characterizing those who benefit most from exercise

**Why this is interesting:** Current subtypes (3 clusters from static AgeAccel) are based on point estimates. Tensor decomposition finds subtypes from TEMPORAL DYNAMICS — potentially revealing phenotypes invisible to static analysis.

---

## 5. Methodology Toolkit

### 5.1 Per-Person Coupling Measures (computed over 10-day window)

| Measure | What it captures | Python implementation | Time complexity |
|---|---|---|---|
| **Time-lagged cross-correlation** | Linear coupling at optimal lag | `scipy.signal.correlate` | O(N log N) per pair |
| **Wavelet coherence** | Time-frequency coupling | `pycwt` or `ssqueezepy` | O(N × F) per pair |
| **Transfer entropy** | Directed information flow (bits) | `pyinform` or `Tigramite` | O(N × k²) per direction |
| **Convergent cross mapping** | Nonlinear causal coupling | `pyEDM` (Sugihara lab) or custom | O(N × L) per direction |
| **PCMCI** | Multivariate causal graph | `tigramite` (Runge) | O(N × p × d²) full graph |
| **Phase coherence** | Synchronization at specific frequency | `scipy.signal.coherence` | O(N log N) per pair |
| **Cross-recurrence** | Recurrence structure between systems | `pyrqa` | O(N²) per pair |
| **Multiscale entropy** | Complexity across time scales | `EntropyHub` or `antropy` | O(N × S) per signal |
| **Cross-predictability** | Practical coupling (R² of prediction) | `sklearn.linear_model.Ridge` per person | O(N × d) per pair |
| **DFA / multifractal DFA** | Long-range correlations, fractal structure | `nolds` or `MFDFA` | O(N log N) per signal |

### 5.2 Cohort-Level Analysis

| Analysis | What it tests | Method |
|---|---|---|
| Coupling × diabetes group | Does coupling degrade with severity? | Kruskal-Wallis + pairwise Mann-Whitney, FDR corrected, effect sizes |
| Coupling → structural damage | Does weak coupling predict retinal/cardiac damage? | Partial correlation, coupling features → retinal AgeAccel / cardiac AgeAccel, adjusted for age |
| Coupling-based aging clock | Can coupling features predict age? | RidgeCV on coupling features → age, compute AgeAccel |
| Coupling network subtypes | Do coupling profiles define distinct phenotypes? | UMAP + HDBSCAN on coupling feature vectors |
| Coupling as mediator | Does coupling mediate the diabetes → organ damage pathway? | Causal mediation analysis (pingouin, semopy) |
| Site bias check | Robust across UW / UCSD / UAB? | Stratified analysis within each site |

### 5.3 Computational Feasibility

2,280 participants × 10 modality pairs × 5 coupling measures = ~114,000 computations. At ~1 second per computation (conservative for 10-day series), that's ~32 hours on a single core. Embarrassingly parallel — fits on a SLURM job with 16 cores in ~2 hours.

---

## 6. Concrete Study Designs

### Study 1: "Network Physiology of Type 2 Diabetes" (the flagship paper)

**Aim:** Characterize inter-organ coupling across the diabetes severity spectrum.

**Design:**
1. Compute per-person coupling matrix (10 pairs × 5 measures) from the 10-day window
2. Compare each coupling measure across 4 diabetes groups (effect sizes, FDR)
3. Build physiological coupling networks per person; compute graph metrics
4. Test: total coupling strength vs diabetes severity (linear trend)
5. Identify which edges break first in pre-diabetes (earliest decoupling signals)
6. Train coupling-based aging clock; compare to static aging clocks
7. Link coupling to structural damage (retinal AgeAccel, cardiac AgeAccel)

**Figures:**
- Fig 1: Coupling atlas — heatmap of all coupling measures × diabetes groups
- Fig 2: Per-person physiological networks (example healthy vs insulin-dependent)
- Fig 3: Total coupling strength vs diabetes severity (violin plots)
- Fig 4: Edge-specific decoupling trajectory (which couplings break first?)
- Fig 5: Coupling-based aging clock vs static clock (AUC comparison)
- Fig 6: Coupling predicts structural damage (retinal/cardiac AgeAccel)

**Target:** Nature Medicine or Nature Aging

---

### Study 2: "Cross-Modal Predictability as a Digital Biomarker" (methods paper)

**Aim:** Demonstrate that cross-modal prediction error from wearable + CGM data is a clinically meaningful biomarker.

**Design:**
1. Per-person cross-modal prediction (6 direction pairs)
2. Predictability score as a function of diabetes severity
3. "Compensated" vs "decompensated" diabetes subtyping
4. External validation concept: predictability score vs clinical outcomes

**Target:** Nature Digital Medicine or Lancet Digital Health

---

### Study 3: "Nonlinear Causal Coupling in Diabetes" (methods + discovery paper)

**Aim:** Apply CCM and PCMCI to reveal the causal architecture of inter-organ communication in diabetes.

**Design:**
1. Per-person CCM for all modality pairs (bidirectional)
2. Per-person PCMCI causal graphs
3. Compare causal network topology across groups
4. Identify causal hubs and pathways that change with disease

**Target:** Science Advances or PNAS

---

## 7. What Would Make This a Nature Paper

### The ideal result

1. **Coupling degrades monotonically** from healthy → insulin-dependent (p < 0.001, Cohen's d > 0.8 for total coupling strength)
2. **Specific decoupling sequence**: glucose-HR coupling breaks first in pre-diabetes (before glucose-sleep or activity-glucose), suggesting autonomic neuropathy as the earliest coupling failure
3. **Coupling-based aging clock** achieves AUC > 0.80 for healthy vs insulin-dependent (vs 0.47 for current static unified clock)
4. **Coupling predicts structural damage**: weak glucose-HR coupling → faster retinal aging (retinal AgeAccel), independent of HbA1c
5. **Environmental coupling matters**: PM2.5 → HR → glucose causal chain is stronger in healthy (buffered) and weaker in insulin-dependent (unbuffered) — first demonstration that diabetes impairs environmental buffering capacity
6. **Subtypes from coupling** cut across the 4 clinical groups — identifying "at-risk but clinically normal" and "compensated despite diagnosis" phenotypes

### What reviewers will challenge

| Challenge | Our defense |
|---|---|
| "10 days is too short for reliable coupling measures" | Bashan et al. (2012) showed network transitions on minute timescales. 2,880 CGM points per person is sufficient for cross-correlation, wavelet coherence, and transfer entropy. Report confidence intervals per person. |
| "Consumer-grade wearable (Garmin) lacks PSG accuracy" | We're measuring coupling, not absolute values. Garmin HR tracks clinical-grade for coupling analysis even if sleep staging is imperfect. Sensitivity analysis: repeat with HR-only (no sleep staging). |
| "Cross-sectional, so can't prove causality" | Within-person causal analysis (Granger/CCM/PCMCI on the 10-day window) IS within-person — same person's glucose causing same person's HR. Cross-sectional limitation is between-person trajectory, not within-person causality. |
| "Sex is redacted" | Coupling measures don't require sex. None of our coupling features use sex-specific formulas. Limitation: can't stratify by sex. |
| "Site bias" | Our infrastructure already has site_bias_check(). Report all results stratified by site. |
| "Multiple comparisons" | FDR correction (Benjamini-Hochberg) throughout. Report effect sizes, not just p-values. |

---

## 8. Open Questions & Risks

1. **Do we have enough temporal resolution?** CGM is 5-min, Garmin HR is ~1-min, but wearable activity/sleep are less frequent. The aligned 5-min grid may miss faster coupling dynamics (e.g., acute HR response to glucose spike peaks at ~2-3 min).

2. **Per-person model stability:** With ~2,880 CGM points per person (~10 days), some coupling measures (especially transfer entropy and CCM) may be noisy for individual participants. Mitigation: report distributions across participants, not individual point estimates. Use bootstrap confidence intervals.

3. **Confounders:** Medications (especially beta-blockers, insulin) directly affect HR and glucose dynamics. Medication data is redacted in the public release. This is a real limitation — medication effects could look like "coupling change."

4. **The Garmin sleep staging problem:** Garmin's sleep staging has poor epoch-by-epoch agreement with PSG. For sleep-dependent coupling analyses (e.g., sleep stage-specific HRV-glucose coupling), this adds noise. Mitigation: use only sleep/wake classification (more reliable) rather than REM/NREM staging.

5. **Computational cost of CCM and PCMCI:** Per-person CCM with Takens embedding at multiple library lengths is more expensive than cross-correlation. Estimate: ~30 seconds per person per direction. For 2,280 × 10 directed pairs = ~190 hours on single core. Needs parallelization (SLURM array job).

6. **The "so what" question:** If coupling degrades with diabetes severity, is this actionable? Connection: coupling measures could serve as (a) early detection biomarkers (pre-diabetes screening from wearable + CGM), (b) treatment response monitors (does metformin restore coupling?), (c) personalized intervention targets (which coupling is weakest for this person?).

---

## 9. References

### Network Physiology
- Bashan A et al. Network physiology reveals relations between network topology and physiological function. **Nature Communications** 3:702, 2012.
- Bartsch RP et al. Network Physiology: How Organ Systems Dynamically Interact. **PLoS ONE**, 2015.
- Bartsch RP, Ivanov PCh. Coexisting Forms of Coupling and Phase-Transitions in Physiological Networks. **NDES 2014**, Springer.
- Liu KKL et al. Dynamic network interactions among distinct brain rhythms. **Communications Biology** 3:197, 2020.
- Ivanov PCh. The New Field of Network Physiology: Building the Human Physiolome. **Frontiers in Network Physiology** 1:711778, 2021.

### Complexity and Aging
- Lipsitz LA, Goldberger AL. Loss of 'complexity' and aging. **JAMA** 267:1806–1809, 1992.
- Goldberger AL et al. Fractal dynamics in physiology: Alterations with disease and aging. **PNAS** 99:2466–2472, 2002.
- Costa M, Goldberger AL, Peng CK. Multiscale entropy analysis of complex physiologic time series. **Phys Rev Lett** 89:068102, 2002.
- Costa M, Goldberger AL, Peng CK. Multiscale entropy analysis of biological signals. **Phys Rev E** 71:021906, 2005.
- Lipsitz LA. Physiologic Complexity and Aging. **Physical Therapy** 92(11):1388–1394, 2012.

### Organ-Specific Aging
- Oh HS-H et al. Organ aging signatures in the plasma proteome track health and disease. **Nature** 624:164–172, 2023.
- Wang B et al. Organ-specific proteomic aging clocks predict disease and longevity. **Nature Aging**, 2025.
- Tian YE et al. Heterogeneous aging across multiple organ systems. **Nature Medicine** 29, 2023.
- Wen J, Tian YE et al. Genetic architecture of biological age across 9 organ systems. **Nature Aging**, 2024.

### Cross-Modal Coupling in Diabetes
- Vallat R et al. Coordinated human sleeping brainwaves map peripheral body glucose homeostasis. **Cell Reports Medicine** 4(7), 2023.
- Heart rate–glucose coupling during sleep. **Sleep Medicine**, 2023.
- Fabris C et al. Glucose and physical activity coupling. **Scientific Reports**, 2022.
- HRV in sleep stages and metabolic function in T2DM. **Frontiers in Physiology**, 2023.
- Real-time HRV and ambulatory glucose profiles. **Frontiers in Cardiovascular Medicine**, 2023.
- Ventricular-arterial coupling in diabetes. **Cardiovascular Diabetology**, 2025.
- Neurovascular coupling in diabetic retinopathy. **Frontiers in Medicine**, 2022.
- HRV and incident type 2 diabetes. **JCEM** 108(10):2510, 2023.
- Multimodal AI correlates of glucose spikes. **Nature Medicine**, 2025.

### Organ Cross-Talk
- Organ cross-talk review. **Signal Transduction & Targeted Therapy** (Nature), 2025.
- Aging at the crossroads of organ interactions. **Circulation Research**, 2025.

### Causal Discovery Methods
- Sugihara G et al. Detecting causality in complex ecosystems. **Science** 338:496–500, 2012.
- Latent Convergent Cross Mapping. **ICLR**, 2021. (Neural ODE-based CCM for short/noisy series)
- Runge J et al. Detecting and quantifying causal associations in large nonlinear time series datasets. **Science Advances** 5:eaau4996, 2019.
- Runge J. PCMCI+ for contemporaneous + lagged causal discovery. **UAI**, 2020.
- Gerhardus A, Runge J. LPCMCI: High-recall causal discovery with latent confounders. **NeurIPS**, 2020.
- Schreiber T. Measuring information transfer. **Phys Rev Lett** 85:461, 2000.
- Kim H et al. Causal dynamics of sleep, circadian rhythm, and mood via transfer entropy from wearable data. **eBioMedicine (Lancet)** 102, 2024.
- Grinsted A et al. Application of cross wavelet transform and wavelet coherence. **Nonlinear Processes in Geophysics** 11:561–566, 2004.
- Healey et al. Glucose-activity wavelet coherence in T1DM. **PMC4760432**, 2016.
- Pamfil A et al. DYNOTEARS: Structure learning from time-series data. **AISTATS**, 2020.
- Cheng Y et al. CUTS: Neural Causal Discovery from Irregular Time-Series Data. **ICLR**, 2023.
- CausalRivers benchmark. **ICLR**, 2025. (Linear Granger was most reliable; nonlinear methods did not consistently outperform.)
- Shojaie A, Fox EB. Granger Causality: A Review and Recent Advances. **Annual Review of Statistics** 9:289–319, 2022.
- Assaad C et al. Survey and Evaluation of Causal Discovery Methods for Time Series. **JAIR** 73:767–819, 2022.
- Katta S et al. Interpretable Causal Inference for Wearable and Distributional Data. **AISTATS**, 2024.

### Advanced Methods
- Kolda TG, Bader BW. Tensor decompositions and applications. **SIAM Review** 51(3):455–500, 2009.
- Becker F et al. Unsupervised EHR-based phenotyping via matrix and tensor decompositions. **WIREs** 13(4):e1494, 2023.
- Qian L et al. Smooth tensor decomposition for ambulatory BP monitoring wearable data. **arXiv:2507.11723**, 2025.
- Carlsson G. Topology and data. **Bulletin of the AMS** 46(2):255–308, 2009.
- Lee MP et al. TDA + circadian model improves wearable sleep staging. **J Biological Rhythms** 39(6):535–553, 2024.
- Lopez-Caballero A et al. Characterising CGM Using Topological Data Analysis. **CIABiomed 2025**, LNCS 16148.
- Costa MD et al. Dynamical glucometry: Multiscale entropy in diabetes. **Chaos** 24(3):033139, 2014.
- Decreasing complexity of glucose correlates with deteriorating regulation. **Frontiers of Medicine**, 2023.
- Matabuena M et al. Glucodensities: distributional glucose representation. **Stat Methods Med Res** 30(6):1445–1464, 2021.
- Matabuena M et al. Glucodensity profiles outperform traditional CGM metrics. **Scientific Reports** 15:33662, 2025.
- Bunne C et al. Optimal transport for single-cell and spatial omics. **Nature Rev Methods Primers** 4, 2024.
- Haviv D et al. Wasserstein Wormhole: Scalable OT with Transformers. **ICML**, 2024.
- Tort ABL et al. Measuring phase-amplitude coupling. **J Neurophysiology** 104:1195–1210, 2010.
- Scheer FAJL et al. Adverse metabolic consequences of circadian misalignment (3 days → prediabetes in 3/8 healthy). **PNAS** 106:4453–4458, 2009.
- Speksnijder EM et al. Circadian desynchrony and glucose metabolism. **J Pineal Research** 76:e12956, 2024.
- Schrader LA et al. Circadian disruption, clock genes, and metabolic health. **JCI** 134(14):e170998, 2024.
- Reyes-Lagos JJ et al. Diabetes alters cardiorespiratory dynamics (RQA). **Frontiers in Physiology** 16:1584922, 2025.

### Cross-Modal Prediction and Digital Phenotyping
- Karunarathna TS et al. Non-invasive glucose prediction from multimodal wearable (R²=0.73). **Sensors** 25(10):3207, 2025.
- Marras et al. Insulin resistance prediction from wearables (AUROC=0.80). **Nature**, 2026.
- Liu JJ et al. Digital phenotyping from wearables identifies genetic associations (16 loci, >fMRI). **Cell** 188(2), 2025.
- Carletti M et al. Multimodal AI correlates of glucose spikes. **Nature Medicine** 31:3121–3127, 2025.

### Datasets and Context
- AI-READI v3.0.0. DOI: 10.60775/fairhub.3.
- Moorman JR et al. Heart rate characteristics monitoring for neonatal sepsis. **npj Digital Medicine**, 2022.
- Raut RV et al. Arousal as universal embedding for spatiotemporal brain dynamics. **Nature** 647:454–461, 2025.
- SleepFM: Thapa et al. **Nature Medicine** 32(2):752–762, 2026.
- Farabi et al. Glucose-activity coupling during sleep and wake. **Scientific Reports** 12:4887, 2022.
