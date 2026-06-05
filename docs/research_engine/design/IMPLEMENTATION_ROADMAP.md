# Implementation Roadmap: Multi-Dimensional Aging Clock Study

> **Status:** Historical implementation roadmap. Many phases are now implemented
> in `scripts/`, `agents/`, `hypothesis_driven/`, and `foundation_jepa*`.
> For current status and remaining gaps, see `docs/CURRENT_STATUS.md`.
> **Date:** 2026-04-24
> **Prerequisites:** Data infrastructure (done), agent system (done), verification (done)

---

## Overview

Three types of work, interleaved:
1. **Batch feature computation** — loop over 2,280 participants, compute features → Parquet files. Direct Python scripts, not agent-mediated. Run as SLURM jobs.
2. **Clock training** — Ridge/ElasticNet regression, train/test evaluation. Direct Python scripts.
3. **Analysis & interpretation** — statistical comparisons, clustering, causal discovery, synthesis. Agent-mediated for reasoning quality.

---

## Phase 1: Clinical Composite Scores (2-3 days)
*No training, formula-based. Immediate value.*

### What to build: `scripts/aging_scores.py`

Compute for all 2,280 participants:

| Score | Formula | Inputs | Notes |
|---|---|---|---|
| **KDM biological age** | Klemera-Doubal weighted regression | albumin, ALP, BUN, creatinine, CRP, HbA1c, total cholesterol, SBP | Retrain on AI-READI (BioAge R approach adapted to Python) |
| **Homeostatic dysregulation** | Mahalanobis distance from healthy-young centroid | Same biomarkers as KDM | Reference: healthy group, age 40-55 |
| **Allostatic load** | Sum of binary risk flags | SBP>140, DBP>90, HR>80, HbA1c>5.7, TC>240, HDL<40, TG>150, BMI>30, WHR>0.90, CRP>3, creatinine>1.2, albumin<3.5 | 12 biomarkers, all available |
| **Frailty index** | Deficit accumulation / total deficits | 30+ conditions + abnormal labs + CES-D≥10 + MoCA<26 + neuropathy | Follow Theou 2023 10-step guide |
| **HOMA-IR** | (insulin_µU × glucose_mg) / 405 | insulin (convert ng/L ÷ 0.04034), glucose | With insulin unit correction |
| **TyG index** | ln(TG × glucose) / 2 | triglycerides, glucose | /2 OUTSIDE the ln |
| **QUICKI** | 1 / (log₁₀(insulin_µU) + log₁₀(glucose)) | insulin (converted), glucose | |
| **Pulse pressure** | SBP - DBP | sbp, dbp | Vascular stiffness marker |
| **UACR** | urine_albumin / urine_creatinine | urine markers | Albuminuria staging |

**Output:** `results/features/clinical_scores.parquet` — 2,280 rows × ~10 score columns

### What to build: `scripts/aging_features_batch.py`

Batch-compute per-person features from continuous monitoring (SLURM job):

```
For each participant (2,280):
  CGM features:    mean, CV, TIR(5-level), MAGE, GRI, LBGI/HBGI, GMI,
                   dawn_phenomenon, nocturnal_mean, nocturnal_CV
  Wearable:        circadian IS/IV/M10/L5/RA/cosinor,
                   sleep (mean SE, TST, WASO, REM%, Deep%),
                   HR (resting, nocturnal dip, day/night means),
                   activity (daily steps, active cal)
  Environment:     daily PM2.5 mean, bright light hours (lch2>threshold),
                   evening light, screen hours, temp mean/range
  Cardiac:         ECG Rate, QTc, PR, QRS (from manifest — no signal processing)
```

**Output:** `results/features/multimodal_features.parquet` — 2,280 rows × ~60 feature columns

**Runtime estimate:** CGM metrics ~1 sec/person, wearable features ~2-3 sec/person (circadian metrics are the bottleneck). Total: ~2 hours for all 2,280. Can parallelize with SLURM array job.

---

