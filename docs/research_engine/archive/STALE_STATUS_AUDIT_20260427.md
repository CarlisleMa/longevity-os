# Stale Status Audit - 2026-04-27

Archive note, 2026-04-29: this file is preserved as a historical audit of
stale implementation claims found on 2026-04-27. For current repository status,
use `docs/CURRENT_STATUS.md`.

This audit checks the specific pre-paper concerns against the current scripts,
result schemas, and documentation. It is intentionally an audit, not a code
change. No analysis outputs were regenerated.

## Executive Summary

The stale status is real, but it is concentrated in a few places:

1. `scripts/biomarker_prediction.py` has two real column-name bugs. The
   circadian insulin-resistance analysis falls back to `heart_rate` even though
   wearable circadian features exist, and the CGM-vision analysis omits
   `cgm_cv_glucose` because it looks for stale `cgm_cv`.
2. `scripts/cross_dimensional.py` is stale relative to the imaging clocks. It
   still analyzes only 13 system/functional clocks and omits
   `retinal_age_accel` and `cardiac_age_accel`.
3. `scripts/unified_clock.py` is not missing retinal/cardiac clocks. It already
   loads them. The problem is conceptual: the current objective predicts
   chronological age from age-acceleration residuals, which is not strong enough
   to carry a primary paper claim.
4. `scripts/causal_analysis.py` is usable as an exploratory baseline, not as
   publication-grade causal evidence. Sleep-Granger has too few within-person
   days, PM2.5-HR needs stronger time-series controls, and PCMCI was not
   regenerated in the current causal summary.
5. Several docs still describe already-implemented features as "not
   implemented" or list scripts as "to create." These should be refreshed before
   paper writing or external sharing.

## Evidence Checked

Current result schemas:

- `results/multimodal_features.parquet`: 2,280 rows x 48 columns.
- Current circadian columns present: `wear_ra`, `wear_is`, `wear_iv`,
  `wear_cosinor_amplitude`.
- Stale circadian columns absent: `circ_ra`, `circ_is`, `circ_iv`,
  `cosinor_amplitude`.
- Current CGM variability columns present: `cgm_cv_glucose`, `cgm_mage`,
  `cgm_gri`, `cgm_hbgi`.
- Stale CGM column absent: `cgm_cv`.
- `results/age_accel.parquet` contains 13 system/functional age-acceleration
  columns.
- `results/retinal_age_accel.parquet` contains `retinal_age_accel`.
- `results/cardiac_age_accel.parquet` contains `cardiac_age_accel`.
- `results/aging_subtypes.csv` and `results/concordance_matrix.csv` still
  contain only the 13 non-imaging clocks.

Current generated evidence:

- `results/biomarker_circadian_ir.csv` contains only `heart_rate`, proving the
  circadian analysis used the fallback path.
- `results/biomarker_cgm_vision.csv` contains `cgm_mage`, `cgm_gri`, and
  `cgm_hbgi`, but not `cgm_cv_glucose`.
- `results/concordance_matrix.csv` is 13 x 13 and has no retinal/cardiac labels.
- `results/unified_clock_performance.csv` reports final test MAE 8.193,
  R2 0.1678, Pearson r 0.4277 for the current unified clock.
- `results/causal_summary.json` reports sleep-Granger 0 FDR discoveries in both
  directions and a targeted refresh where PCMCI was not regenerated.

## Code Updates Needed

### 1. `scripts/biomarker_prediction.py`

Status: real code bug.

Current stale references:

- Circadian analysis uses:
  - `circ_ra`
  - `circ_is`
  - `circ_iv`
  - `cosinor_amplitude`
- Current output columns are:
  - `wear_ra`
  - `wear_is`
  - `wear_iv`
  - `wear_cosinor_amplitude`
  - plus `wear_m10`, `wear_l5`, `wear_cosinor_acrophase`,
    `wear_cosinor_mesor`.
- CGM-vision analysis uses:
  - `cgm_cv`
  - `cgm_mage`
  - `cgm_gri`
  - `cgm_hbgi`
- Current CV column is:
  - `cgm_cv_glucose`

Recommended fix:

- Replace the hard-coded `circ_targets` with `WEARABLE_CIRC`, or at least with
  the four current `wear_*` names.
