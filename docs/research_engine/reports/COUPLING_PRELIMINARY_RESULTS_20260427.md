# Dynamic Coupling Preliminary Results

Date: 2026-04-27

## Executive Read

The network-physiology direction is worth pursuing, but the first result changes the framing.

The data do **not** support a simple "diabetes equals decoupling" story. In AI-READI, the strongest gradients show glucose-HR and glucose-activity coupling becoming more positive with diabetes severity. A more defensible thesis is:

> Type 2 diabetes is associated with altered, more rigid metabolic-autonomic-activity coupling, measurable from synchronized CGM and wearable streams.

This survives age/site adjustment and remains significant after additionally adjusting for HbA1c, BMI, raw glucose mean, HR mean, activity volume, and sleep fraction. That makes it more than a trivial glycemia/heart-rate level artifact.

## What Ran

Core coupling feature extraction:

- Script: `scripts/coupling/coupling_features.py`
- Output: `results/coupling_features.parquet`
- Cohort: 1,939 participants x 39 features
- Group counts:
  - Healthy: 668
  - Pre-diabetes lifestyle controlled: 477
  - Oral/non-insulin medication controlled: 576
  - Insulin dependent: 218

Core downstream analyses:

- `results/coupling_atlas.csv`
- `results/coupling_atlas_sensitivity.csv`
- `results/coupling_damage.csv`
- `results/coupling_prediction_performance.csv`
- `results/figures/coupling_atlas_top_heatmap.png`

Environment expansion:

- Slurm array: `50796803`, completed 32/32, exit code 0
- Postprocess: `50796838`, completed, exit code 0
- Output: `results/coupling_features_env.parquet`
- Atlas/damage/prediction:
  - `results/coupling_env_atlas.csv`
  - `results/coupling_env_damage.csv`
  - `results/coupling_env_prediction_performance.csv`

Cross-modal predictability:

- Slurm array: `50799001`, completed 32/32, exit code 0
- Postprocess: `50799036`, completed, exit code 0
- Output: `results/cross_modal_predictability.parquet`
- Atlas/damage:
  - `results/cross_modal_predictability_atlas.csv`
  - `results/cross_modal_predictability_damage.csv`

## Core Coupling Atlas

Top age/site-adjusted severity-gradient features:

| Feature | FDR p | Healthy vs insulin d | Healthy median | Insulin median |
|---|---:|---:|---:|---:|
| `glucose_hr_awake_r` | 1.30e-19 | 0.585 | -0.041 | 0.045 |
| `glucose_hr_spearman_r` | 1.86e-18 | 0.552 | 0.005 | 0.114 |
| `glucose_hr_partial_r_activity_sleep` | 2.16e-18 | 0.560 | 0.005 | 0.092 |
| `glucose_hr_zero_lag_r` | 2.69e-17 | 0.523 | -0.001 | 0.087 |
| `glucose_activity_spearman_r` | 1.04e-14 | 0.475 | -0.062 | -0.010 |
| `glucose_hr_peak_xcorr` | 1.04e-14 | 0.492 | 0.079 | 0.172 |

Interpretation:

- The flagship signal is glucose-HR coupling, especially awake glucose-HR correlation and glucose-HR rank correlation.
- The direction is increased positive coupling with severity, not lower coupling.
- The partial glucose-HR correlation adjusted for activity and sleep also increases, so the effect is not just "insulin-dependent participants walk less or sleep differently."
- Glucose-activity coupling also shifts with severity, but less strongly than glucose-HR.

## Sensitivity Check

I ran three severity-gradient models for each coupling feature:

- Base: age + clinical site
- Clinical: age + clinical site + HbA1c + BMI
- Clinical plus raw levels: age + clinical site + HbA1c + BMI + glucose mean + HR mean + activity total + sleep fraction

The core glucose-HR findings survive all three models:

| Feature | Clinical+levels severity coef | FDR p |
|---|---:|---:|
| `glucose_hr_awake_r` | 0.0223 | 5.34e-07 |
| `glucose_hr_spearman_r` | 0.0277 | 5.34e-07 |
| `glucose_activity_spearman_r` | 0.0157 | 8.22e-07 |
| `glucose_hr_zero_lag_r` | 0.0245 | 8.22e-07 |
| `glucose_hr_partial_r_activity_sleep` | 0.0173 | 7.96e-06 |

This is the main reason I think the project is still worth pursuing.

## Damage Links

Coupling features link to clinical/systemic burden, but not convincingly to retinal/cardiac structural age acceleration yet.

Strongest adjusted links:

- Frailty index:
  - `glucose_hr_awake_r`: FDR 2.18e-09, partial r 0.148
  - `glucose_hr_partial_r_activity_sleep`: FDR 2.18e-09, partial r 0.147
  - `glucose_hr_zero_lag_r`: FDR 2.18e-09, partial r 0.146
- Allostatic load:
  - `glucose_ms_entropy_s3`: FDR 4.40e-07, partial r 0.130
  - `glucose_ms_entropy_s1`: FDR 1.79e-06, partial r 0.122
- Homeostatic dysregulation:
  - `glucose_activity_spearman_r`: FDR 1.57e-09, partial r 0.151

Weak or null:

- Retinal age acceleration: no convincing FDR-significant coupling associations.
- Cardiac age acceleration: no convincing FDR-significant coupling associations.
- UACR: no convincing FDR-significant coupling associations.

Interpretation:

- The dynamic coupling signal currently looks more like a functional/clinical-burden marker than a structural imaging-damage marker.
- The retinal/cardiac damage bridge should remain a secondary aim until stronger features or longitudinal outcomes are available.