## Phase 2: System-Specific Clocks (1 week)
*Ridge regression on train split, evaluate on test.*

### What to build: `scripts/aging_clocks.py`

For each system, train age prediction:

| System | Features | Expected MAE |
|---|---|---|
| **Immune/inflammatory** | CRP, WBC, RBC, hemoglobin, platelets, RDW | ~8-10y |
| **Metabolic (labs)** | HbA1c, glucose, HOMA-IR, TyG, TG, HDL, LDL, TC | ~6-8y |
| **Renal** | creatinine, BUN, BUN/Cr, urine albumin, UACR, Na, K, Cl, CO2, Ca | ~8-10y |
| **Hepatic** | ALT, AST, ALP, bilirubin, albumin, globulin, total protein, AG ratio | ~9-11y |
| **Cardiovascular** | SBP, DBP, pulse pressure, HR, troponin T, NT-proBNP | ~7-9y |
| **Hematologic** | RDW, MCV, MCH, MCHC, hemoglobin, hematocrit, RBC, WBC, platelets | ~8-10y |
| **Cognitive** | MoCA total + 15 subscores | ~10-12y (MoCA is a coarse measure) |

Method per system:
1. Standardize features (StandardScaler fit on train only)
2. Handle missing: drop if >30% missing, else median impute (fit on train)
3. Ridge regression (alpha via 5-fold CV on train split, n=1576)
4. Evaluate on test split (n=352): MAE, R², Pearson r
5. AgeAccel = predicted - actual (residualize against age to center at 0)

### Also train functional clocks from Phase 1 features:

| Clock | Features (from multimodal_features.parquet) | Novel? |
|---|---|---|
| **Circadian age** | IS, IV, M10, L5, RA, cosinor amplitude/acrophase/mesor | Adapts CosinorAge |
| **CGM metabolic age** | mean glucose, CV, TIR, MAGE, GRI, dawn phenomenon, nocturnal metrics | **NOVEL** |
| **Autonomic age** | resting HR, nocturnal HR dip, day/night HR means | Adapts PpgAge concept |
| **Sleep age** | mean SE, TST, WASO, REM%, Deep%, night-to-night variability | |
| **Physical age** | daily steps, active calories | |
| **Environmental age** | daily PM2.5, bright light hours, evening light, temp variability | **NOVEL** |

**Output:** `results/clocks/age_accel.parquet` — 2,280 rows × ~13 AgeAccel columns (7 system + 6 functional)

---

## Phase 3: Cross-Dimensional Analysis (1 week)
*The core scientific analysis. Agent-mediated for interpretation.*

### 3a. Concordance Matrix

```python
# Correlation matrix of all AgeAccel dimensions
corr = age_accel_df.corr(method='spearman')
# → Which systems age together? Which are independent?
```

### 3b. Per-Person Concordance Score

```python
# For each person: SD of their AgeAccels across all dimensions
concordance = age_accel_df.std(axis=1)
# Low SD = concordant (all organs aging similarly)
# High SD = discordant (some fast, some slow)
```

### 3c. Aging Subtypes (PhenotypeAgent)

```python
# Cluster by AgeAccel profile
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

# Try k=3,4,5,6
for k in [3,4,5,6]:
    km = KMeans(n_clusters=k).fit(age_accel_scaled)
    print(f'k={k}: silhouette={silhouette_score(age_accel_scaled, km.labels_):.3f}')

# Characterize best clustering
# → Per-cluster: which AgeAccel dimensions are highest/lowest?
# → Chi-squared test: do clusters align with study_group?
```

### 3d. Diabetes Severity Gradient

```python
# For each AgeAccel dimension: compare across 4 study groups
# → Which dimension shows the steepest diabetes gradient?
# → Which dimensions are orthogonal to diabetes severity?
```

### 3e. Predictive Hierarchy

```python
# Which AgeAccel best predicts:
# 1. Clinical diabetes severity (study_group ordinal regression)
# 2. Allostatic load (linear regression)
# 3. Cross-modal discordance (regression on concordance score)
```