- Replace `cgm_cv` with `cgm_cv_glucose`.
- Prefer using the already-defined `CGM_FEATURES` constant and then selecting a
  narrower display order if the visual-acuity analysis should stay focused on
  variability.
- Consider a small alias map if old result files need backward compatibility:
  `circ_ra -> wear_ra`, `circ_is -> wear_is`, `circ_iv -> wear_iv`,
  `cosinor_amplitude -> wear_cosinor_amplitude`, `cgm_cv -> cgm_cv_glucose`.

Outputs to regenerate after the fix:

- `results/biomarker_circadian_ir.csv`
- `results/figures/circadian_ir_scatter.png`
- `results/biomarker_cgm_vision.csv`
- Any deck/table that quotes biomarker findings.

### 2. `scripts/cross_dimensional.py`

Status: real implementation drift.

The script defines:

- 7 system clocks.
- 6 functional clocks.
- `ALL_CLOCKS = SYSTEM_CLOCKS + FUNCTIONAL_CLOCKS`.

It does not load or include:

- `results/retinal_age_accel.parquet`
- `results/cardiac_age_accel.parquet`

This is stale because imaging clocks are now implemented and present. The
unified clock loader already has the right pattern in `_get_age_accel_columns`.

Recommended fix:

- Add an `IMAGING_CLOCKS` group:
  - `retinal_age_accel`
  - `cardiac_age_accel`
- Load retinal/cardiac parquet outputs in `cross_dimensional.py`, align by
  participant index, and join them before `_available_clocks`.
- Update titles and labels from "13 clocks" to dynamic counts.
- Recompute subtype clustering with imaging clocks included. Do not just append
  them to old CSVs; clustering and concordance should be recomputed.

Outputs to regenerate after the fix:

- `results/concordance_matrix.csv`
- `results/aging_subtypes.csv`
- `results/diabetes_gradient.csv`
- `results/predictive_hierarchy.csv`
- `results/study_summary.json`
- Cross-dimensional figures under `results/figures/`.

### 3. `scripts/unified_clock.py`

Status: not stale by schema, but weak by objective.

Important distinction:

- It already loads `age_accel.parquet`, `retinal_age_accel.parquet`, and
  `cardiac_age_accel.parquet`.
- The stale issue is not missing imaging clocks.
- The issue is that it predicts chronological age using residualized
  age-acceleration dimensions as inputs, then residualizes the result again.

Why this needs redesign before paper use:

- Age-acceleration residuals are constructed to remove linear chronological age.
  Training a chronological-age predictor from those residuals creates a
  hard-to-interpret stacked clock.
- The current test performance is modest: MAE 8.193, R2 0.1678, Pearson r 0.4277.
- The resulting `unified_age_accel` also performed poorly as a diabetes-severity
  discriminator in earlier review, so it should not be a flagship result in its
  current form.

Recommended options:

- Conservative option: rename/reframe it as an exploratory stacked
  age-acceleration score, not a primary "unified multimodal clock."
- Better age-clock option: train a direct multimodal age predictor from raw
  clinical, CGM, wearable, environmental, ECG, retinal, and cardiac features or
  embedding PCs, then compute age acceleration once.
- Disease-physiology option: train a diabetes severity, insulin dependence,
  frailty, or network-uncoupling score and stop forcing it to be an age clock.
- If retained, report it only with strict train/validation/test separation and
  compare against simpler baselines: chronological age, KDM, multimodal feature
  clock, retinal clock, and age-acceleration mean/PC1.

Outputs to regenerate if redesigned:

- `results/unified_age_accel.parquet`
- `results/unified_clock_performance.csv`
- Unified-clock figures and deck claims.

### 4. `scripts/causal_analysis.py`

Status: baseline exploratory analysis, not paper-grade causal inference.

Sleep -> glucose Granger:

- Current output has 1,305 tested participants.
- Valid tests: 1,279 sleep-to-glucose and 1,297 glucose-to-sleep.
- FDR discoveries: 0 in both directions.
- Each participant has roughly a 10-day window, so per-person Granger tests are
  underpowered and unstable even if many participants are tested.

Recommended update:

- Keep current results as negative/exploratory.
- For a stronger analysis, switch to pooled within-person panel models:
  next-day glucose/TIR as outcome, lagged sleep metrics as predictors, participant
  random intercepts or fixed effects, day index, site, diabetes group, weekday,
  and prior-day glucose adjustment.

Glucose-HR coupling:

