# Foundation JEPA Sequence Experiments

This subtree is isolated from the existing agent work and from the participant
level JEPA prototype. It reads raw CGM, Garmin wearable, environment, clinical,
RETFound, and ECGFounder artifacts, and writes only under
`foundation_jepa/sequence/artifacts/` by default.

## What This Implements

- fixed 10-day, 5-minute aligned sequence tensors
- explicit missingness masks instead of aggressive interpolation
- reset-aware active-calorie deltas rather than raw cumulative Garmin calorie
  counter values
- PatchTST-style temporal Transformer encoders for:
  - CGM
  - wearable HR/activity/sleep
  - environment PM/light/temperature/humidity
- projection encoders for existing RETFound and ECGFounder embeddings
- a tabular clinical projection encoder
- JEPA objective: predict each available target modality latent from the other
  available modalities
- optional age and diabetes-severity grounding heads
- split-preserving shuffled-modality controls and modality ablations
- frozen linear probes on the learned pooled representation for objective
  ablations where the supervised age head is intentionally disabled

Only retinal and ECG use true pretrained foundation-model embeddings today.
The sequence encoders use an off-the-shelf PatchTST-style architecture, trained
inside this experiment. This is the appropriate first version because generic
time-series pretrained weights may not match CGM/Garmin/environment data without
careful validation.

## Current Training Objective

For each participant, the model encodes every available modality into a latent
vector:

- sequence encoders: CGM, wearable, environment
- static encoders: clinical table, RETFound retinal embedding, ECGFounder
  cardiac embedding

The default full GPU run optimizes:

```text
loss = 1.0 * JEPA_MSE + 1.0 * age_MSE_z + 0.2 * severity_CE
```

`JEPA_MSE` is the mean over available target modalities. For target modality
`m`, the model pools the other available modality latents as context, predicts
`m`'s latent through a small predictor, and matches the detached target latent
with MSE. The target latent is stop-gradient only for that target prediction;
the same encoder still receives gradients when it serves as context for other
targets and through the supervised heads.

`age_MSE_z` predicts z-scored chronological age from the availability-weighted
pooled latent. `severity_CE` predicts the diabetes-severity class from the same
pooled latent.

This means the current headline test MAE is not a pure self-supervised JEPA
metric. It is a joint representation plus aging-clock objective. Pure JEPA runs
should be judged with the frozen linear-probe metrics written to
`probe_predictions.csv` and `summary.json`.

## Smoke Test

```bash
/home/mazijian/miniforge3/envs/aireadi/bin/python -m foundation_jepa.sequence.train \
  --limit 32 \
  --epochs 1 \
  --batch-size 8 \
  --latent-dim 32 \
  --model-dim 64 \
  --layers 1 \
  --device cpu \
  --output-dir foundation_jepa/sequence/artifacts/smoke
```

## GPU Pilot

```bash
sbatch foundation_jepa/sequence/slurm/sequence_jepa_pilot_gpu.slurm
```

The pilot writes to `foundation_jepa/sequence/artifacts/pilot_gpu/`.
For a bounded first Slurm run:

```bash
sbatch --export=ALL,LIMIT=256,EPOCHS=5 foundation_jepa/sequence/slurm/sequence_jepa_pilot_gpu.slurm
```

## Next-Stage Ablation Suite

The next-stage suite tests whether signal comes from synchronized 10-day
streams, static clinical/imaging shortcuts, or the supervised clock objective.

Included configs:

- `full_joint`
- `shuffle_all_joint`
- `shuffle_sequences_joint`
- `drop_clinical_joint`
- `drop_imaging_joint`
- `sequence_only_joint`
- `static_only_joint`
- `full_pure_jepa`
- `sequence_only_pure_jepa`
- `full_age_only`

Create a manifest:

```bash
/home/mazijian/miniforge3/envs/aireadi/bin/python -m foundation_jepa.sequence.experiment_suite make-manifest \
  --suite next_stage \
  --seeds 42,43,44 \
  --output-root foundation_jepa/sequence/artifacts/next_stage \
  --manifest foundation_jepa/sequence/artifacts/next_stage/manifest.jsonl
```

Submit the GPU array. The upper array index should be one less than the manifest
row count; the default `next_stage` suite with three seeds has 30 rows.

```bash
sbatch --array=0-29 --export=ALL,MANIFEST=foundation_jepa/sequence/artifacts/next_stage/manifest.jsonl \
  foundation_jepa/sequence/slurm/sequence_jepa_suite_gpu.slurm
```

Summarize finished runs:

```bash
/home/mazijian/miniforge3/envs/aireadi/bin/python -m foundation_jepa.sequence.experiment_suite summarize \
  foundation_jepa/sequence/artifacts/next_stage \
  --manifest foundation_jepa/sequence/artifacts/next_stage/manifest.jsonl \
  --output-csv foundation_jepa/sequence/artifacts/next_stage/summary.csv
```

## Interpretation Guardrails

This is a representation-learning scaffold, not publication evidence. Before
using results scientifically, compare against:

- participant-level JEPA
- age-only objective
- shuffled-modality negative controls
- drop-clinical and drop-imaging ablations
- classical coupling features and hypothesis-driven analyses

The main scientific question is whether raw synchronized 10-day temporal
alignment adds information beyond participant-level summaries and pretrained
retinal/ECG embeddings.

## Data Semantics

`CACHE_VERSION` is `sequence_jepa_v2`. This version encodes
`active_calories` from `scripts.features_wearable.compute_calorie_timeseries()`
as per-record kcal deltas aggregated onto the 5-minute grid. Older v1 caches
used nearest raw cumulative calorie counter values and must not be reused for
training or comparison.