**Run via:** Agent system — `python -m agents --task aging_clocks` after features are computed, or direct scripts for faster iteration.

---

## Phase 4: Imaging Clocks (2-3 weeks, GPU needed)
*Depends on SLURM GPU allocation.*

### 4a. Retinal Age (RETFound)

```bash
# 1. Download RETFound weights
# 2. Extract fundus images for all participants with CFP
# 3. Preprocess to 224x224
# 4. Extract frozen RETFound embeddings (GPU batch job)
# 5. Train linear age regression head on train split
# 6. Compute retinal AgeAccel
```

**Script:** `scripts/retinal_age.py` + `configs/retinal_age.slurm`
**Input:** CFP DICOM files (93,920 photography files, ~2,186 participants)
**Output:** `results/embeddings/retinal_embeddings.parquet` + retinal AgeAccel added to `age_accel.parquet`

### 4b. Cardiac Age (ECGFounder)

```bash
# 1. Download ECGFounder weights
# 2. Load 12-lead ECG, preprocess (highpass, notch, z-score per lead)
# 3. Extract frozen embeddings (GPU batch job, fast — 11s signals)
# 4. Train linear age regression head
# 5. Compute cardiac AgeAccel
```

**Script:** `scripts/cardiac_age.py` + `configs/cardiac_age.slurm`
**Input:** 2,257 WFDB ECG recordings
**Output:** `results/embeddings/cardiac_embeddings.parquet` + cardiac AgeAccel

### 4c. Re-run Phase 3 with imaging clocks added

After adding retinal + cardiac AgeAccel, redo concordance matrix, clustering, and gradient analysis with the full ~15 dimensions.

---

## Phase 5: Causal Discovery (2 weeks)
*Can run in parallel with Phase 4.*

### 5a. Sleep → Glucose Causality

```python
# For each participant with CGM + wearable overlap:
#   1. Segment nights (compute_sleep_architecture)
#   2. Segment daily CGM (per-day TIR, CV, mean)
#   3. Test bidirectional Granger causality (sleep_efficiency → next_day_TIR)
#   4. Aggregate: how many show significant sleep→glucose vs glucose→sleep?
#   5. Stratify by study_group
```

### 5b. Glucose-HR Coupling

```python
# For each participant:
#   1. Load aligned_timeseries (5-min grid)
#   2. Compute cross-correlation between glucose and HR
#   3. Find optimal lag
#   4. Compare coupling strength across study groups
```

### 5c. PM2.5 → HR

```python
# For each participant:
#   1. Load aligned_timeseries
#   2. Lagged regression: PM2.5(t) → HR(t+lag)
#   3. Adjust for time-of-day
#   4. Aggregate across participants
```

### 5d. Causal DAG

```python
# Using tigramite/PCMCI on aligned time series:
#   Variables: glucose, HR, sleep, activity, PM2.5, temperature, light
#   Run PCMCI with ParCorr test
#   Aggregate per-person DAGs into a population-level causal structure
```

**Script:** `scripts/causal_analysis.py`
**Output:** `results/causal/causal_summary.json` + per-question summary tables

---

## Phase 6: Digital Biomarkers (1-2 weeks)
*Can run after Phase 2 features are computed.*

### 6a. Wearable → HbA1c Prediction

```python
# Features: circadian + sleep + HR + activity metrics
# Target: HbA1c (from feature matrix)
# Model: ElasticNet on train, evaluate on test
# Report: R², MAE, AUROC for HbA1c ≥ 6.5
# Feature importance: which wearable features matter most?
```

### 6b. Circadian Disruption → Insulin Resistance

```python
# Partial correlation: RA vs HOMA-IR, adjusting for age + BMI
# Also: IS vs HOMA-IR, cosinor_amplitude vs HOMA-IR
# Stratify by study_group
```

### 6c. CGM Variability → Visual Acuity (retinal proxy)

```python
# Spearman correlation: CV, MAGE vs logMAR (adjusting for age)
# → Proxy for CGM → retinal damage until OCTA vessel density available
```

