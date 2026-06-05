# Derived Features Reference

> Systematic catalog of all derivable features from the AI-READI v3.0.0 dataset.
> For each feature: what it is, what raw data it requires, the established protocol,
> available software, clinical meaning, and feasibility assessment.
>
> **Verification log (2026-04-15):** Sections 1 and 7 web-verified against primary sources.
> Corrections applied:
> - eGFR CKD-EPI 2021 requires sex → NOT computable on public AI-READI data
> - HOMA-β formula requires glucose in mmol/L (not mg/dL)
> - QUICKI uses log₁₀ (not natural log)
> - GRI published in J Diabetes Sci Technol (not Diabetes Care)
> - TyG formula convention clarified; artifacts use the 8.x-scale `ln((TG × glucose) / 2)` convention
>
> **Verification log (2026-04-16):** Sections 2–6 web-verified against primary sources
> (same rigor as §1/§7). Corrections applied and re-verified independently:
> - §2: ECGFounder 10M+ ECG pretraining confirmed (Li et al., *NEJM AI* 2025, PMID 40771651). HeartBEiT pretraining is **8.5M ECGs** (Vaid 2023, PMC10242218), not 10M. Task Force 1996 does NOT endorse ultra-short HRV; 10-sec RMSSD validation comes from Munoz 2015 *PLOS ONE* (r≈0.85 vs 5-min).
> - §3: Normal TST is **7–9h (420–540 min)** per NSF Hirshkowitz 2015 and AASM Watson 2015 (PMID 26039963), not 7–8h. Migueles 2017 is in ***Sports Medicine*** (PMID 28303543), not IJBNPA. Routledge 2010 is in ***Can J Cardiol*** (PMID 20548976) and is about exercise/HRV — NOT nocturnal HR dipping; miscast reference removed. AASM ODI diagnostic threshold of "≥5" is a research convention, not AASM-codified (AHI ≥5 is the diagnostic cut). Garmin SpO2 OSA sensitivity "70–80%" could not be verified in primary literature → claim removed. "N_awakenings <5" and "SE <75% poor" thresholds are folklore (no primary source); flagged as conventions.
> - §4: EPA PM2.5 AQI breakpoints **updated May 2024** (AQI=50 now 9.0 µg/m³, not 12). WHO 2021 AQGs: **annual = 5 µg/m³, 24-h = 15 µg/m³** (only 24-h is 15). ASHRAE 55 comfort envelope is **~20–26°C PMV-based** (season/clo-dependent), not 18–24°C — the 18°C minimum is WHO cold-homes, not ASHRAE. Johnson & Laye *BMJ* 2015 could not be located → citation removed. 250-lux melanopic EDI daytime threshold is from **Brown et al. 2022 *PLoS Biol***, not CIE S 026 (CIE defines the metric, Brown the threshold).
> - §5: Caspersen 2016 *EHP* for PM2.5/HRV could not be located → replaced with **Pope et al. 2004 *Environ Health Perspect* 112:339** (PMID 14998750).
> - §6: Sauer 2017 *Biomed Opt Express* on FLIO in diabetes could not be located → replaced with **Dysli et al. 2017 *Prog Retin Eye Res* 60:120-143** (PMID 28673870). "DeepRT" corrected to **DeepRetina** (Li 2020 *Transl Vis Sci Technol* 9(2):61, PMID 33329940). Nusinovici 2022 confirmed in ***Age and Ageing*** 51:afac065.

## Table of Contents