## Held-Out Prediction

Using the repository train/val/test split:

Coupling-only features:

| Outcome | Metric |
|---|---:|
| Insulin vs healthy | AUROC 0.805 |
| Any diabetes vs healthy | AUROC 0.650 |
| HbA1c | R2 0.144 |
| Frailty index | R2 0.191 |
| Allostatic load | R2 0.195 |
| Study-group ordinal | R2 0.105 |

Coupling + raw summary features:

- Insulin vs healthy AUROC rises to 0.952.
- HbA1c R2 rises to 0.674.

Interpretation:

- Coupling-only is genuinely informative, especially for severe diabetes vs healthy.
- But raw summary features dominate HbA1c prediction, as expected. Do not claim coupling replaces glycemic levels.
- The publishable claim should be "coupling adds a dynamic systems phenotype," not "coupling is the best glucose biomarker."

## Environment Results

Environment-inclusive matrix:

- Output: `results/coupling_features_env.parquet`
- Shape: 1,933 participants x 53 features
- PM2.5 features computed:
  - `pm25_glucose_*`
  - `pm25_hr_*`

PM2.5 results are weaker:

| Feature | FDR p | Healthy vs insulin d |
|---|---:|---:|
| `pm25_glucose_zero_lag_r` | 0.014 | 0.164 |
| `pm25_glucose_peak_abs_xcorr` | 0.080 | 0.154 |
| `pm25_hr_*` | mostly null | small |

Damage links:

- `pm25_glucose_peak_abs_xcorr` links to frailty and HbA1c after adjustment.
- PM2.5-HR is mostly weak/null.

Interpretation:

- Environment should not be the lead paper/story right now.
- It may be a secondary exposome angle, especially PM2.5-glucose coupling, but it needs stronger time-series controls before causal language.

## Cross-Modal Predictability

Output: `results/cross_modal_predictability.parquet`

Overall:

- `hr_from_glucose_activity_r2` median: 0.360
- `glucose_from_hr_activity_r2` median: -0.008
- `predictability_mean_r2` median: 0.158

Severity atlas:

| Feature | FDR p | Healthy vs insulin d |
|---|---:|---:|
| `predictability_min_r2` | 0.047 | -0.191 |
| `glucose_from_hr_activity_r2` | 0.074 | -0.168 |
| `hr_from_glucose_activity_r2` | 0.261 | -0.122 |

Interpretation:

- This is directionally interesting but not a lead result.
- Glucose becomes slightly less predictable from HR/activity with severity and is strongly related to HbA1c, but this score does not explain imaging damage or broad clinical burden well.
- If pursued, improve it with meal/activity timing, richer lags, circadian stratification, and robust per-person reliability before treating it as a digital biomarker.

## Literature Sanity Check

The broad premise is literature-supported, but the exact AI-READI result should be framed carefully.

- Bashan et al. established the network-physiology framing: physiological states have distinct network topology and transitions can reorganize interactions over minutes. This supports analyzing dynamic coupling, but their data were sleep-lab physiology, not free-living diabetes. Source: Nature Communications 2012, https://www.nature.com/articles/ncomms1705
- Scheer et al. showed controlled circadian misalignment can adversely affect glucose/insulin/leptin and cardiovascular physiology. This supports circadian-metabolic mechanisms, but AI-READI observational data cannot infer this causally without stronger controls. Source: PNAS 2009, https://pmc.ncbi.nlm.nih.gov/articles/PMC2657421/
- HR/HRV has prospective links to incident T2D in population data, supporting autonomic-metabolic relevance. Source: JCEM 2023, https://academic.oup.com/jcem/article/108/10/2510/7110036
- CGM complexity/function-representation work supports moving beyond mean glucose. Sources: Am J Physiol 2014, https://pubmed.ncbi.nlm.nih.gov/24808497/ and Scientific Reports 2025, https://www.nature.com/articles/s41598-025-18119-2
- PCMCI/PCMCI+ is reasonable for later multivariate time-series causal discovery, but it should not be used as a first result without reliability checks. Sources: Nature Communications 2019, https://www.nature.com/articles/s41467-019-10105-3 and UAI 2020, https://proceedings.mlr.press/v124/runge20a.html

## Recommended Direction

Lead with:

1. Glucose-HR/activity coupling atlas across diabetes severity.
2. Sensitivity showing the result survives HbA1c, BMI, raw glucose/HR/activity/sleep summaries.
3. Clinical burden links: frailty, allostatic load, homeostatic dysregulation.
4. Held-out biomarker check: coupling-only insulin-vs-healthy AUROC around 0.80.

Do not lead with:

- Retinal/cardiac damage links. Current evidence is weak.
- PM2.5 causal pathway. Current evidence is small and needs stronger time-series controls.
- Cross-modal predictability as a flagship biomarker. Current result is secondary.
- A foundation model/JEPA. Classical signal features already produce interpretable signal; learned representations should wait.

Next best technical runs:

1. Reliability: bootstrap per-participant coupling features; 7-day vs 10-day stability.
2. Circadian stratification: awake/day/night-specific glucose-HR coupling.
3. Lag asymmetry: glucose leads HR vs HR leads glucose, with lag sign conventions made explicit.
4. Medication sensitivity where possible from public proxies: healthy/preDM/oral/insulin; maybe exclude beta-blocker-like HR outliers if medication data remain redacted.
5. Replace the fast Shannon entropy proxy with formal sample entropy/multiscale entropy for the top glucose complexity findings only.
6. For PM2.5, rerun with within-person detrending, time-of-day, temperature/humidity, and autocorrelation controls before making claims.
