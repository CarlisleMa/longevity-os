#!/bin/bash
#SBATCH --job-name=seq_jepa
#SBATCH --account=twc
#SBATCH --partition=gpu_long
#SBATCH --gres=gpu:h200:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=96G
#SBATCH --time=4:00:00
#SBATCH --output=foundation_jepa/sequence/logs/sequence_jepa_pilot_%j.log
#SBATCH --error=foundation_jepa/sequence/logs/sequence_jepa_pilot_%j.err

set -euo pipefail

export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"
export MKL_NUM_THREADS="${MKL_NUM_THREADS:-1}"
export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-1}"
export NUMEXPR_NUM_THREADS="${NUMEXPR_NUM_THREADS:-1}"

eval "$(conda shell.bash hook 2>/dev/null)"
conda activate aireadi

PROJECT_DIR="/oak/stanford/scg/lab_twc/mazijian/aireadi"
cd "${PROJECT_DIR}"

mkdir -p foundation_jepa/sequence/logs foundation_jepa/sequence/artifacts/pilot_gpu

echo "=========================================="
echo "Raw 10-day sequence JEPA GPU pilot - $(date)"
echo "Host: $(hostname)"
echo "GPU: $(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null || echo N/A)"
echo "Python: $(python --version)"
python -c 'import torch; print("PyTorch:", torch.__version__, "CUDA:", torch.cuda.is_available())'
echo "=========================================="

LIMIT_ARGS=()
if [[ -n "${LIMIT:-}" ]]; then
  LIMIT_ARGS=(--limit "${LIMIT}")
fi

python -u -m foundation_jepa.sequence.train \
  --output-dir foundation_jepa/sequence/artifacts/pilot_gpu/full_sequence_jepa \
  --cache-dir foundation_jepa/sequence/artifacts/cache_5min_10d \
  "${LIMIT_ARGS[@]}" \
  --epochs "${EPOCHS:-20}" \
  --batch-size "${BATCH_SIZE:-32}" \
  --latent-dim "${LATENT_DIM:-128}" \
  --model-dim "${MODEL_DIM:-128}" \
  --hidden-dim "${HIDDEN_DIM:-256}" \
  --layers "${LAYERS:-2}" \
  --heads "${HEADS:-4}" \
  --patch-len "${PATCH_LEN:-24}" \
  --stride "${STRIDE:-12}" \
  --jepa-loss-weight 1.0 \
  --age-loss-weight 1.0 \
  --severity-loss-weight "${SEVERITY_LOSS_WEIGHT:-0.2}" \
  --device cuda

python -u -m foundation_jepa.sequence.train \
  --output-dir foundation_jepa/sequence/artifacts/pilot_gpu/shuffle_sequence_all \
  --cache-dir foundation_jepa/sequence/artifacts/cache_5min_10d \
  "${LIMIT_ARGS[@]}" \
  --epochs "${EPOCHS:-20}" \
  --batch-size "${BATCH_SIZE:-32}" \
  --latent-dim "${LATENT_DIM:-128}" \
  --model-dim "${MODEL_DIM:-128}" \
  --hidden-dim "${HIDDEN_DIM:-256}" \
  --layers "${LAYERS:-2}" \
  --heads "${HEADS:-4}" \
  --patch-len "${PATCH_LEN:-24}" \
  --stride "${STRIDE:-12}" \
  --jepa-loss-weight 1.0 \
  --age-loss-weight 1.0 \
  --severity-loss-weight "${SEVERITY_LOSS_WEIGHT:-0.2}" \
  --shuffle-modalities all \
  --device cuda

echo "Done - $(date)"
