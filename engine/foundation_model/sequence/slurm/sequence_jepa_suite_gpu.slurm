#!/bin/bash
#SBATCH --job-name=seq_jepa_suite
#SBATCH --account=twc
#SBATCH --partition=gpu_long
#SBATCH --gres=gpu:h200:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=96G
#SBATCH --time=3:00:00
#SBATCH --array=0-0
#SBATCH --output=foundation_jepa/sequence/logs/sequence_jepa_suite_%A_%a.log
#SBATCH --error=foundation_jepa/sequence/logs/sequence_jepa_suite_%A_%a.err

set -euo pipefail

export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"
export MKL_NUM_THREADS="${MKL_NUM_THREADS:-1}"
export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-1}"
export NUMEXPR_NUM_THREADS="${NUMEXPR_NUM_THREADS:-1}"

eval "$(conda shell.bash hook 2>/dev/null)"
conda activate aireadi

PROJECT_DIR="/oak/stanford/scg/lab_twc/mazijian/aireadi"
cd "${PROJECT_DIR}"

mkdir -p foundation_jepa/sequence/logs foundation_jepa/sequence/artifacts/next_stage

MANIFEST="${MANIFEST:-foundation_jepa/sequence/artifacts/next_stage/manifest.jsonl}"
TASK_INDEX="${SLURM_ARRAY_TASK_ID:-0}"

echo "=========================================="
echo "Sequence JEPA next-stage suite - $(date)"
echo "Job: ${SLURM_JOB_ID:-local} task=${TASK_INDEX}"
echo "Manifest: ${MANIFEST}"
echo "Host: $(hostname)"
echo "GPU: $(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null || echo N/A)"
echo "Python: $(python --version)"
python -c 'import torch; print("PyTorch:", torch.__version__, "CUDA:", torch.cuda.is_available())'
echo "=========================================="

LIMIT_ARGS=()
if [[ -n "${LIMIT:-}" ]]; then
  LIMIT_ARGS=(--limit "${LIMIT}")
fi

SAVE_ARGS=()
if [[ "${SAVE_CHECKPOINT:-0}" == "1" ]]; then
  SAVE_ARGS+=(--save-checkpoint)
fi
if [[ "${SAVE_EMBEDDINGS:-0}" == "1" ]]; then
  SAVE_ARGS+=(--save-embeddings)
fi

if [[ ! -s "${MANIFEST}" ]]; then
  if [[ "${TASK_INDEX}" == "0" ]]; then
    python -m foundation_jepa.sequence.experiment_suite make-manifest \
      --manifest "${MANIFEST}" \
      --suite "${SUITE:-next_stage}" \
      --seeds "${SEEDS:-42,43,44}" \
      --output-root "${OUTPUT_ROOT:-foundation_jepa/sequence/artifacts/next_stage}" \
      --cache-dir "${CACHE_DIR:-foundation_jepa/sequence/artifacts/cache_5min_10d}" \
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
      --severity-loss-weight "${SEVERITY_LOSS_WEIGHT:-0.2}" \
      --probe-ridge-alpha "${PROBE_RIDGE_ALPHA:-1.0}" \
      --device cuda \
      "${SAVE_ARGS[@]}"
  else
    for _ in {1..120}; do
      [[ -s "${MANIFEST}" ]] && break
      sleep 2
    done
  fi
fi

if [[ ! -s "${MANIFEST}" ]]; then
  echo "Manifest was not created: ${MANIFEST}" >&2
  exit 1
fi

python -u -m foundation_jepa.sequence.experiment_suite run-one \
  --manifest "${MANIFEST}" \
  --index "${TASK_INDEX}"

echo "Done - $(date)"
