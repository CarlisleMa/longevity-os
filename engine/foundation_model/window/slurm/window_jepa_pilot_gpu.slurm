#!/bin/bash
#SBATCH --job-name=win_jepa
#SBATCH --account=twc
#SBATCH --partition=gpu_long
#SBATCH --gres=gpu:h200:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=96G
#SBATCH --time=4:00:00
#SBATCH --output=foundation_jepa/window/logs/window_jepa_pilot_%j.log
#SBATCH --error=foundation_jepa/window/logs/window_jepa_pilot_%j.err

set -euo pipefail

export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"
export MKL_NUM_THREADS="${MKL_NUM_THREADS:-1}"
export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-1}"
export NUMEXPR_NUM_THREADS="${NUMEXPR_NUM_THREADS:-1}"

eval "$(conda shell.bash hook 2>/dev/null)"
conda activate aireadi

PROJECT_DIR="/oak/stanford/scg/lab_twc/mazijian/aireadi"
cd "${PROJECT_DIR}"

mkdir -p foundation_jepa/window/logs foundation_jepa/window/artifacts/pilot_gpu

echo "=========================================="
echo "Window-level temporal JEPA pilot - $(date)"
echo "Host: $(hostname)"
echo "GPU: $(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null || echo N/A)"
echo "Python: $(python --version)"
python -c 'import torch; print("PyTorch:", torch.__version__, "CUDA:", torch.cuda.is_available())'
echo "=========================================="

LIMIT_ARGS=()
if [[ -n "${LIMIT:-}" ]]; then
  LIMIT_ARGS=(--limit "${LIMIT}")
fi

COMMON_ARGS=(
  --cache-dir foundation_jepa/sequence/artifacts/cache_5min_10d
  "${LIMIT_ARGS[@]}"
  --epochs "${EPOCHS:-20}"
  --batch-size "${BATCH_SIZE:-256}"
  --context-len "${CONTEXT_LEN:-24}"
  --target-len "${TARGET_LEN:-12}"
  --horizon "${HORIZON:-0}"
  --window-stride "${WINDOW_STRIDE:-12}"
  --max-windows-per-person "${MAX_WINDOWS_PER_PERSON:-96}"
  --latent-dim "${LATENT_DIM:-128}"
  --model-dim "${MODEL_DIM:-128}"
  --hidden-dim "${HIDDEN_DIM:-256}"
  --layers "${LAYERS:-2}"
  --heads "${HEADS:-4}"
  --patch-len "${PATCH_LEN:-12}"
  --patch-stride "${PATCH_STRIDE:-6}"
  --jepa-loss-weight 1.0
  --static-align-weight "${STATIC_ALIGN_WEIGHT:-0.0}"
  --contrastive-weight "${CONTRASTIVE_WEIGHT:-1.0}"
  --temperature "${TEMPERATURE:-0.1}"
  --teacher-tau "${TEACHER_TAU:-0.99}"
  --device cuda
)

python -u -m foundation_jepa.window.train \
  --output-dir foundation_jepa/window/artifacts/pilot_gpu/aligned \
  --control aligned \
  "${COMMON_ARGS[@]}"

python -u -m foundation_jepa.window.train \
  --output-dir foundation_jepa/window/artifacts/pilot_gpu/participant_shuffle \
  --control participant_shuffle \
  "${COMMON_ARGS[@]}"

python -u -m foundation_jepa.window.train \
  --output-dir foundation_jepa/window/artifacts/pilot_gpu/wrong_day \
  --control wrong_day \
  "${COMMON_ARGS[@]}"

echo "Done - $(date)"