---

## Phase 7: Unified Multimodal Clock + Final Analysis (1-2 weeks)
*Depends on all previous phases.*

### 7a. Level 5 Unified Clock

```python
# Input: all AgeAccel values as features (13-15 dimensions)
# Model: stacked Ridge or gradient boosting → age
# Feature importance: which dimension contributes most to unified aging?
# Compare unified AgeAccel vs PhenoAge/KDM vs allostatic load
```

### 7b. Final Cross-Modal Insights (Agent-mediated)

Run through orchestrator:
- Cardiac-metabolic coupling
- Circadian-metabolic alignment
- Cross-modal discordance phenotypes
- Environment-physiology associations
- Sleep-glucose-vision triad (mediation analysis)

### 7c. Paper Figures & Tables

Agent-assisted generation of:
- Table 1: Cohort demographics by study group
- Fig 1: Multi-dimensional aging architecture diagram
- Fig 2: Cross-organ AgeAccel correlation matrix (heatmap)
- Fig 3: Aging subtypes (UMAP + cluster labels, colored by study group)
- Fig 4: Diabetes severity gradient per aging dimension (forest plot)
- Fig 5: Causal DAG (sleep-glucose-HR-environment network)
- Fig 6: Digital biomarker prediction (wearable → HbA1c ROC curve)

---

## Timeline Summary

| Phase | What | Duration | Depends On | Compute |
|---|---|---|---|---|
| **1** | Clinical scores + batch feature computation | 2-3 days | Nothing | CPU (SLURM) |
| **2** | System + functional clocks (Ridge training) | 1 week | Phase 1 | CPU |
| **3** | Cross-dimensional analysis | 1 week | Phase 2 | CPU + Agent system |
| **4** | Imaging clocks (RETFound, ECGFounder) | 2-3 weeks | Phase 1 | **GPU** (SLURM) |
| **5** | Causal discovery | 2 weeks | Phase 1 | CPU (SLURM) |
| **6** | Digital biomarkers | 1-2 weeks | Phase 2 | CPU |
| **7** | Unified clock + final analysis | 1-2 weeks | All above | CPU + Agent |

**Phases 4, 5, 6 can run in parallel** after Phase 2.
**Total: ~6-8 weeks** if parallelized, ~10-12 weeks sequential.

---

## Files to Create

| File | Phase | Purpose |
|---|---|---|
| `scripts/aging_scores.py` | 1 | KDM, allostatic load, frailty index, HOMA-IR, TyG, QUICKI |
| `scripts/aging_features_batch.py` | 1 | Batch per-person multimodal feature computation |
| `configs/feature_batch.slurm` | 1 | SLURM job for batch features |
| `scripts/aging_clocks.py` | 2 | Train all Ridge regression clocks, compute AgeAccel |
| `scripts/cross_dimensional.py` | 3 | Concordance, clustering, diabetes gradient |
| `scripts/retinal_age.py` | 4 | RETFound embedding extraction + age head |
| `scripts/cardiac_age.py` | 4 | ECGFounder embedding extraction + age head |
| `configs/retinal_age.slurm` | 4 | GPU SLURM job |
| `configs/cardiac_age.slurm` | 4 | GPU SLURM job |
| `scripts/causal_analysis.py` | 5 | Granger, cross-correlation, PCMCI, mediation |
| `scripts/biomarker_prediction.py` | 6 | Wearable→HbA1c, circadian→IR, CGM→retinal |
| `scripts/unified_clock.py` | 7 | Level 5 unified multimodal clock |
| `notebooks/aging_atlas.ipynb` | 7 | Figures and tables for paper |

---

## What to Build First

**Start with Phase 1** — it's the foundation everything else depends on, needs no GPU, and produces immediate results (aging scores + multimodal features for all 2,280 participants).

Specifically, the first two scripts to write:
1. `scripts/aging_scores.py` — formula-based clinical scores
2. `scripts/aging_features_batch.py` — batch per-person CGM/wearable/environment features