- Current method is cross-correlation and lag selection, not causal discovery.
- Summary: n=1,479, median optimal lag -20 minutes, mean Pearson r 0.023, strong
  group difference by Kruskal-Wallis.

Recommended update:

- Treat as a promising network physiology signal.
- Add within-person null/permutation controls and adjust for activity/sleep
  state where possible.

PM2.5 -> HR:

- Current method is lagged OLS per participant, adjusted only for hour-of-day
  sine/cosine terms.
- It reports many FDR-significant tests across lags, but this is not yet
  credible enough because 5-minute HR and PM2.5 are highly autocorrelated and
  confounded by sleep, activity, temperature, humidity, time of day, and site/home
  context.

Recommended update:

- Add autoregressive HR terms.
- Add lagged PM2.5 distributed-lag structure rather than selecting the minimum
  p-value across lags.
- Adjust for sleep/wake or activity state, temperature, humidity, day/night,
  weekday, participant fixed effects or random intercepts.
- Use cluster-robust/HAC standard errors or block bootstrap.
- Report effect sizes in bpm per 10 ug/m3 PM2.5, not only p-values.

PCMCI:

- Current summary says it was not regenerated in the targeted refresh.
- If paper claims include DAGs, rerun the DAG step in the locked environment and
  archive exact parameters.

## Documentation Updates Needed

### `docs/reference/DERIVED_FEATURES.md`

Status: heavily stale.

Update from "not implemented" to current status:

- CGM:
  - 5-level TIR is implemented in scalar form.
  - GRI is implemented.
  - LBGI/HBGI are implemented.
  - MAGE is implemented.
  - Dawn/nocturnal features are implemented.
  - AGP percentile curves are implemented in the loader but not saved as scalar
    columns in `multimodal_features.parquet`.
  - Data completeness is implemented in `compute_cgm_metrics`, but not currently
    saved into `multimodal_features.parquet`.
- ECG:
  - Device-reported intervals are available and used.
  - ECGFounder embeddings and cardiac age are implemented.
  - R-peak detection, HRV, signal quality, and morphology remain deferred.
- Wearable:
  - Sleep architecture, circadian metrics, activity summary, and HR summary are
    implemented and saved to `multimodal_features.parquet`.
  - SpO2, stress, and respiratory-rate daily summaries are computed by
    `features_wearable.py`, but not saved into the current multimodal aggregate.
- Environment:
  - Mean/max PM2.5, bright-light hours proxy, evening light proxy, mean temp,
    temp range, and humidity are implemented.
  - Melanopic EDI, AQI category, screen-time summaries, comfort-zone time, and
    PM2.5 event detection remain deferred.
- Cross-modal:
  - Glucose-HR coupling and sleep-glucose baseline analyses are implemented in
    `causal_analysis.py`.
  - Transfer entropy, robust causal discovery, activity-glucose, and
    environment-glucose interactions remain deferred.
- Retinal:
  - RETFound embeddings and retinal age clock are implemented.
  - OCT/OCTA/FLIO biomarker extraction, image quality scoring, and DR grading
    remain deferred.

### `docs/reference/LOADING.md`

Status: stale limitations section.

Update:

- Disk cache sizes: `feature_matrix.parquet` is currently 381 KB, not 179 KB.
  `participant_index.parquet` remains about 179 KB.
- "Current Limitations" should no longer say CGM GRI, dawn phenomenon, wearable
  sleep/circadian summaries, glucose-HR coupling, and sleep-vs-glucose are not
  implemented.
- Keep the limitations for ECG HRV, categorical alignment, full PyTorch
  Dataset/DataLoader abstractions, retinal biomarker extraction, and statistical
  utilities.
- Reword "pre-computed feature caches for all derived metrics" because several
  derived metrics are now cached, but not all possible derived metrics.

### `docs/design/IMPLEMENTATION_ROADMAP.md`

Status: stale as a roadmap.

Update:

- Change top status from "ready to implement" to "implemented baseline, pending
  paper-readiness fixes."
- Mark implemented scripts as done:
  - `scripts/aging_scores.py`
  - `scripts/aging_features_batch.py`
  - `scripts/aging_clocks.py`
  - `scripts/cross_dimensional.py`
  - `scripts/retinal_age.py`
  - `scripts/cardiac_age.py`
  - `scripts/causal_analysis.py`
  - `scripts/biomarker_prediction.py`
  - `scripts/unified_clock.py`
