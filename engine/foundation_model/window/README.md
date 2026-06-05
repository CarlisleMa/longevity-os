# Window-Level Temporal JEPA

This subtree is the next-stage JEPA implementation after the participant-level
ablation showed that age/severity endpoints are dominated by static
clinical/retinal/ECG information.

The goal here is to learn synchronized temporal physiology from 5-minute CGM,
wearable, and environment windows.

The sequence cache must be regenerated with `foundation_jepa/sequence`
`CACHE_VERSION=sequence_jepa_v2` or newer. Earlier caches encoded the Garmin
calorie channel as raw cumulative values instead of reset-aware kcal deltas.

## What This Implements

- Reuses the existing 10-day sequence cache from
  `foundation_jepa/sequence/artifacts/cache_5min_10d`.
- Samples split-preserving context and future target windows.
- Uses only temporal modalities in the JEPA context:
  - CGM
  - wearable HR/activity/sleep/calories
  - environment PM/light/temperature/humidity
- Uses a shared temporal Transformer backbone over modality patch tokens.
- Uses an EMA target encoder for stop-gradient target latents.
- Predicts target-window latents by target modality.
- Supports negative controls:
  - `aligned`
  - `participant_shuffle`
  - `wrong_day`
- Supports optional static-to-dynamic alignment:
  - clinical / RETFound / ECGFounder projections predict detached dynamic
    context latents
  - static modalities are not used as temporal context by default

## Objective

For each sampled window:

```text
context = temporal modalities over an observed window
target = held-out target modality over a future/offset window

loss = JEPA(predicted_target_latent, EMA_target_latent)
     + static_align_weight * static_to_dynamic_alignment
```

`JEPA` currently combines latent MSE with an in-batch target-discrimination
term:

```text
JEPA = normalized_latent_MSE + contrastive_weight * InfoNCE
```

The contrastive term is a collapse guard. The first bounded pilot with only
normalized latent MSE let participant-shuffled targets score too well, so the
default now requires the context representation to identify the matching target
latent within the batch.

The default is pure temporal JEPA:

```text
static_align_weight = 0.0
contrastive_weight = 1.0
```

Static alignment can be enabled after the temporal objective is validated:

```text
static_align_weight = 0.1
```

## Smoke Test

```bash
env OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
/home/mazijian/miniforge3/envs/aireadi/bin/python -m foundation_jepa.window.train \
  --limit 16 \
  --epochs 1 \
  --batch-size 16 \
  --context-len 24 \
  --target-len 12 \
  --window-stride 48 \
  --max-windows-per-person 8 \
  --latent-dim 32 \
  --model-dim 64 \
  --hidden-dim 64 \
  --layers 1 \
  --device cpu \
  --output-dir foundation_jepa/window/artifacts/smoke
```

## GPU Pilot

```bash
sbatch foundation_jepa/window/slurm/window_jepa_pilot_gpu.slurm
```

For a bounded run:

```bash
sbatch --export=ALL,LIMIT=256,EPOCHS=5,MAX_WINDOWS_PER_PERSON=32 \
  foundation_jepa/window/slurm/window_jepa_pilot_gpu.slurm
```

The pilot runs `aligned`, `participant_shuffle`, and `wrong_day` controls.

## Horizon Suite

The first larger suite runs all participants across horizons and controls:

- horizons: `0`, `30`, `60`, `120` minutes
- controls: `aligned`, `wrong_day`, `participant_shuffle`
- seeds: `42`, `43`, `44`

Create the manifest:

```bash
/home/mazijian/miniforge3/envs/aireadi/bin/python -m foundation_jepa.window.experiment_suite make-manifest \
  --output-root foundation_jepa/window/artifacts/horizon_suite \
  --manifest foundation_jepa/window/artifacts/horizon_suite/manifest.jsonl \
  --epochs 10 \
  --max-windows-per-person 64 \
  --horizons 0,6,12,24 \
  --seeds 42,43,44
```

Submit the 36-row GPU array:

```bash
sbatch --array=0-35 --export=ALL,MANIFEST=foundation_jepa/window/artifacts/horizon_suite/manifest.jsonl \
  foundation_jepa/window/slurm/window_jepa_suite_gpu.slurm
```

Summarize finished runs:

```bash
/home/mazijian/miniforge3/envs/aireadi/bin/python -m foundation_jepa.window.experiment_suite summarize \
  foundation_jepa/window/artifacts/horizon_suite \
  --manifest foundation_jepa/window/artifacts/horizon_suite/manifest.jsonl \
  --output-csv foundation_jepa/window/artifacts/horizon_suite/summary.csv
```

## Interpretation

The first question is not whether this predicts chronological age. The first
question is whether aligned temporal windows have lower JEPA loss than
participant-shuffled and wrong-day controls on held-out participants. If that
works, the next layer should add event-specific samplers for:

- glucose excursions
- activity-to-glucose recovery
- sleep and overnight glucose stability
- dawn-window physiology
- HR-glucose coupling lag structure

## Event-Enriched Sampling

Random windows are useful for validating temporal alignment, but they dilute
acute physiology. The trainer now supports event-enriched sampling:

- `random`: baseline window sampler
- `glucose_rise`: windows where future CGM rises relative to context
- `activity_bout`: windows with elevated context steps/calories
- `sleep_transition`: windows around sleep/wake state changes
- `dawn_proxy`: daily-position proxy for early-morning windows
- `mixed_events`: pooled glucose/activity/sleep/dawn-proxy events

`dawn_proxy` is not a true local-clock dawn window yet because the current
sequence cache does not persist absolute start timestamps. It should be treated
as a daily-position control until the cache is extended with clock time.

Example bounded event run:

```bash
env OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
/home/mazijian/miniforge3/envs/aireadi/bin/python -m foundation_jepa.window.train \
  --limit 32 \
  --epochs 1 \
  --event-mode mixed_events \
  --target-modalities cgm wearable \
  --batch-size 32 \
  --context-len 24 \
  --target-len 12 \
  --horizon 6 \
  --window-stride 12 \
  --max-windows-per-person 16 \
  --latent-dim 32 \
  --model-dim 64 \
  --hidden-dim 64 \
  --layers 1 \
  --device cpu \
  --physiology-probes \
  --output-dir foundation_jepa/window/artifacts/smoke_mixed_events
```

Manifest example for a GPU event suite:

```bash
/home/mazijian/miniforge3/envs/aireadi/bin/python -m foundation_jepa.window.experiment_suite make-manifest \
  --output-root foundation_jepa/window/artifacts/event_suite \
  --manifest foundation_jepa/window/artifacts/event_suite/manifest.jsonl \
  --event-modes glucose_rise,activity_bout,sleep_transition,mixed_events \
  --target-modalities cgm wearable \
  --horizons 6,12,24 \
  --controls aligned,wrong_day,participant_shuffle \
  --seeds 42,43,44 \
  --epochs 10 \
  --max-windows-per-person 64
```

The physiology probe output now includes:

- `physiology_probe_metrics.csv`: overall held-out probe metrics
- `physiology_probe_stratified_metrics.csv`: metrics stratified by severity,
  event type, and target modality