1. [CGM-Derived Glycemic Metrics](#1-cgm-derived-glycemic-metrics)
2. [ECG-Derived Cardiac Features](#2-ecg-derived-cardiac-features)
3. [Wearable-Derived Features](#3-wearable-derived-features)
4. [Environmental Sensor Features](#4-environmental-sensor-features)
5. [Cross-Modal Derived Features](#5-cross-modal-derived-features)
6. [Retinal Imaging Features](#6-retinal-imaging-features)
7. [Clinical Composite Scores](#7-clinical-composite-scores)
8. [Summary Matrix](#8-summary-matrix)

---

## 1. CGM-Derived Glycemic Metrics

**Raw data:** Dexcom G6, 5-minute sampling, ~2,856 readings over ~10 days per participant.
**Key reference:** International Consensus on Use of CGM (Battelino et al., *Lancet Diabetes Endocrinol* 2023;11(1):42-57; Battelino et al., *Diabetes Care* 2019;42(8):1593-1603).

### 1.1 Basic Statistics

| Metric | Formula | Unit | What it reflects | Standard? | Software |
|---|---|---|---|---|---|
| **Mean glucose** | arithmetic mean of all readings | mg/dL | Overall glycemic level; correlates with HbA1c | Yes — consensus | Any (trivial) |
| **SD glucose** | standard deviation | mg/dL | Overall variability | Yes — consensus | Any |
| **CV (coefficient of variation)** | SD / mean × 100 | % | Variability normalized to mean; CV ≥36% = "unstable" diabetes per consensus | Yes — primary variability metric per 2019 consensus | Any |

**Status:** Already implemented in `cgm.py`.

### 1.2 Time-in-Range (5-Level Consensus)

| Metric | Range (mg/dL) | Target | What it reflects | Standard? |
|---|---|---|---|---|
| **TBR Level 2** (VLow) | <54 | <1% | Clinically significant hypoglycemia — risk of seizure, coma | Yes — 2019 consensus |
| **TBR Level 1** (Low) | 54–69 | <4% | Mild hypoglycemia — risk of falls, impaired cognition | Yes |
| **TIR** (Target) | 70–180 | >70% | Good glycemic control; each 5% ↑ TIR ≈ 0.5% ↓ HbA1c | Yes — **primary outcome metric** |
| **TAR Level 1** (High) | 181–250 | <25% | Mild hyperglycemia — long-term microvascular risk | Yes |
| **TAR Level 2** (VHigh) | >250 | <5% | Severe hyperglycemia — risk of DKA, acute complications | Yes |

**Reference:** Battelino et al., *Diabetes Care* 2019, Table 2.
**Software:** `cgmquantify` (Python), `cgmanalysis` (R), `iglu` (R). Or trivial to compute: `(glucose >= low) & (glucose <= high)).mean()`.
**Status:** We compute 3-level (TBR/TIR/TAR). Need to expand to 5-level.

### 1.3 GRI (Glycemic Risk Index)

| Component | Formula | What it reflects |
|---|---|---|
| **GRI** | 3.0 × VLow% + 2.4 × Low% + 1.6 × VHigh% + 0.8 × High% | Composite 0–100 score; weights hypo > hyper because hypo is more acutely dangerous |

**Reference:** Klonoff DC, Wang J, Rodbard D, et al. "A Glycemia Risk Index (GRI) of Hypoglycemia and Hyperglycemia for Continuous Glucose Monitoring Validated by Clinician Ratings." *J Diabetes Sci Technol* 2023;17(5):1226-1242. PMID 35348391.
**Why it matters:** Single number that replaces the 5 TIR metrics. Endorsed as the primary CGM composite. Clinician-validated — correlates with endocrinologist ratings of glycemic control.
**Software:** `cgmquantify` has it. Formula is simple arithmetic on the 5 TIR values.
**Status:** Not implemented.

### 1.4 GMI (Glucose Management Indicator)

| Metric | Formula | Unit | What it reflects |
|---|---|---|---|
| **GMI** | 3.31 + 0.02392 × mean_glucose | % (HbA1c-equivalent) | "Lab-free HbA1c" estimated from CGM mean glucose |

**Reference:** Bergenstal RM, Beck RW, Close KL, et al. "Glucose Management Indicator (GMI): A New Term for Estimating A1C From Continuous Glucose Monitoring." *Diabetes Care* 2018;41(11):2275-2280. PMID 30224348.
**Why it matters:** Allows comparison with lab HbA1c; discrepancy between GMI and lab HbA1c ("glycation gap") itself is clinically meaningful — may reflect hemoglobin variants or RBC turnover differences.
**Status:** Already implemented.

### 1.5 LBGI / HBGI (Low/High Blood Glucose Index)

| Metric | Formula | What it reflects |
|---|---|---|
The risk transform for BG in mg/dL:

```
f(BG) = 1.509 × ( [ln(BG)]^1.084 − 5.381 )
r(BG) = 10 × f(BG)²
rl(BG) = r(BG) if f(BG) < 0, else 0     ← left branch (hypoglycemia risk)
rh(BG) = r(BG) if f(BG) > 0, else 0     ← right branch (hyperglycemia risk)
LBGI = mean of rl(BG) across all readings   (LBGI > 2.5 = elevated hypo risk)
HBGI = mean of rh(BG) across all readings   (HBGI > 4.5 = elevated hyper risk)
```

The transform maps BG=112.5 mg/dL to f=0 (zero risk), with risk increasing symmetrically for deviations in either direction on the log-transformed scale.

**Reference:** Kovatchev BP, Cox DJ, Gonder-Frederick LA, et al. "Assessment of risk for severe hypoglycemia among adults with IDDM." *Diabetes Care* 1998;21(11):1870-1875. PMID 9802735. Updated in Kovatchev BP, et al. "Evaluation of a new measure of blood glucose variability in diabetes." *Diabetes Care* 2006;29(11):2433-2438.
**Why it matters:** The glucose scale is inherently asymmetric (40–400 mg/dL). LBGI/HBGI apply a log transform that symmetrizes it, so you can separately quantify low vs high glucose risk. Standard in diabetes technology research for 25+ years.
**Software:** `iglu` (R), `cgmquantify` (Python). Formula is ~10 lines.
**Status:** Not implemented.

### 1.6 ADRR (Average Daily Risk Range)

| Metric | Formula | What it reflects |
|---|---|---|
| **ADRR** | mean across days of (max_daily_LBGI + max_daily_HBGI) | Day-to-day glycemic instability. Captures how extreme each day gets. |

**Reference:** Kovatchev BP, Otto E, Cox DJ, et al. "Evaluation of a New Measure of Blood Glucose Variability in Diabetes." *Diabetes Care* 2006;29(11):2433-2438.
**Why it matters:** Captures the "worst moment of each day" rather than averages. ADRR > 30 = high risk.
**Software:** `iglu` (R). Requires LBGI/HBGI per reading, then daily max + average.
**Status:** Not implemented. Depends on LBGI/HBGI.

### 1.7 MAGE (Mean Amplitude of Glycemic Excursions)

| Metric | Method | What it reflects |
|---|---|---|
| **MAGE** | Identify peaks and nadirs in glucose trace; compute amplitude of excursions exceeding 1 SD; average them | Magnitude of glucose swings, filtering out small fluctuations |

**Reference:** Service et al., *Diabetes* 1970. (Original.) Multiple refinements since.
**Why it matters:** Captures the "rollercoaster" pattern that TIR and CV miss. Two patients can have the same mean and CV but very different MAGE if one has few large swings vs many small ones.
**Software:** `iglu` (R), `cgmquantify` (Python). Multiple algorithmic variants exist (Service original, Baghurst, etc.) — results differ by ~10% depending on implementation.
**Status:** Already implemented (peak-nadir method).

### 1.8 AGP (Ambulatory Glucose Profile)

| Metric | Method | What it reflects |
|---|---|---|
| **AGP percentile curves** | For each time-of-day bin (e.g., every 30 min), compute 10th/25th/50th/75th/90th percentile of glucose across all recorded days | "Typical day" pattern with variability bands |

**Reference:** Mazze et al., *Diabetes Technology & Therapeutics* 2013. International consensus reports include AGP as the standard CGM visualization.
**What it captures that other metrics don't:** Temporal patterns — postprandial spikes, dawn phenomenon, nocturnal hypoglycemia. Two patients with identical TIR/CV/MAGE can have very different AGP shapes.
**As features for ML:** The percentile values at each time bin become a fixed-length feature vector (e.g., 48 bins × 5 percentiles = 240 features). Can also extract summary features: time of daily max, amplitude of dawn rise, postprandial AUC.
**Software:** `iglu` (R) produces AGP plots. For feature extraction: requires aligning to local time (needs the `timezone` field we now expose).
**Status:** Not implemented.

### 1.9 Dawn Phenomenon / Overnight Patterns

| Metric | Method | What it reflects |
|---|---|---|
| **Dawn phenomenon** | Mean glucose 06:00–09:00 minus mean glucose 00:00–06:00 (local time) | Pre-breakfast glucose rise driven by cortisol/growth hormone surge |
| **Nocturnal glucose** | Mean glucose 00:00–06:00 | Basal glucose without food influence |
| **Nocturnal nadir** | Minimum glucose 00:00–06:00 | Risk of overnight hypoglycemia |

**Reference:** Monnier et al., *Diabetes & Metabolism* 2012 (dawn phenomenon prevalence and clinical relevance).
**Why it matters:** Dawn phenomenon is present in ~50% of T2DM patients and is poorly captured by HbA1c or mean glucose. It reflects hepatic insulin resistance specifically.
**Requirement:** Must convert UTC timestamps to local time using CGM header `timezone` field.
**Software:** No standard package; ~20 lines of code once local-time conversion is done.
**Status:** Not implemented. Blocked on local-time conversion (now unblocked since we expose timezone).

### 1.10 Data Completeness / Wear Time

| Metric | Method | What it reflects |
|---|---|---|
| **% expected readings present** | n_readings / (duration_days × 288) × 100 | Sensor wear compliance. <70% may bias metrics. |
| **Longest gap** | Max time between consecutive readings | Sensor dropout events |
| **Number of gaps >20 min** | Count of intervals >4× expected 5-min interval | Data quality indicator |

**Reference:** Consensus recommends ≥70% data capture over ≥14 days for reliable metrics. AI-READI has ~10 days.
**Software:** Trivial computation on timestamp differences.
**Status:** Not implemented.

---

## 2. ECG-Derived Cardiac Features

**Raw data:** Philips TC30 12-lead ECG, 500 Hz, 11 seconds (5,500 samples × 12 leads).
**Key constraint:** 11 seconds is short for many standard ECG analyses (HRV typically requires 5 min+). However, ultra-short-term HRV from 10-sec strips has been validated (Shaffer & Ginsberg, *Frontiers in Public Health* 2017).

### 2.1 Device-Reported Intervals (Already Available)

| Metric | Source | Unit | What it reflects | Standard? |
|---|---|---|---|---|
| **Heart rate** | `.hea` header `Rate` | bpm | Resting heart rate — autonomic tone, fitness, mortality predictor | Yes |
| **PR interval** | `.hea` header `PR` | ms | AV conduction time. Prolonged (>200ms) = 1st degree AV block | Yes |
| **QRS duration** | `.hea` header `QRSD` | ms | Ventricular depolarization. >120ms = bundle branch block | Yes |
| **QT interval** | `.hea` header `QT` | ms | Total ventricular depolarization + repolarization | Yes |
| **QTc** | `.hea` header `QTc` | ms | Rate-corrected QT (Bazett or Fridericia). >470ms (F) / >450ms (M) = prolonged | Yes |

**Status:** Already extracted from manifest and .hea headers. Available in participant_index.

### 2.2 R-Peak Detection and Beat Segmentation

| What | Method | Software | Notes |
|---|---|---|---|
| **R-peak locations** | Pan-Tompkins (1985), Hamilton (2002), or Engelse-Zeelenberg | `neurokit2.ecg_peaks()`, `biosppy.ecg.ecg()`, `wfdb.processing.xqrs_detect()` | Prerequisite for all features below |
| **RR intervals** | Differences between consecutive R-peak times | Derived from R-peaks | The input to all HRV computation |
| **Beat segmentation** | Delineate P-QRS-T boundaries per beat | `neurokit2.ecg_delineate()` | Needed for morphology features |

**Software comparison:**
- `neurokit2` — most comprehensive, Python-native, well-documented, actively maintained. Recommended.
- `biosppy` — simpler, good Hamilton detector, less feature extraction
- `wfdb.processing` — XQRS detector, native to the WFDB format we use
- `HeartPy` — focused on PPG/HR but works for ECG

**Feasibility for 11-second recordings:** All detectors work on short strips. Expect 8–15 beats in 11 seconds (depending on HR 40–80 bpm). Minimum ~6 beats needed for meaningful RR statistics.

### 2.3 HRV — Time Domain

| Metric | Formula | Unit | What it reflects | Min beats needed |
|---|---|---|---|---|
| **SDNN** | SD of all NN (normal-to-normal RR) intervals | ms | Overall HRV — total autonomic variability. Gold standard for mortality prediction. | ~6 |
| **RMSSD** | Root mean square of successive NN differences | ms | Short-term (beat-to-beat) variability — parasympathetic/vagal tone. Most reliable for ultra-short recordings. | ~6 |
| **pNN50** | % of successive NN differences >50ms | % | Another parasympathetic marker. Less reliable than RMSSD for short strips. | ~10 |
| **SDSD** | SD of successive NN differences | ms | Similar to RMSSD, slightly different formula | ~6 |

**Reference:** Task Force of the ESC/NASPE, *Circulation* 1996;93(5):1043-1065, PMID 8598068 (original HRV standard — Task Force itself recommends ≥1 min for time-domain; does NOT endorse 10-sec HRV). Ultra-short HRV validation: Munoz ML et al., *PLOS ONE* 2015;10(9):e0138921, PMID 26414314 — RMSSD from 10-sec strip correlates r=0.85 with 5-min RMSSD; SDNN unreliable at this length. Shaffer & Ginsberg, *Front Public Health* 2017;5:258, PMID 29034226 (review summarizing ultra-short HRV literature).
**Caveat:** 11 seconds gives ~8–15 RR intervals. RMSSD is validated for this length. SDNN and pNN50 are less stable and should be interpreted cautiously.
**Software:** `neurokit2.hrv_time()` — takes R-peak indices, returns all time-domain metrics. Also `pyhrv`, `hrv-analysis`.
**Status:** Not implemented.

### 2.4 HRV — Frequency Domain

| Metric | Band | Unit | What it reflects | Feasible in 11s? |
|---|---|---|---|---|
| **HF power** | 0.15–0.40 Hz | ms² | Parasympathetic (vagal) activity | **Yes** — minimum period 2.5s, need >2 cycles = >5s |
| **LF power** | 0.04–0.15 Hz | ms² | Mixed sympathetic + parasympathetic | **Marginal** — minimum period 6.7s, need >2 cycles = >13s |
| **VLF power** | 0.003–0.04 Hz | ms² | Thermoregulation, renin-angiotensin | **No** — requires minutes |
| **LF/HF ratio** | LF power / HF power | ratio | Sympathovagal balance (controversial) | **Marginal** |

**Method:** Welch PSD or Lomb-Scargle periodogram on the RR interval series.
**Reference:** Task Force 1996 (PMID 8598068) for band definitions; Munoz 2015 (PMID 26414314) and Shaffer & Ginsberg 2017 (PMID 29034226) for ultra-short-strip feasibility — HF power can be estimated from ~10-sec recordings (minimum period 2.5s × ≥2 cycles = 5s); LF, VLF, and LF/HF are NOT endorsed by Task Force 1996 at this duration.
**Software:** `neurokit2.hrv_frequency()`, `scipy.signal.welch()`.
**Status:** Not implemented. Only HF power is reliable from 11-second recordings.

### 2.5 Signal Quality Metrics

| Metric | Method | What it reflects |
|---|---|---|
| **SNR per lead** | Signal power / noise power (noise estimated from isoelectric segments) | Recording quality — low SNR → unreliable feature extraction |
| **Baseline wander** | Low-frequency energy (<0.5 Hz) | Movement artifact or electrode drift |
| **Powerline noise** | Energy at 60 Hz (US mains frequency) | Electromagnetic interference |
| **R-peak confidence** | Detector confidence score or consistency across leads | Whether R-peaks are reliably detected |

**Software:** `neurokit2.ecg_quality()` returns a per-sample quality score. `biosppy` has basic quality checks.
**Why it matters:** Before batch-processing 2,251 ECGs, you need to flag poor-quality recordings that would produce unreliable features. Quality filtering is standard practice — e.g., ECGFounder excludes recordings with SNR < threshold.
**Status:** Not implemented.

### 2.6 Waveform Morphology Features

| Metric | Method | What it reflects | Feasible? |
|---|---|---|---|
| **P-wave duration** | Delineation of P-wave onset/offset | Atrial depolarization time — prolonged in atrial enlargement | Yes |
| **P-wave area** | Integral of P-wave across leads | Atrial mass/pressure — enlarged in heart failure | Yes but noisy in 11s |
| **T-wave amplitude** | Peak of T-wave | Repolarization — inverted T is ischemia marker | Yes |
| **T-wave symmetry** | Ratio of ascending/descending T-wave slopes | Repolarization heterogeneity | Yes |
| **QT dispersion** | Max QTc − Min QTc across 12 leads | Spatial repolarization heterogeneity — arrhythmia risk | Requires per-lead QT measurement |
| **ST segment deviation** | Voltage at J-point + 60ms relative to baseline | Ischemia (depression) or pericarditis (elevation) | Yes |

**Software:** `neurokit2.ecg_delineate()` provides P/QRS/T boundaries. Morphology features require custom extraction on top.
**Status:** Not implemented. Lower priority than HRV for aging clock work.

### 2.7 12-Lead Embeddings (for ML)

| Approach | Method | What it produces |
|---|---|---|
| **Raw waveform** | Normalize, optionally crop/pad to fixed length | (5500, 12) tensor — direct input to 1D-CNN or transformer |
| **Pretrained embeddings** | Pass through ECGFounder, HeartBEiT, or ST-MEM | Fixed-length feature vector from a foundation model |
| **Handcrafted feature vector** | Concatenate HRV + intervals + morphology features | ~30-dimensional vector |

**Software:** ECGFounder (Li et al., *NEJM AI* 2025; 10.77M ECGs / 1.82M subjects; arXiv:2410.04133; PMID 40771651). HeartBEiT (Vaid et al., *npj Digital Medicine* 2023;6:108, PMID 37280346; ViT on ECG spectrograms; **8.5M ECGs pretraining** per PMC10242218). ST-MEM (Na et al., ICLR 2024, arXiv:2402.09450; masked ECG autoencoder). All have public weights.
**Status:** Not implemented. Path A (aging clock probes) would use pretrained embeddings.

---

## 3. Wearable-Derived Features

**Raw data:** Garmin Vivosmart 5, 7 sub-modalities, ~20 days per participant.
**Key reference:** Migueles JH et al., *Sports Medicine* 2017;47(9):1821-1845, PMID 28303543 (accelerometry processing consensus). Ancoli-Israel S et al., *Sleep* 2003;26(3):342-392, PMID 12749557 (actigraphy review).

### 3.1 Sleep Architecture (Per-Night)

| Metric | Formula | Unit | What it reflects | Normal range |
|---|---|---|---|---|
| **TST (Total Sleep Time)** | Sum of all sleep-stage durations (light+deep+REM) | minutes | Sleep quantity | 420–540 min (7–9h) — NSF Hirshkowitz 2015; AASM Watson 2015, PMID 26039963 |
| **TIB (Time In Bed)** | End of last sleep epoch − start of first sleep epoch | minutes | Sleep opportunity window | Variable |
| **SE (Sleep Efficiency)** | TST / TIB × 100 | % | Sleep quality — ratio of actual sleep to time in bed | >85% commonly used as "healthy" cutoff (AASM CBT-I convention); no single consensus threshold for "poor" |
| **WASO (Wake After Sleep Onset)** | Total duration of "awake" epochs between first and last sleep epoch | minutes | Sleep fragmentation | <30 min healthy |
| **SOL (Sleep Onset Latency)** | Time from first epoch to first sleep epoch | minutes | Difficulty falling asleep | <15 min normal; ≥31 min per Lichstein 2003 quantitative insomnia criterion (PMID 12643966) — note DSM-5/ICSD-3 themselves do not specify a numeric SOL cutoff |
| **REM%** | REM duration / TST × 100 | % | REM sleep proportion — critical for memory consolidation, emotional regulation | 20–25% |
| **Deep%** | Deep duration / TST × 100 | % | Slow-wave sleep — growth hormone release, glucose regulation, glymphatic clearance | 15–20% |
| **Light%** | Light duration / TST × 100 | % | Light sleep proportion | 50–60% |
| **N_awakenings** | Count of awake→sleep transitions after sleep onset | count | Fragmentation frequency | No AASM-codified cutoff; AASM uses arousal index (ArI) >10/h as abnormal — prefer that metric |
| **Sleep midpoint** | (sleep onset + wake time) / 2 | clock time | Chronotype proxy — later midpoint = later chronotype | Varies |

**Algorithm:** Segment nights by finding gaps >60 min between sleep episodes. For each night, sum durations by stage, compute onset/offset.
**Software:** No standard package for Garmin-specific sleep data. `GGIR` (R) is the standard for raw accelerometry but works on Axivity/GENEActiv, not Garmin processed stages. Custom implementation needed (~50 lines per night segmentation + ~20 lines per metric).
**Caveat:** Garmin's sleep staging algorithm is proprietary. Validation studies (Núñez-Cortés 2024 *JMIR mHealth* PMID 38557751; Menghini 2025 *Sleep Advances* PMID 40291577) report moderate TST accuracy but **poor epoch-by-epoch stage agreement** with PSG (specificity 29–52%). Garmin is not FDA-cleared for sleep diagnostics. Treat as consumer-grade estimates, not research-grade PSG.
**Status:** Not implemented.

### 3.2 Circadian Rhythm Markers

| Metric | Method | What it reflects | Software |
|---|---|---|---|
| **IS (Interdaily Stability)** | Ratio of variance of 24h-averaged hourly values to overall variance of hourly values | Regularity of the rest-activity pattern across days. IS=1 = identical every day. | `nparACT` (R), `pyActigraphy` (Python) |
| **IV (Intradaily Variability)** | Ratio of mean squared successive difference of hourly values to total variance | Fragmentation of the rhythm within a day. High IV = frequent transitions between rest and activity. | Same |
| **M10 (Most Active 10h)** | Mean activity during the most active 10 consecutive hours | Daytime activity amplitude | Same |
| **L5 (Least Active 5h)** | Mean activity during the least active 5 consecutive hours | Nighttime rest depth | Same |
| **RA (Relative Amplitude)** | (M10 − L5) / (M10 + L5) | Overall circadian amplitude. RA close to 1 = strong rhythm. Declines with aging and disease. | Same |
| **Cosinor amplitude** | Amplitude of fitted cosine: A×cos(2π/24 × (t − φ)) + M | Strength of 24h oscillation | `CosinorPy` (Python), `cosinor` (R) |
| **Cosinor acrophase (φ)** | Phase of peak activity from cosinor fit | Timing of peak activity — delayed in "night owls" | Same |
| **Cosinor mesor (M)** | Midline of cosine fit | Average activity level | Same |

**Input data:** Hourly (or finer) binned heart rate or step counts from wearable. HR is preferred because it's continuously sampled; steps have gaps during sedentary periods.
**Reference:** Witting W et al., *Biol Psychiatry* 1990;27(6):563-572, PMID 2322616 (IS/IV origin). Van Someren EJ et al., *Chronobiol Int* 1999;16(4):505-518, PMID 10442243 (nonparametric M10/L5/RA in AD). Cornelissen G, *Theor Biol Med Model* 2014;11:16, PMID 24725531 (cosinor-based rhythmometry).
**Why it matters:** Circadian disruption is causally linked to T2DM (Scheer FA et al., *PNAS* 2009;106(11):4453-4458, PMID 19255424), cardiovascular disease, and cognitive decline. These metrics are established biomarkers of circadian health.
**Software:** `pyActigraphy` (Hammad G et al., *PLoS Comput Biol* 2021;17(10):e1009514, PMID 34665807; supports IS/IV/M10/L5/RA), `nparACT` (R), `CosinorPy` (Moškon M, *BMC Bioinformatics* 2020;21:485, PMID 33121431). All are well-established.
**Status:** Not implemented.

### 3.3 Activity and Sedentary Behavior

| Metric | Method | What it reflects |
|---|---|---|
| **Daily step count** | Sum steps from physical_activity intervals per day | Physical activity volume |
| **Active minutes per day** | Sum duration of non-sedentary activity intervals | PA volume (time-based) |
| **Sedentary time per day** | Sum duration of "sedentary" intervals | Sedentary behavior — independent risk factor for T2DM |
| **Number of sedentary bouts** | Count of continuous sedentary periods >30 min | Sedentary accumulation pattern |
| **Breaks in sedentary time** | Number of transitions from sedentary to active per day | Protective behavior — breaking up sitting |
| **Peak 30-min cadence** | Highest mean steps/min over any 30-min window | Physical capacity proxy |

**Reference:** Tudor-Locke C et al., *Int J Behav Nutr Phys Act* 2011;8:79, PMID 21798015 (step-based metrics). Healy GN et al., *Diabetes Care* 2008;31(4):661-666, PMID 18252901 (sedentary breaks and metabolic health).
**Software:** Custom implementation on the interval-based physical_activity DataFrame. `actiPASS` (MATLAB), `activPAL` (proprietary) exist for raw accelerometry but not for Garmin processed data.
**Status:** Not implemented.

### 3.4 Heart Rate Features

| Metric | Method | What it reflects |
|---|---|---|
| **Resting HR** | Minimum sustained HR over 5+ minutes during sleep | Cardiovascular fitness; mortality predictor |
| **Mean daytime HR** | Average HR during waking hours (defined by sleep epochs) | Autonomic tone during activity |
| **Mean nighttime HR** | Average HR during sleep | Autonomic tone at rest |
| **Nocturnal HR dip** | (daytime HR − nighttime HR) / daytime HR × 100 | Autonomic "dipping" — non-dipping (<10%) predicts CV events |
| **HR recovery proxy** | Rate of HR decrease after detected activity bouts | Parasympathetic reactivation — impaired in diabetes |

**Reference:** Palatini P, *Curr Hypertens Rep* 2001;3 Suppl 1:S3-S9, PMID 11580882 (sympathetic overactivity in hypertension; for resting-HR-mortality specifically see Palatini 2002 *Arch Intern Med* 162:2313). Nocturnal HR non-dipping: Eguchi K et al., *Am J Hypertens* 2009;22(1):46-51, PMC3806286 (predicts CV events).
**Software:** Custom implementation using HR + sleep timestamps for day/night segmentation.
**Status:** Not implemented.

### 3.5 SpO2 Overnight Features

| Metric | Method | What it reflects |
|---|---|---|
| **Mean nocturnal SpO2** | Average SpO2 during sleep hours | Baseline oxygenation |
| **Min nocturnal SpO2** | Lowest SpO2 during sleep | Severity of desaturation events |
| **ODI (Oxygen Desaturation Index)** | Number of ≥3% SpO2 drops per hour of sleep (AASM recommended rule; ≥4% is the Medicare-aligned alternative) | Screening proxy for OSA — note AASM diagnostic criterion is AHI ≥5, not ODI ≥5; ODI ≥5 is a research convention |
| **T90 (Time below 90%)** | Fraction of sleep time with SpO2 <90% | Hypoxemia burden |

**Reference:** Berry RB et al., *J Clin Sleep Med* 2012;8(5):597-619, PMID 23066376 (AASM 2012 scoring manual — recommended hypopnea rule ≥3% desat OR arousal; ≥4% alternative).
**Caveat:** Garmin wrist SpO2 has limited accuracy compared to medical-grade pulse oximetry. No peer-reviewed Garmin-specific OSA screening sensitivity/specificity could be located — treat any ODI derived from wrist SpO2 as an exploratory signal, not a clinical screening tool.
**Software:** Custom implementation. ~20 lines.
**Status:** Not implemented.

### 3.6 Stress and Respiratory Rate Patterns

| Metric | Method | What it reflects |
|---|---|---|
| **Mean daytime stress** | Average Garmin stress score during waking | Sympathetic arousal during the day |
| **Stress reactivity** | SD of stress scores | Variability of autonomic response |
| **Mean daytime RR** | Average respiratory rate during waking | Baseline respiratory function |
| **Mean nocturnal RR** | Average during sleep | Respiratory drive at rest |

**Caveat:** Garmin stress is derived from HRV via a proprietary algorithm (Firstbeat analytics; Garmin acquired Firstbeat in June 2020). It's an autonomic tone index, not a psychological stress measure.
**Software:** Custom implementation using HR/stress + sleep timestamps.
**Status:** Not implemented.

---

## 4. Environmental Sensor Features

**Raw data:** LeeLab Anura, 22 columns at 5-second intervals, ~10 days.
**Key reference:** CIE S 026/E:2018 *System for Metrology of Optical Radiation for ipRGC-Influenced Responses to Light* (defines α-opic metrics incl. melanopic EDI); Lucas RJ et al., *Trends Neurosci* 2014;37(1):1-9, PMID 24287308 (non-visual effects of light). Daytime / evening / night light dose recommendations: Brown TM et al., *PLoS Biol* 2022;20(3):e3001571, PMID 35298459. US EPA *Technical Assistance Document for the Reporting of Daily Air Quality — the AQI* (May 2024 revision) for PM2.5 breakpoints.

### 4.1 Circadian Light Exposure

| Metric | Method | What it reflects | Software |
|---|---|---|---|
| **Melanopic EDI** | Spectral weighting of the 10 light channels by melanopic sensitivity function (ipRGC response peaks at 480 nm) | Circadian-effective light dose — drives melatonin suppression and circadian entrainment | `luxpy` (Python), CIE S 026 toolbox |
| **Daily melanopic dose** | Integral of melanopic EDI over daytime hours | Total circadian light exposure per day | Custom (integral) |
| **Time above 250 lux melanopic EDI** | Hours per day with melanopic EDI > 250 lux (daytime threshold per Brown et al. 2022 *PLoS Biol* consensus, PMID 35298459 — CIE S 026 defines the metric, Brown 2022 sets the threshold) | Bright light exposure sufficient for daytime circadian entrainment | Custom |
| **First bright light time** | Time of first reading above threshold after midnight | Morning light onset — earlier = more entrained | Custom |
| **Evening light (after 20:00)** | Mean melanopic EDI 20:00–00:00 | Evening light — delays circadian phase, suppresses melatonin | Custom |
| **Daytime/evening light ratio** | Mean daytime EDI / mean evening EDI | Circadian light contrast — higher is better | Custom |

**Feasibility assessment:** The Anura sensor uses an ams AS7341 spectral sensor (datasheet DS000504) with channels at 415, 445, 480, 515, 555, 590, 630, 680 nm plus Clear and 910 nm NIR. Human melanopsin λmax is ~479 nm intrinsically, ~490 nm when in-vivo lens filtering is applied (Bailes & Lucas, *Proc R Soc B* 2013, PMC3619500); CIE S 026 action spectrum is commonly cited at 480 nm. The 480 nm channel (lch2) directly overlaps the melanopic peak, but proper α-opic weighting requires all channels. **This is an approximation**, not a calibrated radiometric measurement — the sensor channels are relative intensity (0–1), not absolute irradiance. Converting to absolute lux requires the sensor's spectral responsivity calibration data, which may not be published.
**Alternative simpler approach:** Use the `clear` channel (lch10, broadband) as a proxy for illuminance. Correlates with lux but isn't calibrated.
**Software:** `luxpy` (Smet KAG, *LEUKOS* 2020;16(3):179-201; PyPI `luxpy`; exposes `spd_to_aopicEDI()`) can compute melanopic EDI from spectral power distributions if calibration data is available. Otherwise custom weighted sum.
**Status:** Not implemented.

### 4.2 Air Quality

| Metric | Method | What it reflects | Reference |
|---|---|---|---|
| **Daily mean PM2.5** | Average of pm2.5 column per day | Fine particulate exposure | EPA/WHO guidelines |
| **PM2.5 AQI category** | Map daily 24-h mean to EPA breakpoint table (effective May 2024): AQI=50 at **9.0 µg/m³**, 100 at 35.4, 150 at 55.4, 200 at 125.4, 300 at 225.4, 500 at 325.4. Categories: Good / Moderate / Unhealthy for Sensitive Groups / Unhealthy / Very Unhealthy / Hazardous | Health risk category | EPA TA Document May 2024; 89 FR 16202 |
| **Hours above WHO limit** | Time per day with PM2.5 > **15 µg/m³ (2021 WHO 24-h guideline)**. WHO 2021 annual guideline is **5 µg/m³** — use the annual value for per-participant average exposure, the 24-h value for daily peaks | Exceedance burden | WHO *Global Air Quality Guidelines* 2021, ISBN 978-92-4-003422-8 |
| **Cooking events** | Detect PM2.5 spikes >3× baseline sustained >5 min | Indoor air quality events | Heuristic, no consensus standard |

**Software:** AQI lookup table is trivial. PM2.5 event detection is custom.
**Status:** Not implemented.

### 4.3 Temperature and Comfort

| Metric | Method | What it reflects |
|---|---|---|
| **Mean indoor temperature** | Daily average of temp column | Thermal environment |
| **Time in comfort zone** | Hours per day with temp in ASHRAE 55 comfort envelope (~20–23.5°C winter 1.0 clo; ~22.5–26°C summer 0.5 clo; PMV −0.5 to +0.5) | Thermal comfort — metabolic implications |
| **Time below cold threshold** | Hours per day with temp <18°C (WHO *Housing and Health Guidelines* 2018 indoor minimum) | Cold-exposure burden |
| **Temperature amplitude** | Daily max − daily min | Home temperature variability |

**Reference:** ANSI/ASHRAE Standard 55-2023 *Thermal Environmental Conditions for Human Occupancy* (PMV-based comfort envelope, NOT a fixed temperature range). WHO *Housing and Health Guidelines* 2018 (ISBN 978-92-4-155037-6) — 18°C indoor minimum for cold-weather health.
**Status:** Not implemented.

### 4.4 Screen Time and Light-at-Night

| Metric | Method | What it reflects |
|---|---|---|
| **Daily screen-on hours** | Sum of duration where screen=1 per day | Screen exposure |
| **Evening screen time** | Screen-on hours after 20:00 | Blue light at night — circadian disruption |
| **Flicker frequency distribution** | Histogram of ff values when screen=1 | Display type (LED ~120 Hz, CRT ~60 Hz, no screen ~1 Hz) |

**Status:** Not implemented. Trivial computation.

---

## 5. Cross-Modal Derived Features

These require combining two or more modalities after computing their respective individual features.

### 5.1 Glucose–HR Coupling

| Metric | Method | What it reflects | Software |
|---|---|---|---|
| **Cross-correlation (lag 0)** | Pearson r between aligned glucose and HR at 5-min grid | Instantaneous metabolic-cardiovascular coupling | `scipy.signal.correlate` |
| **Optimal lag** | Lag (in minutes) that maximizes cross-correlation | Temporal relationship — does HR lead or follow glucose? | Same |
| **Transfer entropy (glucose→HR)** | Information transfer from glucose to HR time series | Directional causal influence: does glucose drive HR? | `pyinform`, `Tigramite` |
| **Transfer entropy (HR→glucose)** | Reverse direction | Does autonomic state drive glucose? | Same |
| **Granger causality** | VAR model testing whether past glucose predicts future HR beyond past HR alone | Linear causal relationship | `statsmodels.tsa.stattools.grangercausalitytests` |

**Input:** Aligned 5-min time series from `aligned_timeseries()`.
**Reference:** Schreiber T, *Phys Rev Lett* 2000;85(2):461-464, DOI 10.1103/PhysRevLett.85.461 (transfer entropy). Granger CWJ, *Econometrica* 1969;37(3):424-438, DOI 10.2307/1912791 (Granger causality). Tigramite / PCMCI: Runge J et al., *Sci Adv* 2019;5(11):eaau4996.
**Why it matters:** The coupling structure between glucose and HR may differ by diabetes severity. Insulin resistance could decouple these systems. This is the core question for causal discovery on the 10-day window.
**Status:** Not implemented.

### 5.2 Sleep–Glucose Interaction

| Metric | Method | What it reflects |
|---|---|---|
| **Overnight glucose stability** | CV of glucose during sleep hours (00:00–06:00 local) | Nocturnal glycemic control |
| **Sleep quality → next-day TIR** | Correlation between last night's SE and today's TIR | Does poor sleep cause worse glycemic control? |
| **Sleep duration → fasting glucose** | Correlation between TST and next-morning glucose (06:00–08:00) | Short sleep → higher fasting glucose (established in literature) |

**Input:** Per-night sleep metrics (§3.1) + per-day CGM segments.
**Reference:** Spiegel K, Leproult R, Van Cauter E. *Lancet* 1999;354(9188):1435-1439, PMID 10543671 (sleep restriction → impaired glucose tolerance — landmark paper).
**Status:** Not implemented. Requires sleep architecture (§3.1) + daily CGM segmentation.

### 5.3 Activity–Glucose Interaction

| Metric | Method | What it reflects |
|---|---|---|
| **Post-activity glucose response** | Mean glucose in 2h after detected activity bouts vs 2h matched rest periods | Exercise-induced glucose lowering |
| **Daily steps ↔ daily TIR** | Within-person correlation across ~10 days | Does more activity improve same-day glycemic control? |
| **Sedentary bout → glucose drift** | Glucose trend during prolonged sedentary periods (>60 min) | Does inactivity cause glucose rise? |

**Input:** Activity bout detection (§3.3) + aligned CGM.
**Reference:** Colberg SR et al., *Diabetes Care* 2016;39(11):2065-2079, PMID 27926890 (ADA position statement on physical activity/exercise and diabetes).
**Status:** Not implemented.

### 5.4 Environment–Physiology Interaction

| Metric | Method | What it reflects |
|---|---|---|
| **Light exposure → sleep timing** | Correlation between daily bright-light hours and sleep onset time | Light entrainment of circadian clock |
| **Evening light → sleep quality** | Correlation between evening melanopic EDI and that night's SE/WASO | Blue light disrupting sleep |
| **PM2.5 → HR/HRV** | Correlation between daily PM2.5 and mean HR or HRV | Air pollution → cardiovascular stress |
| **Temperature → glucose** | Correlation between ambient temperature and glucose levels | Thermoregulation–metabolism coupling |

**Input:** Environmental features (§4) + wearable features (§3) + CGM features (§1).
**Reference:** Pope CA 3rd, Hansen ML, Long RW, et al. "Ambient particulate air pollution, heart rate variability, and blood markers of inflammation in a panel of elderly subjects." *Environ Health Perspect* 2004;112(3):339-345, PMID 14998750 (canonical PM2.5 → HRV paper).
**Status:** Not implemented.

### 5.5 Clinical Labs ↔ Continuous Modality Summary Table

| What | Method | Purpose |
|---|---|---|
| **Feature matrix extension** | Join feature_matrix.parquet (125 clinical features) with per-person aggregated CGM metrics, wearable summaries, and environmental summaries | Create the master analysis table for all statistical and ML work |

**This is the fundamental cross-modal join.** Every analysis that combines day-1 clinical snapshot with the ~10-day continuous window needs this table.
**Status:** The clinical feature matrix exists. CGM metrics are partially computed. Wearable and environmental summary features don't exist yet.

---

## 6. Retinal Imaging Features

**Raw data:** DICOM images from 4–6 devices across 4 sub-modalities.
**Key constraint:** These are computationally heavy (pixel-level analysis, GPU-accelerated). Listed here for completeness but are a separate workstream from the time-series features.

### 6.1 Image Quality

| Metric | Method | Software | Feasibility |
|---|---|---|---|
| **CFP gradability** | CNN-based quality classifier (blur, exposure, centering) | `EyeQ` (pretrained), `ODIR-grading` | Moderate — need to validate on AI-READI's multi-device images |
| **OCT signal strength** | Mean intensity of B-scans, or manufacturer signal-strength index in DICOM metadata | DICOM tag parsing + numpy | Easy |
| **OCTA motion artifact** | Horizontal banding detection in flow cube | Custom — stripe detection in frequency domain | Moderate |

### 6.2 Retinal Biomarkers from OCT

| Metric | Method | Software | What it reflects |
|---|---|---|---|
| **RNFL thickness** | Extract from manufacturer segmentation (OCTA segmentation files) or re-segment with `retipy` or `DeepRetina` (Li Q et al., *Transl Vis Sci Technol* 2020;9(2):61, PMID 33329940) | Manufacturer-provided in OCTA segmentation DICOMs | Glaucoma biomarker, neural degeneration |
| **Central macular thickness** | Same — extract from segmentation | Same | Macular edema, diabetic retinopathy |
| **Choroidal thickness** | Segment choroid-sclera boundary from enhanced-depth OCT | `choroid-analysis` (limited), mostly custom | Vascular health, age-related changes |

### 6.3 Retinal Biomarkers from OCTA

| Metric | Method | Software | What it reflects |
|---|---|---|---|
| **Vessel density** | Binarize OCTA enface → count vessel pixels / total pixels | Otsu thresholding, `skimage` | Microvascular perfusion — reduced in diabetes |
| **FAZ area** | Segment foveal avascular zone from superficial enface → measure area | Thresholding + connected component in central region | Diabetic retinopathy severity — FAZ enlarges |
| **FAZ circularity** | 4π × area / perimeter² | Same segmentation, then `skimage.measure.regionprops` | Irregular FAZ = more severe disease |
| **Fractal dimension** | Box-counting on binarized vessel map | `skimage`, `FracLac` | Vascular branching complexity — altered in diabetes |

### 6.4 FLIO Decay Curve Fitting

| Metric | Method | Software | What it reflects |
|---|---|---|---|
| **τ_mean (mean fluorescence lifetime)** | Bi-exponential fit: I(t) = α₁e^(-t/τ₁) + α₂e^(-t/τ₂), then τ_mean = (α₁τ₁ + α₂τ₂)/(α₁+α₂) | `FLIMJ` (ImageJ plugin), `SPCImage` (commercial), or custom `scipy.optimize.curve_fit` per pixel | Metabolic state of retinal tissue — τ_mean changes in diabetes, AMD, macular holes |
| **τ₁ (short lifetime)** | From bi-exponential fit | Same | Free flavin fluorescence (FAD) |
| **τ₂ (long lifetime)** | From bi-exponential fit | Same | Bound flavin / lipofuscin |
| **α₁/α₂ ratio** | Amplitude ratio | Same | Relative contribution of metabolic vs structural fluorophores |

**Computational cost:** 256×256 pixels × 1024 time points × bi-exponential fit = ~65K nonlinear optimizations per image × 7,968 images. GPU-accelerated fitting (`gpufit`: Przybylski A et al., *Sci Rep* 2017;7:15722, PMID 29146965) is needed for batch processing.
**Reference:** Dysli C, Wolf S, Berezin MY, Sauer L, Hammer M, Zinkernagel MS. "Fluorescence lifetime imaging ophthalmoscopy." *Prog Retin Eye Res* 2017;60:120-143, PMID 28673870 (comprehensive FLIO review, incl. diabetes applications). FLIMJ tooling: Gao D et al., *PLoS One* 2020;15(12):e0238327, PMID 33378370.
**Status:** Not implemented. Substantial effort.

### 6.5 Diabetic Retinopathy Grading

| Metric | Method | Software | What it reflects |
|---|---|---|---|
| **DR severity grade** | CNN classification on CFP: none / mild NPDR / moderate NPDR / severe NPDR / PDR | `RETFound` (fine-tuned), `EyePACS graders`, `IDx-DR` (FDA-cleared, not open) | Standard DR staging per ETDRS |
| **Microaneurysm count** | Object detection on CFP | `RetinalLesions`, `ODIR` pretrained models | Earliest sign of DR |
| **Hard exudate area** | Segmentation on CFP | Same | Lipid leakage — more severe DR |

**Reference:** International Clinical DR Severity Scale — Wilkinson CP, Ferris FL 3rd, Klein RE, et al. *Ophthalmology* 2003;110(9):1677-1682, PMID 13129861 (defines 5-level: none / mild NPDR / moderate NPDR / severe NPDR / PDR). IDx-DR FDA De Novo DEN180001 authorized April 11, 2018 (Abràmoff MD et al., *npj Digit Med* 2018;1:39).
**Software:** RETFound (Zhou Y, Chia MA, Wagner SK et al., *Nature* 2023;622(7981):156-163, PMID 37704728) is the current state-of-the-art retinal foundation model with public weights (Moorfields/UCL). Fine-tuning on AI-READI CFPs for DR grading is the most natural benchmarking task.
**Status:** Not implemented.

### 6.6 Retinal Age (from pretrained models)

| Metric | Method | Software | What it reflects |
|---|---|---|---|
| **Retinal age** | CNN regression on CFP, trained to predict chronological age | Zhu Z et al., *Br J Ophthalmol* 2023;107(4):547-554, PMID 35042683 ("Retinal age gap as a predictive biomarker for mortality risk"), or fine-tune RETFound with age regression head | Biological age of retinal vasculature |
| **Retinal AgeAccel** | Retinal age − chronological age | Derived | Accelerated vascular aging — predicts mortality (Nusinovici S et al., *Age Ageing* 2022;51(4):afac065, DOI 10.1093/ageing/afac065) |

**This is the entry point for Path A (aging clock probes).**

---

## 7. Clinical Composite Scores

These are computed from the clinical feature matrix (already built) using established formulas.

### 7.1 Cardiovascular Risk

| Score | Inputs | What it estimates | Reference |
|---|---|---|---|
| **ASCVD 10-year risk** | Age, sex, race, SBP, total cholesterol, HDL, diabetes, smoking, BP treatment | 10-year risk of atherosclerotic CV event | Goff et al., *Circulation* 2014 |
| **Framingham Risk Score** | Age, sex, total cholesterol, HDL, SBP, smoking, diabetes | 10-year CHD risk | Wilson et al., *Circulation* 1998 |

**Feasibility for AI-READI:** Sex and race are redacted in the public release. ASCVD and Framingham both require sex. **Cannot compute these scores on public data.** Would need controlled-access version.

### 7.2 Kidney Function

| Score | Formula | What it estimates | Reference |
|---|---|---|---|
| **eGFR (CKD-EPI 2021)** | 142 × min(Scr/κ, 1)^α × max(Scr/κ, 1)^-1.200 × 0.9938^Age × 1.012 [if female]. κ=0.7/α=-0.241 (F), κ=0.9/α=-0.302 (M). | Estimated glomerular filtration rate — kidney function | Inker LA, et al. *NEJM* 2021;385:1737-1749 |
| **UACR** | urine_albumin / urine_creatinine | Albuminuria — early diabetic nephropathy marker | KDIGO 2012 guidelines |
| **CKD stage** | eGFR + UACR category | Chronic kidney disease staging | KDIGO 2012 |

**⚠️ CORRECTION:** The 2021 CKD-EPI equation removed **race** but still **requires sex** (different κ, α constants and a female multiplier of 1.012). Since sex is redacted in the AI-READI public release, **eGFR CANNOT be computed on public data.** CKD staging (which depends on eGFR) is also blocked.

**What IS computable:** UACR alone (urine_albumin / urine_creatinine from the feature matrix). UACR ≥30 mg/g indicates albuminuria regardless of eGFR. UACR can be used for albuminuria staging (A1: <30, A2: 30–300, A3: >300) without needing sex.

### 7.3 Metabolic Syndrome

| Criterion | Threshold | AI-READI column |
|---|---|---|
| Elevated waist | ≥102 cm (M) / ≥88 cm (F) | `waist_cm` — **cannot apply sex-specific threshold (sex redacted)** |
| Elevated triglycerides | ≥150 mg/dL | `triglycerides` ✓ |
| Low HDL | <40 (M) / <50 (F) | `hdl` — **cannot apply sex-specific threshold** |
| Elevated BP | SBP ≥130 or DBP ≥85 | `sbp`, `dbp` ✓ |
| Elevated fasting glucose | ≥100 mg/dL | `glucose` ✓ |

**Feasibility:** Standard MetS definition (NCEP ATP III) requires sex-specific thresholds for waist and HDL. **Cannot compute standard MetS on public data.** Could compute a modified version ignoring sex-specific thresholds, but this is non-standard.

### 7.4 Insulin Resistance Indices

| Score | Formula (with correct units) | What it estimates | Feasible? |
|---|---|---|---|
| **HOMA-IR** | (insulin_µU/mL × glucose_mg/dL) / 405 | Insulin resistance (higher = more resistant). HOMA-IR > 2.5 suggests insulin resistance. | ✓ |
| **HOMA-β** | (20 × insulin_µU/mL) / (glucose_mg/dL / 18.0182 − 3.5) | Beta-cell function as % of normal (higher = better). **⚠️ glucose must be converted to mmol/L in the denominator** (divide mg/dL by 18.0182). | ✓ |
| **QUICKI** | 1 / (log₁₀(insulin_µU/mL) + log₁₀(glucose_mg/dL)) | Insulin sensitivity index. Range 0.30 (diabetic) to 0.45 (healthy). **⚠️ Uses base-10 logarithm, not natural log.** | ✓ |
| **TyG index** | ln((TG_mg/dL × glucose_mg/dL) / 2) | Insulin resistance proxy that does NOT require insulin measurement. TyG > 8.5 suggests IR on this 8.x-scale convention. **⚠️ Keep the `/2` inside the logarithm for consistency with the implemented artifact and most adult metabolic studies.** | ✓ |

**References:**
- **HOMA-IR, HOMA-β:** Matthews DR, Hosker JP, Rudenski AS, et al. "Homeostasis model assessment: insulin resistance and beta-cell function from fasting plasma glucose and insulin concentrations in man." *Diabetologia* 1985;28(7):412-419. PMID 3899825.
- **QUICKI:** Katz A, Nambi SS, Mather K, et al. "Quantitative Insulin Sensitivity Check Index: a simple, accurate method for assessing insulin sensitivity in humans." *J Clin Endocrinol Metab* 2000;85(7):2402-2410. PMID 10902785.
- **TyG index:** Simental-Mendía LE, Rodríguez-Morán M, Guerrero-Romero F. "The product of fasting glucose and triglycerides as surrogate for identifying insulin resistance in apparently healthy subjects." *Metab Syndr Relat Disord* 2008;6(4):299-304. PMID 19067533. Note that some papers use a 4.x-scale variant written as ln(TG × glucose) / 2; do not mix thresholds across conventions.

**⚠️ Unit warnings:**
- AI-READI measurement.csv stores **insulin in ng/L** (OMOP unit_concept_id 8725), NOT µU/mL. Convert to µU/mL by dividing by 0.04034 before applying HOMA-IR/QUICKI/HOMA-β formulas. Verified: median 0.6 ng/L ÷ 0.04034 = 14.9 µU/mL (expected for mixed diabetes cohort). The reference range in the CSV (0–24.9) appears unconverted (still in µU/mL).
- C-peptide has the same issue: labeled ng/L, values consistent with ng/mL.
- Glucose is in mg/dL (confirmed). The HOMA-β denominator requires mmol/L — divide by 18.0182.
- TyG index does NOT use insulin, so the insulin unit issue does not affect it.

**Status:** `homa_ir`, `tyg_index`, and `quicki` are implemented in `scripts/aging_scores.py` and written to `results/features/clinical_scores.parquet`. `HOMA-β` remains documented but is not currently written to the score artifact.

---

## 8. Summary Matrix

| Category | # Features | Input modality | Established software? | Effort | Priority for aging clocks | Priority for causal discovery |
|---|---|---|---|---|---|---|
| **CGM basic** (TIR 5-level, GRI, LBGI/HBGI) | ~10 | CGM JSON | `iglu`, `cgmquantify` | Trivial | Medium | High |
| **CGM temporal** (AGP, dawn phenomenon) | ~50+ | CGM JSON + timezone | `iglu` (partial) | Moderate | Medium | High |
| **CGM data quality** | ~5 | CGM JSON | Custom | Trivial | Low | Medium |
| **ECG HRV time-domain** | ~4 | ECG .dat | `neurokit2` | Trivial (once R-peaks done) | High | Medium |
| **ECG R-peak detection** | prerequisite | ECG .dat | `neurokit2`, `biosppy` | Moderate | High | Medium |
| **ECG HRV frequency** | ~3 | ECG .dat | `neurokit2` | Trivial | Medium | Low |
| **ECG signal quality** | ~4 | ECG .dat | `neurokit2` | Moderate | High | Low |
| **ECG morphology** | ~10 | ECG .dat | `neurokit2` | Substantial | Low | Low |
| **ECG embeddings** | 1 vector | ECG .dat | ECGFounder, HeartBEiT | Moderate | High | Low |
| **Sleep architecture** | ~10/night | Wearable sleep JSON | Custom | Moderate | High | High |
| **Circadian rhythm** | ~8 | Wearable HR/activity JSON | `pyActigraphy` | Moderate | High | High |
| **Activity/sedentary** | ~6/day | Wearable activity JSON | Custom | Moderate | Medium | High |
| **HR features** | ~5 | Wearable HR JSON + sleep | Custom | Moderate | High | Medium |
| **SpO2 overnight** | ~4 | Wearable SpO2 JSON + sleep | Custom | Easy | Medium | Medium |
| **Environmental light** | ~6 | Env CSV (spectral channels) | `luxpy` (if calibrated) | Moderate–Hard | Medium | High |
| **Environmental air quality** | ~4 | Env CSV (PM columns) | Custom | Trivial | Low | Medium |
| **Environmental screen time** | ~3 | Env CSV (screen, ff) | Custom | Trivial | Low | Medium |
| **Cross-modal coupling** | ~10 | CGM + HR aligned | `Tigramite`, `statsmodels` | Moderate | Medium | **Critical** |
| **Sleep–glucose** | ~3 | Sleep metrics + daily CGM | Custom | Moderate | Medium | **Critical** |
| **Activity–glucose** | ~3 | Activity bouts + CGM | Custom | Moderate | Medium | High |
| **FLIO decay fitting** | 4/pixel | FLIO DICOM | `scipy.optimize`, `gpufit` | **Substantial** | High | Low |
| **OCTA vessel metrics** | ~4 | OCTA enface DICOM | `skimage` | Substantial | High | Low |
| **DR grading** | 1 grade | CFP DICOM | RETFound | Substantial | Medium | Low |
| **Retinal age** | 1 score | CFP DICOM | RETFound / RetinaAge | Moderate | **Critical** | Low |
| **Insulin resistance** (HOMA-IR, HOMA-β, QUICKI, TyG) | 4 | Feature matrix (labs) | Custom (formulas) | **Trivial** (⚠️ verify units) | Medium | Medium |
| **UACR / albuminuria staging** | 2 | Feature matrix (labs) | Custom (formulas) | **Trivial** | Medium | Medium |
| ~~**eGFR / CKD stage**~~ | ~~3~~ | ~~Feature matrix~~ | ~~CKD-EPI 2021~~ | ~~Trivial~~ | ~~Medium~~ | ~~Medium~~ |
| | | | **⚠️ BLOCKED: requires sex (redacted in public release)** | | | |

### Implementation priority (what to build first)

**Tier 1 — Trivial effort, high value (build now):**
- CGM 5-level TIR, GRI, LBGI/HBGI (arithmetic on existing glucose array)
- Insulin resistance indices: HOMA-IR, HOMA-β, QUICKI, TyG (arithmetic on feature matrix — **⚠️ verify unit conversions**)
- UACR + albuminuria staging (arithmetic on feature matrix — eGFR/CKD staging is **NOT computable** due to sex redaction)
- CGM data completeness metrics

**Tier 2 — Moderate effort, high value (build next):**
- Sleep architecture per night (segment nights, compute SE/WASO/REM%)
- Per-day wearable summary table
- ECG R-peak detection + HRV time-domain (via `neurokit2`)
- CGM AGP + dawn phenomenon (requires local-time conversion)
- Circadian rhythm metrics (via `pyActigraphy` or custom)

**Tier 3 — Moderate effort, needed for specific analyses:**
- Cross-modal coupling (glucose–HR, sleep–glucose, activity–glucose)
- HR features (resting HR, nocturnal dip)
- ECG signal quality
- Environmental AQI, screen time

**Tier 4 — Substantial effort, separate workstream:**
- FLIO decay curve fitting
- OCTA vessel segmentation + FAZ
- Retinal age from RETFound
- DR grading
