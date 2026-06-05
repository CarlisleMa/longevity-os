#!/bin/bash
#SBATCH --job-name=seq_cache_warm
#SBATCH --account=twc
#SBATCH --partition=batch
#SBATCH --cpus-per-task=8
#SBATCH --mem=96G
#SBATCH --time=6:00:00
#SBATCH --array=0-0
#SBATCH --output=foundation_jepa/sequence/logs/sequence_cache_warm_%A_%a.log
#SBATCH --error=foundation_jepa/sequence/logs/sequence_cache_warm_%A_%a.err

set -euo pipefail

export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"
export MKL_NUM_THREADS="${MKL_NUM_THREADS:-1}"
export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-1}"
export NUMEXPR_NUM_THREADS="${NUMEXPR_NUM_THREADS:-1}"

eval "$(conda shell.bash hook 2>/dev/null)"
conda activate aireadi

PROJECT_DIR="/oak/stanford/scg/lab_twc/mazijian/aireadi"
cd "${PROJECT_DIR}"

mkdir -p foundation_jepa/sequence/logs foundation_jepa/sequence/artifacts/cache_5min_10d

echo "=========================================="
echo "Sequence cache warm - $(date)"
echo "Job: ${SLURM_JOB_ID:-local} task=${SLURM_ARRAY_TASK_ID:-0}"
echo "Host: $(hostname)"
echo "Python: $(python --version)"
echo "=========================================="

NUM_SHARDS="${NUM_SHARDS:-1}"
SHARD_INDEX="${SLURM_ARRAY_TASK_ID:-0}"
OUTPUT_JSON_DEFAULT="foundation_jepa/sequence/artifacts/cache_5min_10d/warm_cache_summary_${SLURM_ARRAY_JOB_ID:-${SLURM_JOB_ID:-local}}_${SHARD_INDEX}.json"

python -u -m foundation_jepa.sequence.warm_cache \
  --cache-dir "${CACHE_DIR:-foundation_jepa/sequence/artifacts/cache_5min_10d}" \
  --num-shards "${NUM_SHARDS}" \
  --shard-index "${SHARD_INDEX}" \
  --skip-version-counts \
  --output-json "${OUTPUT_JSON:-${OUTPUT_JSON_DEFAULT}}"

echo "Done - $(date)"
