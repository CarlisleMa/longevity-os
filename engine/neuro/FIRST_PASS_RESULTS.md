# First-Pass MoCA Mapping Results

Run on 2026-05-21:

```bash
python -m neuro_moca_mapping.run_moca_mapping
```

Outputs:

```text
results/neuro_moca_mapping/
```

## Cohort

- MoCA-available participants: 2,265
- `moca_total < 26`: 927 participants, 40.9%
- Test split: 349 participants, 148 with `moca_total < 26`

## Leakage Guard

The analysis excludes all `moca_*` predictors, `moca_low_lt26`,
`cognitive_predicted_age`, and `cognitive_age_accel`.

## Main Test Results

### `moca_total` Regression

| Model | Test R2 | Test MAE | Pearson r |
| --- | ---: | ---: | ---: |
| Retina image embeddings | 0.079 | 2.69 | 0.287 |
| Physiology only | 0.062 | 2.72 | 0.261 |
| Demographics | 0.051 | 2.80 | 0.237 |
| Full multimodal | 0.023 | 2.69 | 0.265 |
| Clinical/metabolic | -0.013 | 2.70 | 0.238 |

### `moca_total < 26` Classification

| Model | Test AUROC | Test AUPRC | Balanced accuracy |
| --- | ---: | ---: | ---: |
| Clinical/metabolic | 0.677 | 0.588 | 0.629 |
| Clinical + retina age gap | 0.677 | 0.588 | 0.631 |
| Clinical + retina image embeddings | 0.669 | 0.597 | 0.626 |
| Full multimodal | 0.667 | 0.582 | 0.608 |
| Retina image embeddings | 0.631 | 0.547 | 0.600 |
| Demographics | 0.618 | 0.513 | 0.589 |
| Physiology only | 0.605 | 0.524 | 0.589 |

## Incremental Value Over Clinical/Metabolic Baseline

On the test split:

| Contrast | Delta R2 | Delta AUROC |
| --- | ---: | ---: |
| Add retinal embeddings | +0.002 | -0.008 |
| Add retinal age gap | +0.001 | +0.000 |
| Add physiology | +0.010 | -0.021 |
| Add retina + physiology | +0.036 | -0.010 |

## Interpretation

This supports the project direction but not a strong claim yet.

Retina-only and physiology-only models show weak-to-modest MoCA signal, with
retinal embeddings slightly stronger than demographics for `moca_total`
regression. For low-MoCA classification, the clinical/metabolic baseline is
stronger, and adding retina or physiology does not improve AUROC in this first
linear model ladder.

The defensible current claim is:

> AI-READI retinal and physiologic modalities contain measurable but modest
> cognitive-function signal, motivating a more targeted eye-brain-metabolism
> mapping analysis.

The current results do not yet support:

> Multimodal retinal/physiology features robustly improve low-cognition
> screening beyond clinical/metabolic metadata.

## Next Analyses

Recommended next steps:

- Add PCA/PLS compression of RETFound embeddings before supervised modeling.
- Calibrate regression predictions on the validation split.
- Test nonlinear baselines available in sklearn, especially random forest and
  histogram gradient boosting.
- Run split sensitivity with `balanced_split_v1`.
- Prioritize MoCA domain targets where signal looks more plausible, especially
  delayed recall and trails/executive-visuospatial measures.
- Consider raw-image fine-tuning only if embedding-level signal remains stable
  under sensitivity checks.

## OCTA En Face Follow-Up

An OCTA-specific en face feature extraction was added after this first pass.
Using Topcon Maestro2 macula 6 x 6 en face proxy features from 2,189
MoCA-available participants:

- OCTA-only low-MoCA AUROC: 0.528
- clinical baseline on the OCTA cohort AUROC: 0.673
- clinical + OCTA en face AUROC: 0.627
- adding OCTA en face features changed test AUROC by -0.046

So the en face proxy feature route is also negative for incremental prediction.
This does not close the OCT/OCTA direction; the next biologically grounded test
should use segmentation-derived layer thickness and true vessel-density /
perfusion-density features.
