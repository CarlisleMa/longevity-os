# Model Artifacts

The **bridge** between the AI-READI research engine and LongevityOS: small frozen models +
reference statistics that let the app score one person consistently. Weights live here locally
and are **gitignored** (`weights/`). This README is the export checklist (BUILD_GUIDE Phase 1).

## What goes here

```text
model_artifacts/
  weights/                       # gitignored — large frozen encoders, copied locally
    RETFound_cfp_weights.pth     # retinal foundation encoder
    ecgfounder/12_lead_ECGFounder.pth
  clocks/
    unified_clock.joblib         # fitted aging clock (model + scaler + imputer in a Pipeline)
    system_clocks.joblib         # per-system clocks
  reference/
    feature_stats.json           # train-set means/stds for each feature (consistent normalization)
    age_accel_percentiles.json   # cohort percentile tables → place an individual in context
    subtype_centroids.json       # optional: aging-subtype reference points
  MANIFEST.json                  # what was exported, from which AI-READI commit, when
```

## Export checklist (run in the AI-READI repo)

1. **Fit/locate the frozen clocks.** After training in AI-READI, persist the *Pipeline*
   (imputer + scaler + Ridge) with `joblib.dump(pipe, "unified_clock.joblib")`. Do **not** refit
   here — LongevityOS only applies.
2. **Export train-set stats.** Save the training-split feature means/stds to `feature_stats.json`
   so an individual's features are normalized exactly as the cohort was.
3. **Export reference percentiles.** Save AgeAccel (and subtype) quantiles from the training/held
   cohort to `age_accel_percentiles.json` for "you are in the Nth percentile" context.
4. **Copy encoder weights** into `weights/` (kept local; ~2.7 GB for RETFound + ECGFounder).
5. **Write `MANIFEST.json`** recording the source commit, date, and file list.

## How the backend uses these

`backend/.../services/scoring_service.py:score_live()` loads `clocks/*.joblib` + `reference/*`,
builds the feature vector with `engine/science` formulas, predicts biological age, places it on
the reference percentiles, and diffs against the user's own baseline. Until artifacts exist, the
backend runs in **representative mode** (serves the synthetic demo user) and `/api/meta` reports
`scoring_live: false`.

## Data ethics

Reference statistics are **aggregates** (means/quantiles), not participant rows — safe to keep
locally. Do not commit raw participant data or anything that could re-identify individuals.
