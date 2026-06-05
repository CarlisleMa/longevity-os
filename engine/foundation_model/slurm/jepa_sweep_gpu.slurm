#!/bin/bash
#SBATCH --job-name=jepa_sweep
#SBATCH --account=twc
#SBATCH --partition=gpu_long
#SBATCH --gres=gpu:h200:1
#SBATCH --array=0-35
#SBATCH --cpus-per-task=4
#SBATCH --mem=48G
#SBATCH --time=4:00:00
#SBATCH --output=foundation_jepa/logs/jepa_sweep_%A_%a.log
#SBATCH --error=foundation_jepa/logs/jepa_sweep_%A_%a.err

set -euo pipefail

eval "$(conda shell.bash hook 2>/dev/null)"
conda activate aireadi

PROJECT_DIR="/oak/stanford/scg/lab_twc/mazijian/aireadi"
cd "${PROJECT_DIR}"

mkdir -p foundation_jepa/logs foundation_jepa/artifacts/sweeps

EPOCHS="${EPOCHS:-50}"
BATCH_SIZE="${BATCH_SIZE:-256}"
LATENT_DIM="${LATENT_DIM:-128}"
HIDDEN_DIM="${HIDDEN_DIM:-256}"
JEPA_SEEDS="${JEPA_SEEDS:-42,43,44}"
OUTPUT_ROOT="${OUTPUT_ROOT:-foundation_jepa/artifacts/sweeps/${SLURM_JOB_ID}}"

echo "=========================================="
echo "Foundation JEPA sweep - $(date)"
echo "Host: $(hostname)"
echo "Array task: ${SLURM_ARRAY_TASK_ID}/${SLURM_ARRAY_TASK_COUNT}"
echo "Output root: ${OUTPUT_ROOT}"
echo "GPU: $(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null || echo N/A)"
echo "Python: $(python --version)"
python -c 'import torch; print("PyTorch:", torch.__version__, "CUDA:", torch.cuda.is_available())'
echo "=========================================="

python -u -m foundation_jepa.run_sweep \
  --output-root "${OUTPUT_ROOT}" \
  --seeds "${JEPA_SEEDS}" \
  --array-index "${SLURM_ARRAY_TASK_ID}" \
  --epochs "${EPOCHS}" \
  --batch-size "${BATCH_SIZE}" \
  --latent-dim "${LATENT_DIM}" \
  --hidden-dim "${HIDDEN_DIM}" \
  --device cuda

echo "Done - $(date)"
