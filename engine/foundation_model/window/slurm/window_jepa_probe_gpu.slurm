#!/bin/bash
#SBATCH --job-name=win_jepa_probe
#SBATCH --account=twc
#SBATCH --partition=gpu_long
#SBATCH --gres=gpu:h200:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=128G
#SBATCH --time=4:00:00
#SBATCH --output=foundation_jepa/window/logs/window_jepa_probe_%j.log
#SBATCH --error=foundation_jepa/window/logs/window_jepa_probe_%j.err

set -euo pipefail

export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"
export MKL_NUM_THREADS="${MKL_NUM_THREADS:-1}"
export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-1}"
export NUMEXPR_NUM_THREADS="${NUMEXPR_NUM_THREADS:-1}"

eval "$(conda shell.bash hook 2>/dev/null)"
conda activate aireadi

PROJECT_DIR="/oak/stanford/scg/lab_twc/mazijian/aireadi"
cd "${PROJECT_DIR}"

mkdir -p foundation_jepa/window/logs foundation_jepa/window/artifacts/probe_runs

HORIZON="${HORIZON:-6}"
SEED="${SEED:-42}"
EVENT_MODE="${EVENT_MODE:-random}"
OUTPUT_DIR="${OUTPUT_DIR:-foundation_jepa/window/artifacts/probe_runs/horizon_030min_seed_42_aligned}"

LIMIT_ARGS=()
if [[ -n "${LIMIT:-}" ]]; then
  LIMIT_ARGS=(--limit "${LIMIT}")
fi

SAVE_ARGS=()
if [[ "${SAVE_EMBEDDINGS:-0}" == "1" ]]; then
  SAVE_ARGS+=(--save-embeddings)
fi

echo "=========================================="
echo "Window JEPA physiology-probe run - $(date)"
echo "Horizon: ${HORIZON} steps"
echo "Seed: ${SEED}"
echo "Event mode: ${EVENT_MODE}"
echo "Output: ${OUTPUT_DIR}"
echo "Host: $(hostname)"
echo "GPU: $(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null || echo N/A)"
python -c 'import torch; print("PyTorch:", torch.__version__, "CUDA:", torch.cuda.is_available())'
echo "=========================================="

python -u -m foundation_jepa.window.train \
  --output-dir "${OUTPUT_DIR}" \
  --cache-dir foundation_jepa/sequence/artifacts/cache_5min_10d \
  "${LIMIT_ARGS[@]}" \
  --seed "${SEED}" \
  --epochs "${EPOCHS:-10}" \
  --batch-size "${BATCH_SIZE:-256}" \
  --context-len "${CONTEXT_LEN:-24}" \
  --target-len "${TARGET_LEN:-12}" \
  --horizon "${HORIZON}" \
  --window-stride "${WINDOW_STRIDE:-12}" \
  --max-windows-per-person "${MAX_WINDOWS_PER_PERSON:-64}" \
  --control aligned \
  --event-mode "${EVENT_MODE}" \
  --cgm-rise-threshold "${CGM_RISE_THRESHOLD:-0.5}" \
  --activity-threshold "${ACTIVITY_THRESHOLD:-0.75}" \
  --sleep-change-threshold "${SLEEP_CHANGE_THRESHOLD:-0.5}" \
  --latent-dim "${LATENT_DIM:-128}" \
  --model-dim "${MODEL_DIM:-128}" \
  --hidden-dim "${HIDDEN_DIM:-256}" \
  --layers "${LAYERS:-2}" \
  --heads "${HEADS:-4}" \
  --patch-len "${PATCH_LEN:-12}" \
  --patch-stride "${PATCH_STRIDE:-6}" \
  --static-align-weight "${STATIC_ALIGN_WEIGHT:-0.0}" \
  --contrastive-weight "${CONTRASTIVE_WEIGHT:-1.0}" \
  --temperature "${TEMPERATURE:-0.1}" \
  --teacher-tau "${TEACHER_TAU:-0.99}" \
  --physiology-probes \
  --probe-ridge-alpha "${PROBE_RIDGE_ALPHA:-1.0}" \
  --save-checkpoint \
  "${SAVE_ARGS[@]}" \
  --device cuda

echo "Done - $(date)"
