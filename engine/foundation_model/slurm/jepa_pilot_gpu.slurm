#!/bin/bash
#SBATCH --job-name=jepa_pilot
#SBATCH --account=twc
#SBATCH --partition=gpu_long
#SBATCH --gres=gpu:h200:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=48G
#SBATCH --time=1:00:00
#SBATCH --output=foundation_jepa/logs/jepa_pilot_%j.log
#SBATCH --error=foundation_jepa/logs/jepa_pilot_%j.err

set -euo pipefail

eval "$(conda shell.bash hook 2>/dev/null)"
conda activate aireadi

PROJECT_DIR="/oak/stanford/scg/lab_twc/mazijian/aireadi"
cd "${PROJECT_DIR}"

mkdir -p foundation_jepa/logs foundation_jepa/artifacts/pilot_gpu

echo "=========================================="
echo "Foundation JEPA GPU pilot - $(date)"
echo "Host: $(hostname)"
echo "GPU: $(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null || echo N/A)"
echo "Python: $(python --version)"
python -c 'import torch; print("PyTorch:", torch.__version__, "CUDA:", torch.cuda.is_available())'
echo "=========================================="

python -u -m foundation_jepa.train \
  --output-dir foundation_jepa/artifacts/pilot_gpu/full_jepa_age \
  --epochs "${EPOCHS:-25}" \
  --batch-size "${BATCH_SIZE:-256}" \
  --latent-dim "${LATENT_DIM:-128}" \
  --hidden-dim "${HIDDEN_DIM:-256}" \
  --jepa-loss-weight 1.0 \
  --age-loss-weight 1.0 \
  --severity-loss-weight "${SEVERITY_LOSS_WEIGHT:-0.2}" \
  --device cuda

python -u -m foundation_jepa.train \
  --output-dir foundation_jepa/artifacts/pilot_gpu/shuffle_all \
  --epochs "${EPOCHS:-25}" \
  --batch-size "${BATCH_SIZE:-256}" \
  --latent-dim "${LATENT_DIM:-128}" \
  --hidden-dim "${HIDDEN_DIM:-256}" \
  --jepa-loss-weight 1.0 \
  --age-loss-weight 1.0 \
  --severity-loss-weight "${SEVERITY_LOSS_WEIGHT:-0.2}" \
  --shuffle-modalities all \
  --device cuda

python -u -m foundation_jepa.summarize_sweep foundation_jepa/artifacts/pilot_gpu

echo "Done - $(date)"
