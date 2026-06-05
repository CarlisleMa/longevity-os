# Neuro MoCA Mapping

This directory keeps the brain/neurodegeneration-facing AI-READI work separate
from the aging-clock analyses.

The working hypothesis is:

> Non-invasive AI-READI modalities, especially retinal imaging and continuous
> cardiometabolic physiology, contain signal that maps to cognitive function as
> measured by MoCA.

This is not a dementia or Parkinson's classifier. AI-READI has too few diagnosed
neurodegenerative cases for that to be the primary claim. MoCA is used here as a
brain-relevant bridge phenotype.

## First-pass analysis

Run:

```bash
python -m neuro_moca_mapping.run_moca_mapping
```

The script trains a model ladder for:

- `moca_total` regression
- `moca_total < 26` classification
- selected MoCA subdomain regression targets

It explicitly excludes all MoCA-derived predictors and cognitive age-clock
columns from the feature matrix to avoid target leakage.

Regression predictions are bounded to the valid target range so models cannot
score outside the MoCA scale.

Generated outputs are written to:

```text
results/neuro_moca_mapping/
```

The most important files are:

- `cohort_summary.csv`
- `feature_blocks.csv`
- `model_performance.csv`
- `incremental_performance.csv`
- `domain_performance.csv`
- `analysis_summary.json`
- `figures/`

The key interpretation should focus on incremental value:

```text
Does retina or continuous physiology improve MoCA prediction beyond
demographics and standard metabolic/clinical metadata?
```

## OCTA Exploration

A first OCTA-specific path is also available:

```bash
python -m neuro_moca_mapping.extract_octa_biomarkers --workers 1 --skip-segmentation
python -m neuro_moca_mapping.run_octa_moca_mapping
```

This extracts hand-engineered en face OCTA intensity/flow-proxy features from
the canonical Topcon Maestro2 macula 6 x 6 protocol and tests whether they add
MoCA signal beyond the clinical/metabolic baseline.

Use segmentation extraction separately when ready:

```bash
python -m neuro_moca_mapping.extract_octa_biomarkers --workers 1
```

The segmentation path reads larger DICOM heightmaps and is slower, but it is
the more biologically relevant route for layer-thickness proxies.
