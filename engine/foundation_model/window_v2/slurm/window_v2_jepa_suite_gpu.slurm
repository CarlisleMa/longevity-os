#!/bin/bash
#SBATCH --job-name=win_v2_jepa
#SBATCH --account=twc
#SBATCH --partition=gpu_long
#SBATCH --gres=gpu:h200:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=96G
#SBATCH --time=4:00:00
#SBATCH --array=0-0
#SBATCH --output=foundation_jepa/window_v2/logs/window_v2_jepa_suite_%A_%a.log
#SBATCH --error=foundation_jepa/window_v2/logs/window_v2_jepa_suite_%A_%a.err

set -euo pipefail

export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"
export MKL_NUM_THREADS="${MKL_NUM_THREADS:-1}"
export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-1}"
export NUMEXPR_NUM_THREADS="${NUMEXPR_NUM_THREADS:-1}"

eval "$(conda shell.bash hook 2>/dev/null)"
conda activate aireadi

PROJECT_DIR="/oak/stanford/scg/lab_twc/mazijian/aireadi"
cd "${PROJECT_DIR}"

mkdir -p foundation_jepa/window_v2/logs foundation_jepa/window_v2/artifacts/horizon_suite

MANIFEST="${MANIFEST:-foundation_jepa/window_v2/artifacts/horizon_suite/manifest.jsonl}"
TASK_INDEX="${SLURM_ARRAY_TASK_ID:-0}"

echo "=========================================="
echo "Window V2 target-token JEPA suite - $(date)"
echo "Job: ${SLURM_JOB_ID:-local} task=${TASK_INDEX}"
echo "Manifest: ${MANIFEST}"
echo "Host: $(hostname)"
echo "GPU: $(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null || echo N/A)"
echo "Python: $(python --version)"
python -c 'import torch; print("PyTorch:", torch.__version__, "CUDA:", torch.cuda.is_available())'
echo "=========================================="

python -u -m foundation_jepa.window_v2.experiment_suite run-one \
  --manifest "${MANIFEST}" \
  --index "${TASK_INDEX}"

echo "Done - $(date)"

