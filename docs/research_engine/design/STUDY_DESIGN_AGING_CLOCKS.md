# Study Design: Multi-Dimensional Biological Aging Across the Diabetes Spectrum

> **Working title:** "A Multi-Dimensional Biological Aging Atlas from Multimodal Functional Signals in 2,280 Adults Across the Diabetes Spectrum"
>
> **Dataset:** AI-READI v3.0.0 (2,280 participants, 4 diabetes severity groups, 9 modalities)
>
> **Target venues:** Nature Medicine / Nature Aging / Cell

---

## 1. The Central Question

**Do different dimensions of biological aging progress independently or in concert, and how does diabetes alter this landscape?**

No existing study has measured biological aging across this many dimensions — EHR, continuous glucose dynamics, circadian rhythms, cardiac electrophysiology, retinal imaging, and environmental exposure — in the same individuals.

---

## 2. Five Levels of Aging Clocks

### Level 1: Established Composite Scores (formula-based, no training)

These are directly computable from AI-READI's feature matrix using published formulas.

| Clock | Method | Biomarkers | Code | Notes |
|---|---|---|---|---|
| **PhenoAge** | Gompertz mortality model (Levine 2018) | albumin, creatinine, glucose, CRP, **lymphocyte %**, MCV, RDW, ALP, WBC | [BioAge R](https://github.com/dayoonkwon/BioAge) | **BLOCKED: lymphocyte % NOT in AI-READI CBC** (no WBC differential). Use modified PhenoAge without lymph% or use KDM instead |
| **KDM Biological Age** | Weighted linear combination (Klemera-Doubal 2006) | albumin, ALP, BUN, creatinine, CRP, HbA1c, total cholesterol, SBP | [BioAge R](https://github.com/dayoonkwon/BioAge) | All biomarkers available |
| **Homeostatic Dysregulation** | Mahalanobis distance from "healthy young" centroid | Any biomarker panel | [BioAge R](https://github.com/dayoonkwon/BioAge) | Define reference: healthy group, age 40-50 |
| **Allostatic Load** | Sum of binary high-risk flags (Seeman 2001) | SBP, DBP, HR, HbA1c, total chol, HDL, TG, BMI, WHR, CRP, creatinine, albumin | Manual (trivial) | 10-12 biomarkers, all available |
| **Frailty Index** | Deficit accumulation (Rockwood; Theou 2023) | 30+ deficits: conditions (30 booleans) + abnormal labs + depression + neuropathy + cognitive | Manual | 30+ deficits easily constructable |

**DATA QUALITY ISSUES FOUND (2026-04-24 verification):**
- **Lymphocyte % not available:** AI-READI CBC lacks WBC differential. PhenoAge requires it. Use KDM as primary composite instead, or compute modified PhenoAge omitting lymphocyte %.
- **Insulin unit mislabel:** Raw data stores insulin as "ng/L" but values are consistent with conversion from µU/mL (median 0.6 ng/L ÷ 0.04034 = 14.9 µU/mL, matching expected fasting insulin). For HOMA-IR: convert insulin from ng/L to µU/mL by dividing by 0.04034. Reference range in CSV (0-24.9) was NOT converted — still in µU/mL.
- **C-peptide same issue:** Labeled ng/L, but median 2.57 matches ng/mL normal range (0.8-3.1). Likely ng/mL mislabeled as ng/L.
- **CRP is in mg/L** (confirmed). PhenoAge formula uses ln(CRP) where CRP is in mg/dL — divide by 10.
- **Albumin is in g/dL** (confirmed). PhenoAge needs g/L — multiply by 10.
- **Creatinine is in mg/dL** (confirmed). PhenoAge needs µmol/L — multiply by 88.4.
- **Glucose is in mg/dL** (confirmed). PhenoAge needs mmol/L — divide by 18.0182.

**Implementation:** KDM, allostatic load, and frailty index can be computed in ~1 day. PhenoAge requires modified formula. HOMA-IR/QUICKI/TyG require insulin unit correction.

### Level 2: System-Specific Clocks (from clinical labs)

Train per-system age regression models using AI-READI data. Follow the Tian et al. (Nature Aging 2024) approach: cross-validated Ridge/SVM on system-specific biomarkers.

| System | Features from AI-READI | Method |
|---|---|---|
| **Immune/Inflammatory** | CRP, WBC, RBC, hemoglobin, platelets, RDW | Ridge regression → age |
| **Metabolic** | HbA1c, glucose, insulin, HOMA-IR, TyG, triglycerides, HDL, LDL, total cholesterol | Ridge regression → age |
| **Renal** | Creatinine, BUN, BUN/Cr ratio, urine albumin, UACR, sodium, potassium, chloride, CO2, calcium | Ridge regression → age |
| **Hepatic** | ALT, AST, ALP, bilirubin, albumin, globulin, total protein, AG ratio | Ridge regression → age |
| **Cardiovascular** | SBP, DBP, pulse pressure, HR, troponin T, NT-proBNP | Ridge regression → age |
| **Hematologic** | RDW, MCV, MCH, MCHC, hemoglobin, hematocrit, RBC, WBC, platelets | Ridge regression → age |
| **Cognitive** | MoCA total + 15 subscores | Ridge regression → age |

**7 system clocks** from clinical data alone. Tian et al. built 9 systems but required MRI (brain) and spirometry (pulmonary), which AI-READI lacks.

**Implementation:** AgingClockAgent trains each on train split (1576), evaluates on test (352). Report MAE and R² per system.

### Level 3: Functional/Behavioral Clocks (from continuous monitoring)

These leverage the ~10-day continuous multimodal window — unique to AI-READI.

| Clock | Features | Adapt From | Code |
|---|---|---|---|
| **Circadian Age** | IS, IV, M10, L5, RA, cosinor amplitude/acrophase/mesor from Garmin HR/activity | CosinorAge (npj Dig Med 2024) | [CosinorAge Python](https://github.com/ADAMMA-CDHI-ETH-Zurich/CosinorAge) |
| **Metabolic Dynamics Age** | TIR, CV, MAGE, dawn phenomenon, nocturnal glucose mean/CV, AGP shape, GRI, LBGI/HBGI | **NOVEL — no CGM aging clock exists** | Build from scratch (Ridge on CGM features → age) |
| **Autonomic Age** | Resting HR, nocturnal HR dip, RMSSD (if neurokit2), HR recovery proxy | PpgAge approach (Nature Comms 2025) | Adapt method (different sensor) |
| **Sleep Age** | TST, SE, WASO, REM%, Deep%, night-to-night variability, sleep midpoint | SleepFM concept (Nature Med 2026) | Build from features (not raw signals) |
| **Physical/Fitness Age** | Daily steps, active minutes, sedentary time, peak cadence | Activity-based aging (UK Biobank studies) | Ridge on activity features → age |
| **Environmental Exposure Age** | Cumulative PM2.5 dose, bright light hours, evening light, circadian light disruption score, temperature variability | **NOVEL — no environmental aging clock exists** | Build from scratch |

**6 functional clocks**, 2 of which are novel (CGM metabolic dynamics, environmental exposure).

**Implementation:** WearableAgent computes circadian + sleep + activity features. GlucoseAgent computes CGM features. EnvironmentAgent computes exposure features. AgingClockAgent trains all clocks.

### Level 4: Imaging/Signal-Based Clocks

Deep learning on raw signals/images.

| Clock | Data | Adapt From | Public Weights? |
|---|---|---|---|
| **Retinal Age** | Fundus photography (CFP) | RETFound (Nature 2023) + age regression head | [Yes — GitHub](https://github.com/rmaphoh/RETFound_MAE) |
| **Retinal Age (multimodal)** | OCT + fundus | Ludwig et al. (Sci Reports 2026) multimodal retinal clock | Method published |
| **Cardiac Electrical Age** | 12-lead ECG waveform | ECGFounder (NEJM AI 2025) or Lima (Nature Comms 2021) ECG-Age | Checking availability |
| **Vascular Age** | OCTA enface images | Vessel density + FAZ age regression | Build from OCTA features |
| **FLIO Metabolic Age** | Fluorescence lifetime maps | **NOVEL — no FLIO aging clock exists** | Build from scratch |

**5 imaging clocks**, 1 novel (FLIO).

**Implementation:** RetinalAgent loads manifests and images. GPU jobs for embedding extraction (RETFound, ECGFounder). AgingClockAgent trains age heads.

### Level 5: Unified Multimodal Clock

Combine ALL levels into one model.

**Approach:**
1. Collect per-person raw numeric features across clinical labs/vitals, CGM, wearable, environment, clinical-score summaries, and frozen retinal/ECG embeddings.
2. Exclude chronological age, split metadata, predicted-age outputs, and AgeAccel residuals from the predictor matrix.
3. Tune the age model on training rows, inspect validation performance, then refit on train+validation and evaluate once on the held-out test split.
4. The residual = **Unified Biological AgeAccel** — computed after age prediction, not used as a predictor for the clock.

**This is the first multimodal aging clock integrating EHR + CGM + wearable + retinal + ECG + environment.**

---

## 3. Cross-Dimensional Analysis (The Core Novelty)

### 3.1 Concordance Matrix

For each participant, compute AgeAccel across all dimensions. Build the N × N correlation matrix of AgeAccels.

Key questions:
- Do immune and metabolic aging correlate? (Inflammaging theory predicts yes)
- Does circadian aging track autonomic aging? (Both reflect ANS health)
- Does retinal aging predict renal aging? (Microvascular hypothesis)
- Which pairs are most discordant?

### 3.2 Aging Subtypes

Cluster participants by their multi-dimensional AgeAccel profile (PhenotypeAgent).

Hypothesized subtypes:
- **Concordant slow agers:** All dimensions younger than expected. Who are they?
- **Concordant fast agers:** All dimensions older. Likely severe T2DM, but are there surprises?
- **Metabolic-accelerated:** Fast metabolic + CGM aging, normal other dimensions. Pre-diabetes pattern?
- **Vascular-accelerated:** Fast retinal + cardiovascular, normal metabolic. Hypertension-driven?
- **Circadian-disrupted:** Fast circadian + sleep aging, variable metabolic. Environmental exposure pattern?
- **Discordant:** Fast in some dimensions, slow in others. The most scientifically interesting.

### 3.3 Diabetes Severity Gradient

For each aging dimension, test whether AgeAccel increases across the 4 study groups.

Prediction: Some dimensions (metabolic, CGM) will show steep gradients. Others (circadian, environmental) may be orthogonal to diabetes severity — revealing aging axes that the clinical classification misses.

### 3.4 Predictive Hierarchy

Which aging dimension best predicts:
- Clinical diabetes severity? (Likely: metabolic system clock)
- Cross-modal discordance? (Unknown — this is discovery)
- Allostatic load? (Test: does the unified clock outperform PhenoAge?)

---

## 4. What's Directly Adaptable vs What's Novel

### Adaptable (published methods + code)

| What | From | Effort |
|---|---|---|
| PhenoAge formula | Levine 2018 / BioAge R package | 1 day |
| KDM biological age | Klemera-Doubal 2006 / BioAge R | 1 day |
| Allostatic load score | Seeman 2001 / NHANES implementations | 1 day |
| Frailty index | Rockwood / Theou 2023 10-step guide | 1-2 days |
| CosinorAge | ETH Zurich Python package | 2-3 days |
| System-specific clocks (Ridge on labs) | Tian et al. 2024 approach | 1 week |
| PCAge/LinAge retraining | Fong et al. 2024 | 2-3 days |
| Retinal age (RETFound probe) | Zhou et al. 2023 + age head | 1 week (GPU) |
| ECG-Age from intervals | Lima 2021 approach with feature-based proxy | 2-3 days |

### Novel (first-of-their-kind)

| What | Why It's New | Impact |
|---|---|---|
| **CGM metabolic dynamics clock** | No aging clock from CGM exists | First continuous glucose aging clock |
| **Environmental exposure clock** | No aging clock from personal environment data | First exposome-based aging clock |
| **FLIO metabolic aging clock** | FLIO + aging is unexplored | Retinal metabolic aging before structural damage |
| **Unified multimodal clock** | No clock combines EHR + CGM + wearable + retinal + ECG + environment | Most comprehensive aging model ever built |
| **Cross-dimensional concordance analysis in diabetes** | Tian et al. used MRI/proteomics, not functional signals | Scalable multi-system aging |
| **Aging subtypes beyond diabetes staging** | Existing subtypes are T2DM-defined | Data-driven aging phenotypes |

---

## 5. Agent System Workflow

### Phase 1: Compute Level 1 scores (immediate, no training)

```
ClinicalAgent → compute PhenoAge, KDM, allostatic load, frailty index
                for all 2,280 participants
Critic → validate computations (unit conversions, missing data handling)
```

### Phase 2: Train Level 2 system clocks (1-2 weeks)

```
ClinicalAgent → extract system-specific feature matrices
AgingClockAgent → train 7 Ridge regressions (train/test split)
                  compute per-system AgeAccel
Critic → validate each clock (MAE, R², no data leakage)
```

### Phase 3: Compute Level 3 functional clocks (2-3 weeks)

```
GlucoseAgent → compute per-person CGM feature vectors (all 2,245 with CGM)
WearableAgent → compute circadian + sleep + activity features (all 2,184 with wearable)
EnvironmentAgent → compute exposure features (all 2,231 with env data)
AgingClockAgent → train 6 functional clocks, compute AgeAccel
Critic → validate
```

### Phase 4: Imaging clocks (3-4 weeks, GPU needed)

```
RetinalAgent → extract RETFound embeddings from fundus (GPU job)
CardiacAgent → extract ECG embeddings or use interval-based clock
AgingClockAgent → train imaging-based age heads
```

### Phase 5: Unified model + cross-dimensional analysis (1-2 weeks)

```
AgingClockAgent → build Level 5 unified clock from raw features + frozen embeddings
PhenotypeAgent → cluster by multi-dimensional AgeAccel profile
HypothesisAgent → propose mechanisms for aging subtypes
CausalAgent → test which dimensions predict others
LiteratureAgent → contextualize findings
Critic → validate everything
```

---

## 6. Expected Outputs

1. **Per-participant aging profile:** ~20 aging scores per person (5 Level 1 + 7 Level 2 + 6 Level 3 + ~3 Level 4 + 1 Level 5)
2. **Cross-dimensional correlation matrix** showing which aging dimensions co-vary
3. **Aging subtypes** (3-6 clusters) with clinical characterization
4. **Diabetes severity gradient** per aging dimension
5. **Feature importance** in the unified model (which dimension matters most?)
6. **Novel clocks:** CGM metabolic age, environmental exposure age, FLIO metabolic age
7. **Parquet files:** `results/clocks/age_accel.parquet` (2280 × ~20 AgeAccel columns)

---

## 7. Model Availability & Adaptation Guide

### Confirmed Available (weights + code)

| Model | Source | Install / Download | Input Format | Adaptation |
|---|---|---|---|---|
| **RETFound** | [GitHub](https://github.com/rmaphoh/RETFound), [HuggingFace](https://huggingface.co/YukunZhou) | Clone repo + HF download (needs token) | 224×224 images, ViT-Large | Replace classification head with linear regression. Frozen encoder + linear probe validated for age prediction (MAE ~2.85y on UK Biobank) |
| **ECGFounder** | [GitHub](https://github.com/PKUDigitalHealth/ECGFounder), [HuggingFace](https://huggingface.co/PKUDigitalHealth/ECGFounder) | Clone repo + HF download | 12-lead, 500Hz, 10s = tensor 12×5000. Requires: 0.5Hz highpass, 50Hz Butterworth lowpass, 50/60Hz notch, z-score per lead | Add regression head. RegNet architecture (1D CNN). Fine-tuning notebook included |
| **CosinorAge** | [GitHub](https://github.com/ADAMMA-CDHI-ETH-Zurich/CosinorAge) | `pip install cosinorage` | Minute-level ENMO from wrist accelerometry. 7+ days continuous | Pretrained Gompertz model included. **Garmin gotcha:** needs raw accelerometry or ENMO proxy from HR/activity data |
| **BioAge R** (PhenoAge, KDM, HD) | [GitHub](https://github.com/dayoonkwon/BioAge) | R package | Standard blood biomarkers | Direct formula application. All required biomarkers in AI-READI |
| **Tigramite/PCMCI** | [GitHub](https://github.com/jakobrunge/tigramite) | `pip install tigramite` | Regular time series, any resolution | 2,880 points (10 days × 5-min) sufficient for per-person causal graphs |
| **GluFormer** | [GitHub](https://github.com/Guylu/GluFormer) | Code available, weights unclear | CGM glucose traces | May need to train from scratch. Representations useful for downstream tasks |

### NOT Available

| Model | Reason | Workaround |
|---|---|---|
| **JETS** (Empirical Health) | Weights not released (consent restrictions). Apple Watch only | Reimplement architecture (Mamba-2 + TST tokenizer) and train on AI-READI's ~23K person-days. Or skip — use hand-crafted wearable features instead |
| **LifeClock/EHRFormer** | GitHub listed but weights not confirmed available | Use BioAge R package methods (PhenoAge, KDM) as alternatives |
| **PpgAge** | Requires raw PPG waveforms from Apple Watch | Use CosinorAge or hand-crafted HR features instead |

### Key Gotchas

1. **RETFound:** Requires HuggingFace token for weight download. Default code is classification-only — need to swap head for regression. CFP weights validated for age; OCT weights exist but age regression less established.
2. **ECGFounder:** Preprocessing must follow `dataset.py` exactly (specific filter parameters). AI-READI ECGs are 11 seconds — extract 10-second window.
3. **CosinorAge:** Calibrated on research-grade Axivity/ActiGraph, not consumer Garmin. Cross-device validation is a known limitation. Alternative: compute cosinor parameters ourselves from Garmin HR and use Ridge regression → age (bypassing the pretrained CosinorAge model).
4. **Tigramite:** Assumes regularly sampled complete data. Must resample CGM + HR to common 5-min grid and handle gaps before running PCMCI.

---

## 8. Key References

### Established Methods
- Levine ME. PhenoAge. *Aging* 2018. PMC5940111
- Klemera P, Doubal S. KDM. *Mech Ageing Dev* 2006
- Seeman TE. Allostatic load. *PNAS* 2001
- Theou SE et al. Frailty index. *Age Ageing* 2023
- Fong et al. PCAge/LinAge. *Nature Aging* 2024
- Kwon D, Belsky DW. BioAge R package. *GeroScience* 2021

### Multi-Organ Aging
- Wen J, Tian YE et al. 9-system organ ages. *Nature Aging* 2024. PMC11446180
- Oh HS-H et al. Proteomic organ clocks (~20% accelerated aging in one organ). *Nature* 2023;624:164-172
- Oh HS-H et al. Proteomic organ clocks. *Nature* 2023
- MRI multi-organ clocks. *Nature Medicine* 2025

### Modality-Specific Clocks
- CosinorAge. *npj Digital Medicine* 2024. [GitHub](https://github.com/ADAMMA-CDHI-ETH-Zurich/CosinorAge)
- PpgAge. *Nature Communications* 2025
- Lima et al. ECG-Age. *Nature Communications* 2021
- Zhou et al. RETFound. *Nature* 2023. [GitHub](https://github.com/rmaphoh/RETFound_MAE)
- Ludwig et al. Multimodal retinal clock. *Scientific Reports* 2026
- SleepFM. *Nature Medicine* 2026

### Aging + Diabetes
- AI-READI Dataset v3.0.0. doi:10.60775/fairhub.3
- LifeClock. *Nature Medicine* 2025
- Hematology aging clock. *Nature Aging* 2024

### Public Code
- BioAge R: https://github.com/dayoonkwon/BioAge (PhenoAge, KDM, HD)
- CosinorAge: https://github.com/ADAMMA-CDHI-ETH-Zurich/CosinorAge
- RETFound: https://github.com/rmaphoh/RETFound_MAE
- EHRFormer: https://github.com/kaiwang13/EHRFormer
