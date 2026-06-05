---
marp: true
theme: default
paginate: true
size: 16:9
style: |
  section { font-size: 20px; }
  h1 { font-size: 34px; color: #1a365d; }
  h2 { font-size: 26px; color: #2c5282; }
  h3 { font-size: 20px; color: #4a5568; }
  table { font-size: 16px; }
  code { font-size: 14px; }
  .columns { display: flex; gap: 2em; }
  .col { flex: 1; }
  blockquote { font-size: 16px; border-left: 4px solid #2c5282; padding-left: 1em; }
  .small { font-size: 14px; }
---

# Agentic Multi-Dimensional Biological Aging from Synchronized Multimodal Physiological Signals

**Zijian (Carl) Ma**
Stanford University | TWC Lab

AI-READI v3.0.0 | 2,280 participants | 9 modalities | 15 aging dimensions

---

## The Problem

**Biological aging is multi-dimensional, but we measure it one organ at a time.**

| Existing Multi-Organ Clocks | Modality | Limitation |
|---|---|---|
| Oh et al. (*Nature* 2023) | Plasma proteomics | Requires mass spectrometry |
| Tian/Wen et al. (*Nat Aging* 2024) | MRI + clinical labs | Requires hospital MRI |
| MRI multi-organ (*Nat Med* 2025) | UK Biobank MRI | 7 organs, imaging only |
| LifeClock (*Nat Med* 2025) | EHR codes | No continuous monitoring |

**What's missing:** No system measures aging across clinical labs, continuous glucose, wearable activity, cardiac electrophysiology, retinal imaging, AND personal environment -- in the same individuals, at the same time.

**And:** LLMs alone score 0.48-0.54 (random chance) on aging biology tasks (LongevityBench, 2026). Agents must be grounded in computed features, not parametric knowledge.

---

## AI-READI: The Dataset

**2,280 participants** | 3 sites (UW, UCSD, UAB) | 4 T2DM severity groups | ~3.82 TB

| Modality | Format | Coverage | Temporal |
|---|---|---|---|
| Clinical labs + vitals (125 features) | OMOP CDM | 100% | Snapshot |
| Cardiac ECG (12-lead, 500 Hz, 11s) | WFDB | 98.7% | Snapshot |
| Retinal (CFP, OCT, OCTA, FLIO) | DICOM | 81-99.8% | Snapshot |
| Wearable (HR, SpO2, sleep, stress, RR, activity) | OMH JSON | 95.8% | **~10 days** |
| Continuous glucose (Dexcom G6, 5-min) | OMH JSON | 98.5% | **~10 days** |
| Environmental sensor (PM2.5, light, temp, VOC) | CSV, 5-sec | 97.9% | **~10 days** |

**Cohort stratification:**
Healthy (776) | Pre-diabetes (560) | Oral medication (686) | Insulin-dependent (258)

**Recommended splits:** Train 1,576 | Val 352 | Test 352

---

## The Unique 10-Day Synchronized Window

Unlike any other public dataset, AI-READI captures **~10 days of simultaneous continuous monitoring** from 3 wearable/environmental sensors, all anchored to the same clinic visit with labs + imaging.

```
           Clinic visit (Day 0)
                │
  Retinal ─────●───── snapshot (CFP, OCT, OCTA, FLIO)
  ECG ─────────●───── 11-second recording
  Labs ────────●───── 125 clinical measurements
                │
  CGM    ══════●══════════════════  ~10 days, 5-min intervals (~2,856 readings)
  Garmin ══════●══════════════════  ~10 days, HR/sleep/SpO2/stress/activity (7 streams)
  Anura  ══════●══════════════════  ~10 days, PM2.5/light/temp/VOC (5-sec intervals)
```

**This enables:**
1. **Within-person causal inference** -- does last night's sleep quality cause today's glucose dysregulation?
2. **Cross-modal temporal alignment** -- glucose, HR, and PM2.5 on a shared 5-min grid per person
3. **Functional aging clocks** from behavioral dynamics, not just static labs
4. **N-of-1 phenotyping** -- each person's circadian fingerprint, glucose response pattern, sleep architecture

---

## System Architecture: Four Layers

```
  Layer 3:  LONGEVITY OS BRIDGE ──────── Population findings → individual phenotype
            N-of-1 trial suggestions       → personalized interventions
            ─────────────────────────────────────────────────────────────────
  Layer 2:  MULTI-AGENT SYSTEM ───────── Orchestrator → Modality agents (6)
            Scientific reasoning              → Reasoning agents (5) → Critic
            ─────────────────────────────────────────────────────────────────
  Layer 1:  FOUNDATION MODELS ────────── Pretrained encoders (RETFound, ECGFounder)
            Learned representations          → Cross-modal JEPA (future)
            ─────────────────────────────────────────────────────────────────
  Layer 0:  DATA INFRASTRUCTURE ──────── 18 Python modules, 9 modality loaders
            scripts/ API                     → Feature matrix (2280 x 125+48+2048)
```

**What's built:**
- **Layer 0**: Complete (18 scripts, ~2,000 lines, all 9 modality loaders)
- **Layer 1**: Partial (RETFound + ECGFounder deployed, cross-modal JEPA designed but not trained)
- **Layer 2**: Complete (11 agents, 5 task pipelines, critic, memory, workspace)
- **Layer 3**: Designed (Longevity OS integration planned)

---

## Layer 0: Data Infrastructure (Complete)

**1,970 lines of Python across 18 modules**

<div class="columns"><div class="col">

**Core loaders (`scripts/loaders/`):**
- `clinical.py` -- 6 OMOP CDM CSV tables, concept mapping
- `ecg.py` -- WFDB 12-lead ECG → (5500, 12) arrays
- `cgm.py` -- Dexcom G6 → DataFrame + 16 glycemic metrics
- `wearable.py` -- 7 Garmin sub-modalities → unified DataFrames
- `environment.py` -- 22-channel sensor with 45-line header parsing
- `retinal.py` -- 4 imaging sub-modalities, lazy DICOM loading

**Unified access:**
- `features.py` -- 2,280 x 125 clinical feature matrix (Parquet)
- `multimodal.py` -- `get_participant("1046")` → lazy multimodal accessor
- `participant_index.py` -- per-person availability flags
- `utils/temporal.py` -- cross-modal 5-min time alignment

</div><div class="col">

**Data quality issues resolved:**
- Insulin units: ng/L → uU/mL (divide by 0.04034)
- CRP: mg/L (not mg/dL as PhenoAge assumes)
- Creatinine: mg/dL (multiply by 88.4 for umol/L)
- Humidity: data is 0-100% despite header claiming 0-1
- Lymphocyte % missing → PhenoAge blocked, KDM used instead
- Sex redacted → eGFR, MetS, ASCVD scores blocked

**Generated artifacts:**
- `feature_matrix.parquet` (2,280 x 125)
- `multimodal_features.parquet` (2,280 x 48)
- `clinical_scores.parquet` (2,280 x 10)
- `participant_index.parquet` (2,280 x 39)
- `retinal_embeddings.parquet` (2,274 x 1,024)
- `cardiac_embeddings.parquet` (2,251 x 1,024)

</div></div>

---

## Layer 2: Multi-Agent System Architecture

```
                         ┌──────────────────────────────┐
                         │     ORCHESTRATOR AGENT        │
                         │  Decomposes → routes → synth  │
                         └──────────────┬───────────────┘
                                        │
              ┌─────────────────────────┼─────────────────────────┐
              │                         │                         │
    ┌─────────▼─────────┐   ┌──────────▼──────────┐   ┌─────────▼─────────┐
    │  MODALITY AGENTS   │   │  REASONING AGENTS    │   │  CRITIC AGENT     │
    │  (Tier 1: data)    │   │  (Tier 2: insight)   │   │  (validation)     │
    │                    │   │                      │   │                   │
    │  ClinicalAgent     │   │  HypothesisAgent     │   │  - Age adjustment │
    │  GlucoseAgent      │   │  CausalAgent         │   │  - Site bias      │
    │  CardiacAgent      │   │  PhenotypeAgent       │   │  - FDR correction │
    │  WearableAgent     │   │  AgingClockAgent      │   │  - Effect sizes   │
    │  RetinalAgent      │   │  LiteratureAgent      │   │  - Missing data   │
    │  EnvironmentAgent  │   │                      │   │  - Sensitivity    │
    └─────────┬─────────┘   └──────────┬──────────┘   └───────────────────┘
              └──────────────┬──────────┘
                    SHARED WORKSPACE + MEMORY
                    (findings, hypotheses, workflows, domain knowledge)
```

**Key design principle:** Agents write Python against `scripts/` API, execute in sandbox, observe results. They never hallucinate statistics -- they compute them. (Follows PHIA/CodeAct pattern.)

---

## Agent Deep Dive: ClinicalAgent

**Data access:** `load_feature_matrix()` → 2,280 x 125 clinical features

**Concrete problems it solves:**

1. **Clinical composite aging scores** -- computes KDM biological age, allostatic load (12 binary risk flags), frailty index (42 deficits), HOMA-IR/TyG/QUICKI insulin resistance indices
   - Discovered insulin unit mislabel in raw data (ng/L vs uU/mL) -- would have produced 25x error in HOMA-IR

2. **Cohort characterization** -- Table 1 demographics, stratified comparisons with Kruskal-Wallis + pairwise effect sizes + FDR correction
   - HbA1c gradient: Healthy 5.54% → Insulin-dependent 7.38% (eta-squared=0.41)
   - Significant site bias detected (p=6.6e-6) -- all downstream analyses must adjust

3. **System-specific aging clocks** -- extracts organ-specific feature panels, trains Ridge regressions on train split
   - 7 system clocks: immune, metabolic, renal, hepatic, cardiovascular, hematologic, cognitive
   - Best: Cardiovascular (MAE=8.1y, R2=0.19) driven by troponin T + NT-proBNP + pulse pressure

**Implementation:** `scripts/aging_scores.py`, `scripts/aging_clocks.py`, `scripts/features.py`

---

## Agent Deep Dive: GlucoseAgent

**Data access:** `loaders/cgm.py` → per-person Dexcom G6 time series (~2,856 readings over ~10 days)

**Concrete problems it solves:**

1. **CGM metabolic aging clock (NOVEL)** -- no aging clock from CGM exists in the literature
   - Features: mean glucose, CV, 5-level TIR, MAGE, GRI, LBGI/HBGI, GMI, dawn phenomenon, nocturnal mean/CV
   - Trained on AI-READI: MAE=9.2y, r=0.22
   - The first continuous glucose aging clock ever built

2. **Glucose-HR temporal coupling** -- aligns CGM with wearable HR on 5-min grid
   - Cross-correlation reveals optimal lag between glucose spikes and HR response
   - Tests whether coupling strength differs by diabetes severity (Phase 5 causal analysis)

3. **Dawn phenomenon quantification** -- 4-7am glucose rise vs 0-4am baseline
   - Physiologically: hepatic glucose output before waking, amplified in insulin resistance
   - Detectable from CGM without any provocation test

4. **Digital HbA1c proxy** -- GMI (3.31 + 0.024 x mean_glucose) from 10 days of CGM
   - Discrepancy between GMI and lab HbA1c ("glycation gap") is itself a biomarker of hemoglobin turnover

**Implementation:** `scripts/loaders/cgm.py`, `scripts/aging_features_batch.py`

---

## Agent Deep Dive: WearableAgent

**Data access:** `loaders/wearable.py` + `features_wearable.py` → 7 Garmin streams over ~10 days

**Concrete problems it solves:**

1. **Circadian aging clock** -- adapts CosinorAge approach to Garmin data
   - Features: IS (interdaily stability), IV (intradaily variability), M10/L5, RA (relative amplitude), cosinor amplitude/acrophase/mesor
   - MAE=8.8y, r=0.33 -- circadian disruption ages you
   - RA declines with aging and diabetes -- a functional marker of autonomic health

2. **Sleep architecture from consumer wearable** -- per-night TST, SE, WASO, REM%, deep%, N_awakenings
   - Sleep aging clock: MAE=9.2y from 6 features
   - Top predictor of HbA1c among wearable features: REM% (coef=-0.16)
   - Caveat: Garmin is NOT PSG-equivalent (epoch-level specificity only 29-52%)

3. **Autonomic aging** -- resting HR, nocturnal HR, diurnal HR, nocturnal dip %
   - MAE=8.8y, r=0.31
   - Nocturnal HR dip is a marker of ANS health; reduced dipping associates with cardiovascular risk

4. **Physical aging** -- daily steps + active calories → age
   - MAE=8.9y from just 2 features -- remarkably informative
   - Consistent with UK Biobank accelerometry aging studies

**Implementation:** `scripts/features_wearable.py`, `scripts/aging_features_batch.py`

---

## Agent Deep Dive: RetinalAgent

**Data access:** `loaders/retinal.py` → 4 imaging modalities (CFP, OCT, OCTA, FLIO)

**Concrete problems it solves:**

1. **Retinal aging clock via RETFound** -- frozen ViT-Large embeddings (1,024-dim) from color fundus photography
   - 2,274 participants processed on NVIDIA H200 GPU (2.6 img/s)
   - **MAE=6.0 years, R2=0.53** -- the single best aging clock in the entire system
   - A single fundus photo predicts chronological age better than any combination of lab values
   - Retinal age gap (RAG): +1y associated with higher mortality, CVD, dementia risk (Nusinovici 2022)

2. **Cross-modal retinal-metabolic coupling** -- does CGM glycemic variability predict retinal vascular damage?
   - MAGE → logMAR: rho=+0.07 (p<0.001) after adjusting for age AND HbA1c
   - Glucose variability has a small independent effect on vision beyond mean glycemia
   - This is novel: variability, not just mean glucose, matters for the eye

3. **Future: FLIO metabolic aging clock** -- fluorescence lifetime imaging captures AGE/lipofuscin accumulation
   - 1,847 participants (81% coverage), 256x256x1024 per file
   - No FLIO aging clock exists in the literature -- metabolic retinal aging before structural damage

**Implementation:** `scripts/retinal_age.py` (RETFound + fallback to ImageNet ViT-Large)

---

## Agent Deep Dive: CardiacAgent

**Data access:** `loaders/ecg.py` → 2,257 WFDB 12-lead ECGs (500 Hz, 11s)

**Concrete problems it solves:**

1. **Cardiac aging clock via ECGFounder** -- frozen RegNet-1D embeddings (1,024-dim) from 12-lead ECG
   - 2,251 participants, 16 ECG/s on H200 GPU
   - MAE=8.9y, R2=0.08 from embeddings
   - ECG-age gap: +7y associated with 62% higher mortality, 2x MACE risk (Lima *Nat Comms* 2021)

2. **Interval-based cardiac age (CPU fallback)** -- uses ecg_rate, PR, QRS, QT, QTc from manifest
   - MAE=8.9y from just 5 features -- comparable to the deep learning approach
   - Top feature: PR interval (coef=2.18) -- conduction slowing is a hallmark of cardiac aging

3. **HRV from ultra-short ECG** -- AI-READI ECGs are only 11 seconds
   - RMSSD validated for 10-sec strips (r=0.85 vs 5-min, Munoz 2015)
   - SDNN/LF/HF NOT reliable at this duration -- documented in domain memory

**Implementation:** `scripts/cardiac_age.py` (ECGFounder + interval fallback)

---

## Agent Deep Dive: EnvironmentAgent

**Data access:** `loaders/environment.py` → Anura sensor (PM2.5, 10 spectral channels, temp, humidity, VOC/NOx)

**Concrete problems it solves:**

1. **Environmental exposure aging clock (NOVEL)** -- no aging clock from personal environment data exists
   - Features: mean PM2.5, bright light hours, evening light exposure, temperature, temperature range
   - MAE=9.3y, r=0.15 -- weakest individual clock, but captures a unique aging axis
   - Orthogonal to clinical clocks -- environmental aging is not explained by lab values

2. **PM2.5 → Heart Rate causal analysis** -- lagged regression at 0-240 min lags
   - Tests whether personal air pollution exposure causes acute cardiovascular responses
   - Adjusts for time-of-day (Fourier terms) to remove circadian confounding
   - EPA AQI breakpoints updated May 2024: Good <= 9.0 ug/m3

3. **Circadian light exposure** -- spectral channels enable melanopic EDI estimation
   - Evening light (8pm-midnight) delays circadian phase → disrupts sleep → worsens glucose
   - Bright light hours during daytime support circadian entrainment
   - Brown et al. 2022: 250 lux melanopic EDI daytime threshold for alertness

**Implementation:** `scripts/aging_features_batch.py` (environment features), `scripts/causal_analysis.py`

---

## Agent Deep Dive: Reasoning Agents

<div class="columns"><div class="col">

**CausalAgent** -- designs and runs causal analyses
- Bidirectional Granger causality (sleep → glucose)
- Cross-correlation with optimal lag detection
- Lagged regression with time-of-day adjustment
- PCMCI causal graphs (tigramite)
- All run per-person, then aggregated to population level

**PhenotypeAgent** -- discovers data-driven subtypes
- Clusters participants by multi-dimensional AgeAccel profiles
- Identifies subtypes that cut across the 4 diabetes groups
- Concordant vs discordant agers
- UMAP/t-SNE visualization

**AgingClockAgent** -- coordinates clock training
- 13 system + 6 functional clocks
- Ridge regression with CV alpha selection
- AgeAccel residualization against chronological age
- Cross-dimensional concordance analysis

</div><div class="col">

**HypothesisAgent** -- generates testable hypotheses
- "GlucoseAgent found TIR differs by group. Hypothesis: insulin resistance mediates this. Test: compare TIR after adjusting for HOMA-IR."
- Links findings from different modality agents

**LiteratureAgent** -- provides domain context
- CGM consensus targets (Battelino 2023)
- Clinical thresholds and reference ranges
- Citation support for findings

**CriticAgent** -- validates every finding
- Was age adjusted? (almost everything correlates with age)
- Site bias check within UW/UCSD/UAB?
- FDR correction for multiple comparisons?
- Effect size (Cohen's d, eta-squared), not just p-value?
- Does analysis implicitly require sex? (redacted)

</div></div>

---

## Results: 15 Aging Clocks Trained

| Clock | Type | Input | Features | MAE | R2 | r |
|---|---|---|---|---|---|---|
| **Retinal (RETFound)** | Imaging | Fundus photo | 1024 | **6.0y** | 0.53 | 0.73 |
| Cardiovascular | System | SBP, DBP, HR, troponin, NTproBNP | 6 | 8.1y | 0.19 | 0.48 |
| Circadian | Functional | IS, IV, M10, L5, RA, cosinor | 8 | 8.8y | 0.11 | 0.33 |
| Autonomic | Functional | Resting/nocturnal/diurnal HR, dip | 4 | 8.8y | 0.09 | 0.31 |
| Physical | Functional | Daily steps, active calories | 2 | 8.9y | 0.10 | 0.32 |
| Cardiac (ECGFounder) | Imaging | 12-lead ECG waveform | 1024 | 8.9y | 0.08 | 0.28 |
| Immune | System | CRP, WBC, RBC, Hgb, platelets, RDW | 6 | 8.9y | 0.09 | 0.31 |
| Metabolic | System | HbA1c, glucose, TG, HDL, LDL, TC | 8 | 9.1y | 0.05 | 0.24 |
| Cognitive | System | MoCA total + 15 subscores | 16 | 9.1y | 0.07 | 0.28 |
| CGM metabolic | Functional | Mean glucose, CV, TIR, MAGE, GRI | 8 | 9.2y | 0.04 | 0.22 |
| Sleep | Functional | TST, SE, WASO, REM%, deep% | 6 | 9.2y | 0.03 | 0.18 |
| Environmental | Functional | PM2.5, light, temp | 5 | 9.3y | 0.02 | 0.15 |

**Novel clocks (first of their kind):** CGM metabolic age, Environmental exposure age

---

## Results: Multi-Modal Aging Clock (2,192 predictors -> age)

**Artifact-verified result:** `scripts/unified_clock.py` trains the current all-feature clock and writes `results/clocks/multimodal_clock_age_accel.parquet`, `results/clocks/multimodal_clock_performance.csv`, and `results/clocks/multimodal_clock_feature_importance.csv`.

**All raw numeric features and frozen embeddings, one model predicting age:**

| Run | Split | Preprocessing | Validation MAE | Test MAE | Test R2 | Test r |
|---|---|---|---:|---:|---:|---:|
| Primary | recommended_split | no clipping | 4.78y | 9.83y | -47.516 | 0.138 |
| Sensitivity | recommended_split | train-only winsorization | 4.67y | 5.17y | 0.664 | 0.815 |
| Sensitivity | balanced_split_v1 | no clipping | 4.74y | 5.10y | 0.397 | 0.696 |

**Leakage guardrails:**
- Predictor matrix excludes chronological age, split metadata, predicted-age outputs, and AgeAccel residuals.
- Missingness filtering, optional outlier clipping, imputation, scaling, and alpha selection are fit without test rows.
- Final performance is reported once on the held-out test split.

**Key finding:** Raw multimodal features and frozen retinal/ECG embeddings carry age signal without using residualized AgeAccel dimensions as predictors, but the no-clipping recommended-split run exposes a high-dimensional extrapolation failure. Treat clipped results as sensitivity analyses until the offending feature/participant patterns are audited.

---

## Results: Top Features Driving the Multi-Modal Clock

**Ridge coefficient importance from `multimodal_clock_feature_importance.csv`:**

| Rank | Feature | Relative importance |
|---:|---|---:|
| 1 | clinical_score__pulse_pressure | 0.70% |
| 2 | clinical__cesd_total | 0.62% |
| 3 | clinical_score__frailty_index | 0.49% |
| 4 | clinical__weight_kg | 0.43% |
| 5 | clinical__bmi | 0.39% |
| 6 | retinal__retinal_emb_902 | 0.37% |
| 7 | clinical__moca_memory1 | 0.36% |
| 8 | clinical__sbp | 0.35% |
| 9 | clinical__whr | 0.34% |
| 10 | multimodal__ecg_pr | 0.33% |

---

## Results: Cross-Dimensional Analysis

<div class="columns"><div class="col">

**Are aging dimensions independent?**
- Mean pairwise Spearman rho = 0.08
- Most organ systems age **largely independently**
- Cardiovascular-cardiac correlation highest (r=0.17)
- This supports the multi-dimensional approach -- a single aging clock misses organ-specific heterogeneity

**Aging subtypes (KMeans on 13 AgeAccel profiles):**
- 3 clusters identified (silhouette=0.095)
- Clusters partially align with diabetes severity but are NOT identical
- Some "metabolically healthy" individuals cluster with accelerated agers in non-metabolic dimensions

</div><div class="col">

**Diabetes severity gradient:**
- All 13 aging dimensions show significant gradient across the 4 study groups
- Steepest: metabolic and CGM clocks (as expected)
- Environmental and circadian clocks show shallower gradients -- partially orthogonal to diabetes staging

**Best discriminator of diabetes severity:**
| Measure | AUC (healthy vs insulin) |
|---|---|
| Frailty Index | **0.90** |
| Allostatic Load | 0.82 |
| KDM AgeAccel | 0.76 |

Composite deficit-counting measures outperform individual clocks for disease classification.

</div></div>

---

## Results: Causal Discovery from the 10-Day Window

The synchronized CGM + wearable + environment recording enables **within-person causal inference** impossible from cross-sectional snapshots alone.

**5a. Sleep → Glucose (Granger causality)**
For each participant: per-night sleep efficiency → next-day glucose TIR. Bidirectional test.
Aggregate: does the direction depend on diabetes severity?

**5b. Glucose-HR Coupling**
Cross-correlation on 5-min aligned grid. Optimal lag and coupling strength per person.
Hypothesis: weaker coupling in more severe diabetes (autonomic decoupling).

**5c. PM2.5 → Heart Rate**
Lagged regression at 0, 15, 30, 60, 120, 240 min. Adjusted for time-of-day.
Tests acute cardiovascular effect of personal air pollution exposure.

**5d. Population Causal DAG (PCMCI)**
Tigramite on 5 aligned variables (glucose, HR, PM2.5, temp, humidity).
Per-person DAGs aggregated to population-level structure.
Edges retained if present in >10% of participants.

> Currently running on all 2,280 participants. Results accumulating.

---

## Results: Digital Biomarkers

**6a. Wearable-only → HbA1c (no glucose data):**
R2=0.060, MAE=0.80%, AUROC=0.649

Top predictive wearable features:
- REM% (-0.16) -- less REM → higher HbA1c
- L5 activity (+0.08) -- higher nighttime activity → higher HbA1c
- Cosinor amplitude (-0.08) -- weaker circadian rhythm → higher HbA1c
- Intradaily variability (-0.07) -- more fragmented rhythm → higher HbA1c
- Nocturnal HR (+0.05) -- elevated nocturnal HR → higher HbA1c

> Modest but biologically meaningful: circadian disruption and sleep quality explain ~6% of HbA1c variance without any glucose measurement.

**6b. Heart Rate → Insulin Resistance:**
Partial r=+0.246 (p=5.8e-32), adjusting for age+BMI. Consistent across all 4 study groups.

**6c. CGM Variability → Visual Acuity:**
MAGE → logMAR: rho=+0.07 (p<0.001) after adjusting for age AND HbA1c.
Glucose variability has an independent effect on vision beyond mean glycemia.

---

## The 10-Day Window: What Longitudinal Inference It Enables

The ~10-day continuous window is NOT longitudinal aging data (single visit). But it enables powerful analyses that snapshots cannot:

**1. Temporal dynamics as aging biomarkers**
- Circadian amplitude, regularity, phase stability -- degradation reflects ANS aging
- Glucose variability patterns (dawn phenomenon, nocturnal instability) -- reflect metabolic aging dynamics
- Sleep architecture stability night-to-night -- reflects homeostatic resilience

**2. Cross-modal coupling as a health signature**
- Tight glucose-HR coupling = intact autonomic regulation
- Loose coupling = possible neuropathy/autonomic dysfunction
- Sleep quality → next-day glucose → daytime activity → next-night sleep: the full loop

**3. Environmental exposure-response curves per person**
- Personal dose-response: does THIS person's HR rise with PM2.5?
- Light exposure → sleep timing → glucose control mediation chain
- Temperature variability → stress response → HRV impact

**4. Individual deviation from population norms**
- "Participant 1046: circadian amplitude 2 SD below age-matched controls, but glucose control is average"
- Identifies compensated vs decompensated systems

---

## Vision: N-of-1 Trial Suggestions via Longevity OS

**From population analysis → individual intervention:**

```
  AI-READI population analysis (Layer 2)
            │
            ▼
  Per-person multi-organ aging profile
  (15 AgeAccel dimensions + cross-modal coupling scores)
            │
            ▼
  Longevity OS (Layer 3)
  ┌──────────────────────────────────────────────────┐
  │  Imperial Physician Orchestrator                  │
  │  "Participant 1046:                              │
  │   - Circadian age +4y (RA=0.32, IS=0.28)        │
  │   - Sleep age +3y (SE=72%, REM=14%)              │
  │   - Cardiovascular age normal                    │
  │   - CGM metabolic age +2y (CV=38%, dawn=+22mg)   │
  │                                                  │
  │  Recommended N-of-1 trial:                       │
  │   Intervention: Morning bright light (10K lux,   │
  │     30 min within 1h of waking) + evening light  │
  │     restriction (blue-blocking after 8pm)        │
  │   Primary endpoint: Circadian RA change          │
  │   Secondary: Sleep SE, next-day TIR              │
  │   Duration: 2 weeks on / 2 weeks off / 2 on     │
  │   Analysis: Bayesian STS + ITS"                  │
  └──────────────────────────────────────────────────┘
```

The 9 Longevity OS domain agents (diet, exercise, metrics, biomarkers, supplements, trial monitor, trial design, safety review, reports) generate personalized, evidence-based interventions targeting the specific aging dimensions where the individual is accelerated.

---

## Vision: Test-Time Training with Agents

**The TextGrad paradigm applied to aging physiology:**

Current system: Foundation models (RETFound, ECGFounder) are frozen. Agents operate on fixed embeddings.

**Future: Agents as gradient signals for model improvement.**

```
  User provides new data (Garmin + CGM + labs)
            │
            ▼
  Foundation model predicts aging profile
            │
            ▼
  Agent system evaluates predictions:
  ┌────────────────────────────────────────────────┐
  │ CriticAgent: "Retinal age prediction conflicts │
  │ with this person's clinical trajectory.        │
  │ The model may be miscalibrated for this        │
  │ phenotype (high myopia + low HbA1c)."          │
  │                                                │
  │ → Generate natural language gradient:           │
  │   "The retinal encoder overweighs myopic       │
  │    refractive changes as aging. Reduce          │
  │    sensitivity to refractive features."         │
  └───────────────────────┬────────────────────────┘
                          │
            ▼ (TextGrad-style backprop)
  Foundation model fine-tuned via:
  1. LoRA adapter update from agent feedback
  2. Prompt/representation adjustment
  3. Calibration layer correction
            │
            ▼
  Improved predictions for this user AND future similar phenotypes
```

**Three modes of test-time adaptation:**
1. **Calibration** -- agent detects systematic bias for a subpopulation, adjusts predictions
2. **Personalization** -- with 10 days of user data, fine-tune adapters for individual physiology
3. **Discovery** -- agent identifies novel phenotypes the training data didn't represent, flags for human review and model update

---

## Vision: The Full Adaptive Loop

```
  ┌─────────────────────────────────────────────────────────────────┐
  │                    POPULATION LEARNING                          │
  │  AI-READI (2,280) + future cohorts → pretrain/fine-tune FMs    │
  └──────────────────────────┬──────────────────────────────────────┘
                             │
                             ▼
  ┌─────────────────────────────────────────────────────────────────┐
  │                    INDIVIDUAL INFERENCE                         │
  │  New user's 10-day data → frozen FM → aging profile            │
  │  Agent system → interprets, validates, identifies anomalies    │
  └──────────────────────────┬──────────────────────────────────────┘
                             │
                             ▼
  ┌─────────────────────────────────────────────────────────────────┐
  │                    PERSONALIZED INTERVENTION                    │
  │  Longevity OS → N-of-1 trial suggestion based on aging profile │
  │  User executes intervention → new data generated               │
  └──────────────────────────┬──────────────────────────────────────┘
                             │
                             ▼
  ┌─────────────────────────────────────────────────────────────────┐
  │                    TEST-TIME ADAPTATION                         │
  │  Agent evaluates intervention outcome:                         │
  │  "Bright light therapy improved RA by 0.08 in 2 weeks"        │
  │  → TextGrad signal to FM: strengthen circadian-light coupling  │
  │  → Updated model better serves this phenotype                  │
  │  → Aggregated across users: population model improves          │
  └─────────────────────────────────────────────────────────────────┘
```

**Key insight:** The agent system is not just an inference wrapper -- it generates training signal. Each user interaction is a mini-experiment that refines both the foundation model and the agent's reasoning.

---

## Future Directions

<div class="columns"><div class="col">

**Near-term (next 3 months):**

1. **Cross-modal JEPA training** -- mask one modality, predict from others. 2,280 participants sufficient for alignment (not from-scratch pretraining). Curriculum: SFT grounding → JEPA dynamics.

2. **FLIO metabolic aging clock** -- no FLIO aging clock exists. Fluorescence lifetime captures AGE/lipofuscin before structural damage.

3. **OCTA vascular aging** -- vessel density, FAZ area, fractal dimension → vascular age. Cross-validate with retinal fundus age.

4. **Full causal DAG** -- population-level causal structure from PCMCI on all 2,280 participants. Sleep-glucose-HR-environment network.

5. **ECG HRV features** -- R-peak detection (neurokit2), RMSSD from 11s ECG, integrate with wearable HR for complementary autonomic assessment.

</div><div class="col">

**Medium-term (6-12 months):**

6. **Longevity OS integration** -- bridge population aging profiles to individual intervention suggestions. Bayesian N-of-1 trial design from agent system.

7. **Test-time training** -- TextGrad-style adaptation where agent feedback becomes gradient signal for model fine-tuning. LoRA adapters personalized per phenotype.

8. **Longitudinal follow-up** -- AI-READI Year 4 will add ~10% longitudinal data. Validate aging clocks as predictors of disease progression.

9. **Signal-level LongevityBench** -- a benchmark for wearable + imaging + clinical aging biology, complementing the omics-focused original.

10. **External validation** -- apply clocks to UK Biobank wearable + imaging data, All of Us CGM data.

</div></div>

---

## Summary

**What we built:** A complete computational infrastructure for multi-dimensional biological aging analysis from 9 simultaneously-measured modalities in 2,280 adults across the diabetes spectrum.

**What's novel:**
- First CGM metabolic aging clock and environmental exposure aging clock
- First multi-modal aging clock integrating EHR + CGM + wearable + retinal + ECG + environment (saved artifact MAE=5.2y; training script provenance should be restored before publication claims)
- Multi-agent system grounded in computed features (not LLM parametric knowledge)
- Causal discovery from synchronized 10-day multimodal time series

**Key numbers:**

| Metric | Value |
|---|---|
| Modalities integrated | 9 |
| Aging dimensions | 15 |
| Best single clock (retinal) | MAE=6.0y, R2=0.53 |
| Multi-modal clock | Primary no-clipping run currently fails from extrapolation; clipped sensitivity MAE=5.17y, R2=0.664 |
| Features computed per person | 2,192 all-feature clock predictors (clinical, CGM/wearable/environment, retinal embeddings, ECG embeddings) |
| Python infrastructure | 18 modules, ~4,000 lines |
| Agent system | 11 agents, 5 task pipelines |
| Paper figures | 12 publication-quality |

**Target venues:** Nature Medicine / Nature Aging / Cell

---

## References

<div class="small">

**Multi-organ aging:** Oh et al. *Nature* 2023;624:164 (proteomic organ clocks) | Tian/Wen et al. *Nat Aging* 2024 (9-system organ ages) | MRI multi-organ *Nat Med* 2025

**Foundation models:** Zhou et al. *Nature* 2023 (RETFound) | Li et al. *NEJM AI* 2025 (ECGFounder) | Assran/LeCun CVPR 2023 (I-JEPA) | JETS (Empirical Health, wearable JEPA) | SMB-Structure 2025 (EHR JEPA)

**Agent systems:** Liu/Zou et al. 2026 (CEREBRA) | Wei et al. *Nat Comms* 2025 (PHIA) | Swanson et al. *Nature* 2025 (Virtual Lab) | BioMedAgent *Nat BME* 2026 | ClockBase Agent (Gladyshev 2025)

**Aging clocks:** Levine *Aging* 2018 (PhenoAge) | Klemera-Doubal 2006 (KDM) | CosinorAge *npj Dig Med* 2024 | Lima *Nat Comms* 2021 (ECG-Age) | Nusinovici *Age Ageing* 2022 (retinal age)

**CGM/wearable:** Battelino et al. *Lancet Diabetes* 2023 (CGM consensus) | SleepFM *Nat Med* 2026 | PpgAge *Nat Comms* 2025

**Benchmarks:** LongevityBench (Insilico 2026) -- LLMs score 0.48-0.54 on aging biology

**Dataset:** AI-READI v3.0.0, doi:10.60775/fairhub.3, NCT06002048

</div>
