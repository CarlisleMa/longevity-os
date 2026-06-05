# OCT/OCTA Exploration

This note records the first pass at making the MoCA project more retinal
structure / neurovascular focused.

## Why OCT/OCTA

The fundus RETFound path is broad and generic. For brain/neurodegeneration
framing, OCT/OCTA is more directly aligned with:

- retinal neural structure
- macular and optic nerve anatomy
- microvascular flow patterns
- neurovascular coupling / small-vessel disease relevance

So the sharper project question becomes:

> Do retinal neural and microvascular imaging features map to MoCA cognitive
> function beyond standard clinical/metabolic metadata?

## Local Data Inventory

From the AI-READI manifests:

- Structural OCT: 56,477 acquisitions from 2,266 participants
- OCTA: 24,560 acquisitions from 2,264 participants
- MoCA with OCT: 2,256 participants
- MoCA with OCTA: 2,254 participants

For a cleaner first pass, we used one canonical OCTA protocol:

```text
Topcon Maestro2, Macula, 6 x 6
```

This yielded:

- 4,506 OCTA acquisitions
- 2,199 participants
- 2,189 participants with MoCA
- test split: 330 participants

## What Was Extracted

Script:

```bash
python -m neuro_moca_mapping.extract_octa_biomarkers --workers 1 --skip-segmentation
```

Output:

```text
results/neuro_moca_mapping/octa_maestro2_macula_6_x_6_enface_only_participant_features.parquet
```

Feature type:

- en face layer 1-4 intensity summaries
- Otsu flow-fraction proxy
- foreground intensity
- entropy
- row/column banding coefficients
- left/right asymmetry summaries

This is an OCTA en face proxy feature set, not a final vessel-density or
segmentation-derived neuroretinal thickness feature set.

## First MoCA Results

Script:

```bash
python -m neuro_moca_mapping.run_octa_moca_mapping
```

Output:

```text
results/neuro_moca_mapping/octa_model_performance.csv
results/neuro_moca_mapping/octa_incremental_performance.csv
results/neuro_moca_mapping/octa_domain_performance.csv
results/neuro_moca_mapping/octa_analysis_summary.json
```

### `moca_total` Regression

| Model | Test R2 | Test MAE | Pearson r |
| --- | ---: | ---: | ---: |
| Demographics | 0.051 | 2.80 | 0.237 |
| Clinical/metabolic | -0.013 | 2.70 | 0.238 |
| OCTA en face biomarkers | -0.007 | 2.83 | 0.088 |
| Clinical + OCTA | -0.048 | 2.76 | 0.190 |

### `moca_total < 26` Classification

| Model | Test AUROC | Test AUPRC | Balanced accuracy |
| --- | ---: | ---: | ---: |
| Clinical/metabolic | 0.677 | 0.588 | 0.629 |
| Clinical baseline on OCTA cohort | 0.673 | 0.579 | 0.622 |
| Clinical + OCTA en face biomarkers | 0.627 | 0.537 | 0.576 |
| OCTA en face biomarkers only | 0.528 | 0.429 | 0.529 |

Incremental test performance from adding OCTA en face features:

- `moca_total`: delta R2 = -0.022
- `moca_total < 26`: delta AUROC = -0.046

## Interpretation

This is negative for the current OCTA en face proxy path.

It does not show that OCT/OCTA generally has no brain-relevant signal. It shows
that simple intensity/threshold features from Maestro2 macula 6 x 6 en face
OCTA do not improve MoCA prediction beyond clinical/metabolic metadata.

The next OCT/OCTA route should be more anatomically grounded:

- use segmentation heightmaps for layer-thickness proxies
- extract true vessel-density / perfusion-density features rather than simple
  image-intensity proxies
- model MoCA residuals after age/site/clinical adjustment
- prioritize MoCA domains, especially delayed recall and executive/visuospatial
  scores

## Recommendation

Do not use the current en face OCTA proxy as a positive result.

The defensible next experiment is:

```text
OCTA segmentation-derived layer thickness + true plexus vessel density
    -> residual MoCA / MoCA domains
```

That is more neurodegeneration-facing than both fundus RETFound embeddings and
simple OCTA intensity summaries.

