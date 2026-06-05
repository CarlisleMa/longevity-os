# Foundation JEPA Experiments

This directory is the single namespace for experimental multimodal
representation learning in AI-READI. The three experiment generations are kept
together because they answer different questions and reuse artifacts.

## Layout

| Path | Role | Scientific question |
|---|---|---|
| `foundation_jepa/` | Participant-level JEPA over summary tables and pretrained retinal/ECG embeddings | Do modality-summary embeddings reconstruct each other or predict age/severity beyond classical features? |
| `foundation_jepa/sequence/` | 10-day, 5-minute sequence JEPA | Do synchronized full-window temporal streams add information beyond static modalities? |
| `foundation_jepa/window/` | Window-level temporal JEPA v1 | Do local temporal contexts predict future/held-out physiology better under true alignment than under wrong-day or participant-shuffle controls? |
| `foundation_jepa/window_v2/` | Target-token temporal JEPA | Does a student context encoder predict EMA-teacher target patch embeddings under true temporal alignment? |

Only source code, Slurm launchers, and placeholder `.gitkeep` files are tracked.
Caches, logs, checkpoints, probes, and generated summaries stay local under each
experiment's `artifacts/` or `logs/` directory.

## Participant-Level Prototype

The root package uses existing participant-level artifacts:

- `results/features/feature_matrix.parquet`
- `results/features/multimodal_features.parquet`
- `results/embeddings/retinal_embeddings.parquet`
- `results/embeddings/cardiac_embeddings.parquet`

It is a sandbox for testing whether learned cross-modal reconstruction loss can
become a useful coupling score after classical temporal hypotheses establish
the signal.

Smoke test:

```bash
/home/mazijian/miniforge3/envs/aireadi/bin/python -m foundation_jepa.train \
  --limit 128 \
  --epochs 1 \
  --batch-size 32 \
  --latent-dim 32 \
  --hidden-dim 64 \
  --device cpu \
  --output-dir foundation_jepa/artifacts/smoke
```

GPU pilot:

```bash
sbatch foundation_jepa/slurm/jepa_pilot_gpu.slurm
```

## Sequence-Level JEPA

Use the sequence package for participant-level representations from 10-day
aligned CGM, wearable, environment, clinical, retinal, and ECG modalities.

```bash
/home/mazijian/miniforge3/envs/aireadi/bin/python -m foundation_jepa.sequence.train \
  --limit 32 \
  --epochs 1 \
  --device cpu \
  --output-dir foundation_jepa/sequence/artifacts/smoke
```

The sequence cache version is `sequence_jepa_v2`; older caches used raw
cumulative calorie counter values and should not be reused.

## Window-Level JEPA

Use the window package for local temporal prediction with aligned, wrong-day,
and participant-shuffle controls.

```bash
/home/mazijian/miniforge3/envs/aireadi/bin/python -m foundation_jepa.window.train \
  --limit 16 \
  --epochs 1 \
  --event-mode mixed_events \
  --device cpu \
  --output-dir foundation_jepa/window/artifacts/smoke_mixed_events
```

## Window V2 Target-Token JEPA

Use `window_v2` for the more proper JEPA implementation: temporal patch tokens,
student context encoder, EMA teacher target encoder, target modality/time
queries, and no supervised age/severity/static objective during pretraining.

```bash
/home/mazijian/miniforge3/envs/aireadi/bin/python -m foundation_jepa.window_v2.train \
  --limit 16 \
  --epochs 1 \
  --target-modalities cgm wearable \
  --device cpu \
  --output-dir foundation_jepa/window_v2/artifacts/smoke
```

## Interpretation Guardrails

- Treat all JEPA stacks as experimental scaffolds, not publication evidence.
- Compare aligned runs against shuffled and wrong-day controls before making
  scientific claims.
- Keep train/validation/test boundaries intact for probes and downstream
  evaluation.
- Compare learned representations with classical coupling features and
  hypothesis-driven analyses.