- Replace "Files to Create" with "Implemented files and missing wrappers."
- Missing wrappers/artifacts:
  - `configs/feature_batch.slurm`
  - `configs/retinal_age.slurm`
  - `configs/cardiac_age.slurm`
  - `notebooks/aging_atlas.ipynb`
- Note that `configs/imaging_clocks.slurm` exists and covers retinal/cardiac
  imaging jobs.
- Update the expected `multimodal_features.parquet` shape from about 60 columns
  to the current 48 columns, unless new features are added.

### `agents/modality/retinal.py`

Status: stale agent prompt.

Update:

- The prompt says RETFound embeddings are not extracted and should be treated as
  a future capability.
- Current outputs include `results/retinal_embeddings.parquet` and
  `results/retinal_age_accel.parquet`.
- Keep the warning that OCT/OCTA/FLIO pixel biomarker extraction is not
  implemented.

### `agents/reasoning/aging_clock.py`

Status: stale agent prompt.

Update:

- The prompt says retinal age is "not yet available."
- Current retinal age and cardiac age outputs exist.
- Add the current distinction:
  - RETFound retinal age is available.
  - ECGFounder cardiac age is available.
  - OCT/OCTA/FLIO hand-engineered retinal biomarkers remain deferred.

### `docs/design/AGENT_SYSTEM_BRAINSTORM.md`

Status: mostly historical, but needs labeling.

Recommended update:

- Either mark it clearly as a historical brainstorm from 2026-04-24 or refresh
  status language to reflect that the agent package exists.
- The note that OCTA vessel density is not implemented remains accurate.

### `docs/design/INFRASTRUCTURE_PLAN.md`

Status: mostly current.

It already correctly lists many implemented derived features. The only
clarification needed is that "Layer 4 ML pipeline not yet started" refers to
general PyTorch Dataset/DataLoader infrastructure, not to the separate retinal
and ECG foundation-model embedding/age-clock scripts, which now exist.

### `docs/decks/project_deck.md`

Status: stale for paper use.

Update:

- The deck still says "training script provenance missing" for a saved
  multimodal clock artifact. That should either be resolved by finding the exact
  generating script/command, or the claim should be removed.
- The current `scripts/unified_clock.py` result is not the MAE 5.2/R2 0.65
  artifact. Keep these as separate analyses:
  - `multimodal_clock_age_accel.parquet`: saved artifact with strong age
    prediction but provenance needs restoration.
  - `unified_clock.py`: current stacked age-acceleration model, MAE 8.193,
    R2 0.1678.
- Any "15 aging dimensions" claim should specify whether retinal/cardiac are
  included in the particular table/figure being shown.

### `README.md`

Status: mostly current.

Optional update:

- Add a "Known paper-readiness issues" section linking to this audit.
- Mention that `biomarker_prediction.py` and `cross_dimensional.py` need reruns
  after the column and imaging-clock fixes.

## Recommended Update Order

1. Fix `biomarker_prediction.py` column references and rerun biomarker outputs.
2. Update `cross_dimensional.py` to include retinal and cardiac clocks, then
   rerun cross-dimensional outputs.
3. Decide whether to redesign or demote the current unified clock. Do this
   before updating deck claims.
4. Reframe causal outputs as exploratory baseline unless the stronger
   time-series models are implemented.
5. Refresh `DERIVED_FEATURES.md`, `LOADING.md`, `IMPLEMENTATION_ROADMAP.md`, and
   stale agent prompts.
6. Regenerate or edit `docs/decks/project_deck.md` only after the code outputs above
   are stable.

## Paper-Readiness Classification

Ready to cite with minor cleanup:

- Cohort/dataset coverage.
- Clinical score formulas, with unit caveats.
- Individual system and functional clocks, subject to the usual split and
  missingness reporting.
- Retinal and cardiac imaging clocks as standalone outputs.

Needs code fix and rerun:

- Circadian insulin-resistance biomarker analysis.
- CGM-vision biomarker analysis if CV should be included.
- Cross-dimensional subtype/concordance/gradient analysis with imaging clocks.

Needs conceptual redesign or demotion:

- Current unified clock.

Needs stronger methods before causal wording:

- PM2.5-HR.
- Sleep-Granger.
- PCMCI/DAG claims.
