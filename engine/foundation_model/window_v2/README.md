# Window V2 Target-Token JEPA

This subtree is the literature-aligned replacement path for the current
window-level JEPA objective. It keeps the same split-preserving window sampler
and controls as `foundation_jepa/window/`, but changes the model and loss.

## What Changed

- The student context encoder sees only observed temporal context patches.
- The EMA teacher encodes the held-out target window as patch tokens.
- The predictor receives context tokens plus target modality/time queries.
- The loss compares predicted target-token embeddings to stopped EMA teacher
  target-token embeddings.
- Age, severity, static alignment, and contrastive InfoNCE are not part of the
  default pretraining objective.
- Target coverage is rechecked after controls are applied, so wrong-day shifts
  do not silently introduce below-threshold target windows.

This is closer to the I-JEPA/V-JEPA pattern than the v1 window model, which
predicts one pooled target-window latent and uses InfoNCE as a collapse guard.

## Objective

```text
student_context_tokens = f_student(context_window)
teacher_target_tokens  = stopgrad(f_ema(target_window))

predicted_target_tokens = predictor(
  student_context_tokens,
  target_modality_query,
  target_patch_position_query
)

loss = smooth_l1(
  normalize(predicted_target_tokens),
  normalize(teacher_target_tokens)
)
```

An optional variance floor is available with `--variance-weight`, but the
default is pure latent target-token prediction.

## Smoke Test

```bash
env OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
/home/mazijian/miniforge3/envs/aireadi/bin/python -m foundation_jepa.window_v2.train \
  --limit 16 \
  --epochs 1 \
  --batch-size 16 \
  --context-len 24 \
  --target-len 12 \
  --horizon 6 \
  --window-stride 48 \
  --max-windows-per-person 8 \
  --target-modalities cgm wearable \
  --patch-len 6 \
  --patch-stride 3 \
  --latent-dim 32 \
  --model-dim 64 \
  --layers 1 \
  --predictor-layers 1 \
  --heads 4 \
  --device cpu \
  --output-dir foundation_jepa/window_v2/artifacts/smoke
```

## Event Run With Probes

```bash
env OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
/home/mazijian/miniforge3/envs/aireadi/bin/python -m foundation_jepa.window_v2.train \
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
  --layers 1 \
  --predictor-layers 1 \
  --heads 4 \
  --device cpu \
  --physiology-probes \
  --output-dir foundation_jepa/window_v2/artifacts/smoke_mixed_events
```

## Horizon/Control Manifest

```bash
/home/mazijian/miniforge3/envs/aireadi/bin/python -m foundation_jepa.window_v2.experiment_suite make-manifest \
  --output-root foundation_jepa/window_v2/artifacts/horizon_suite \
  --manifest foundation_jepa/window_v2/artifacts/horizon_suite/manifest.jsonl \
  --epochs 10 \
  --max-windows-per-person 64 \
  --horizons 0,6,12,24 \
  --seeds 42,43,44
```

Run one manifest row:

```bash
/home/mazijian/miniforge3/envs/aireadi/bin/python -m foundation_jepa.window_v2.experiment_suite run-one \
  --manifest foundation_jepa/window_v2/artifacts/horizon_suite/manifest.jsonl \
  --index 0
```

Submit the full 36-row GPU array with at most six concurrent tasks:

```bash
sbatch --array=0-35%6 --export=ALL,MANIFEST=foundation_jepa/window_v2/artifacts/horizon_suite/manifest.jsonl \
  foundation_jepa/window_v2/slurm/window_v2_jepa_suite_gpu.slurm
```

Summarize finished runs:

```bash
/home/mazijian/miniforge3/envs/aireadi/bin/python -m foundation_jepa.window_v2.experiment_suite summarize \
  foundation_jepa/window_v2/artifacts/horizon_suite \
  --manifest foundation_jepa/window_v2/artifacts/horizon_suite/manifest.jsonl \
  --output-csv foundation_jepa/window_v2/artifacts/horizon_suite/summary.csv
```

## Interpretation

The first paper-grade check remains the same as v1:

```text
aligned test JEPA loss < wrong-day test JEPA loss < participant-shuffle test JEPA loss
```

The next checks should be frozen probes, random/untrained encoder baselines,
classical context-summary baselines, participant bootstrap confidence intervals,
and disease-stratified aligned-minus-control gaps.
