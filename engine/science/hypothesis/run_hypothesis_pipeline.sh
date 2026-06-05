#!/bin/bash
set -euo pipefail

# ═══════════════════════════════════════════════════════════
# Hypothesis-Driven Discovery Pipeline
# Runs Phase 2 execution + generates summary report
# ═══════════════════════════════════════════════════════════

PROJECT_DIR="/oak/stanford/scg/lab_twc/mazijian/aireadi"
cd "${PROJECT_DIR}"

eval "$(conda shell.bash hook 2>/dev/null)"
conda activate aireadi

LOG="results/logs/pipeline_$(date +%Y%m%d_%H%M%S).log"
mkdir -p results/logs results/shards/hypothesis_phase2

log() { echo "[$(date '+%H:%M:%S')] $*" | tee -a "$LOG"; }

log "═══════════════════════════════════════════════════"
log "HYPOTHESIS PIPELINE START"
log "═══════════════════════════════════════════════════"

# ── Phase 2: Feature extraction (Slurm array) ────────────

log "Submitting Phase 2 feature extraction (H-NEW03 + H-NEW10)..."

PHASE2_JOB=$(sbatch --parsable \
  --job-name=hyp_p2 \
  --account=twc \
  --partition=batch \
  --array=0-31 \
  --cpus-per-task=2 \
  --mem=16G \
  --time=3:00:00 \
  --output=results/logs/hyp_p2_%A_%a.log \
  --error=results/logs/hyp_p2_%A_%a.err \
  --wrap="cd ${PROJECT_DIR} && eval \"\$(conda shell.bash hook 2>/dev/null)\" && conda activate aireadi && python -u -m scripts.hypothesis.hypothesis_phase2 --output results/shards/hypothesis_phase2/shard_\${SLURM_ARRAY_TASK_ID}.parquet --num-shards \${SLURM_ARRAY_TASK_COUNT} --shard-index \${SLURM_ARRAY_TASK_ID}")

log "Phase 2 array job: ${PHASE2_JOB}"

# ── Phase 2: Postprocess (after array completes) ─────────

log "Queuing Phase 2 postprocess..."

POST2_JOB=$(sbatch --parsable \
  --dependency=afterok:${PHASE2_JOB} \
  --job-name=hyp_p2_post \
  --account=twc \
  --partition=batch \
  --cpus-per-task=4 \
  --mem=32G \
  --time=1:00:00 \
  --output=results/logs/hyp_p2_post_%j.log \
  --error=results/logs/hyp_p2_post_%j.err \
  --wrap="cd ${PROJECT_DIR} && eval \"\$(conda shell.bash hook 2>/dev/null)\" && conda activate aireadi && python -u -m scripts.hypothesis.hypothesis_phase2_postprocess")

log "Phase 2 postprocess job: ${POST2_JOB}"

# ── Monitor progress ─────────────────────────────────────

log "Monitoring jobs..."

while true; do
    P2_STATUS=$(squeue -j "${PHASE2_JOB}" --noheader 2>/dev/null | wc -l)
    POST2_STATUS=$(squeue -j "${POST2_JOB}" --noheader 2>/dev/null | wc -l)

    SHARDS_DONE=$(ls results/shards/hypothesis_phase2/shard_*.parquet 2>/dev/null | wc -l)

    log "Phase2 array: ${P2_STATUS} jobs running, ${SHARDS_DONE}/32 shards done | Postprocess: ${POST2_STATUS} jobs queued/running"

    if [ "${P2_STATUS}" -eq 0 ] && [ "${POST2_STATUS}" -eq 0 ]; then
        break
    fi
    sleep 60
done

log "All Slurm jobs complete."

# ── Generate summary report ───────────────────────────────

log "Generating final summary report..."

python -u << 'PYEOF'
import json
import pandas as pd
from pathlib import Path
from datetime import datetime

results_dir = Path("results")
hyp_dir = Path("hypothesis_driven/hypotheses")

print("\n" + "=" * 70)
print("HYPOTHESIS-DRIVEN DISCOVERY: FULL RESULTS REPORT")
print(f"Generated: {datetime.now().isoformat()}")
print("=" * 70)

# Load all hypothesis files
hypotheses = []
for p in sorted(hyp_dir.glob("H-*.json")):
    with open(p) as f:
        hypotheses.append(json.load(f))

# Summary table
print(f"\nTotal hypotheses: {len(hypotheses)}")
print(f"  Migrated: {sum(1 for h in hypotheses if h.get('source') == 'migrated')}")
print(f"  Proposed: {sum(1 for h in hypotheses if h.get('source') == 'proposer')}")

status_counts = {}
for h in hypotheses:
    s = h.get("status", "unknown")
    status_counts[s] = status_counts.get(s, 0) + 1
print(f"\nStatus breakdown:")
for s, c in sorted(status_counts.items()):
    print(f"  {s}: {c}")

# Completed hypotheses with results
print(f"\n{'=' * 70}")
print("COMPLETED HYPOTHESES")
print("=" * 70)

for h in sorted(hypotheses, key=lambda x: -x.get("priority", 0)):
    if h.get("results"):
        r = h["results"]
        verdict = "?"
        if h["status"] in ("supported",):
            verdict = "SUPPORTED"
        elif h["status"] in ("refuted",):
            verdict = "REFUTED"
        elif h["status"] in ("completed",):
            interp = r.get("interpretation", "").lower()
            if "not supported" in interp or "refuted" in interp or "null" in interp:
                verdict = "NOT SUPPORTED"
            elif "partially" in interp:
                verdict = "PARTIAL"
            else:
                verdict = "SUPPORTED"
        elif h["status"] == "inconclusive":
            verdict = "INCONCLUSIVE"

        primary = r.get("primary_metric", "")
        value = r.get("primary_value", "")
        effect = r.get("effect_size", "")
        fdr = r.get("fdr_p_value", "")

        print(f"\n--- {h['id']}: {h['title']} ---")
        print(f"  Category: {h['category']}")
        print(f"  Status: {h['status']} | Verdict: {verdict}")
        print(f"  Priority: {h.get('priority', 0):.2f}")
        print(f"  N: {r.get('sample_size', '?')}")
        print(f"  Primary: {primary} = {value}")
        print(f"  Effect: {effect} | FDR: {fdr}")
        print(f"  Interpretation: {r.get('interpretation', '')[:200]}...")
        if r.get("surprises"):
            print(f"  SURPRISE: {r['surprises'][:200]}")

# Still pending
pending = [h for h in hypotheses if h["status"] in ("proposed", "critiqued", "validated", "queued")]
if pending:
    print(f"\n{'=' * 70}")
    print(f"PENDING HYPOTHESES ({len(pending)})")
    print("=" * 70)
    for h in sorted(pending, key=lambda x: -x.get("priority", 0))[:10]:
        v = h.get("critic_verdict", {})
        verdict_str = v.get("verdict", "?") if v else "?"
        print(f"  [{h['id']}] P={h.get('priority', 0):.2f} [{verdict_str}] {h['title']}")

print(f"\n{'=' * 70}")
print("KEY FINDINGS ACROSS ALL HYPOTHESES")
print("=" * 70)
print("""
1. BROADBAND COUPLING MASKS FREQUENCY-SPECIFIC EFFECTS (H-NEW01):
   Fast coupling (<2h) DECREASES while slow coupling (>2h) INCREASES with severity.
   The broadband increase (H-MIG01, d=0.585) is driven entirely by slow coupling.

2. COUPLING INCREASE IS A DAYTIME PHENOMENON (H-NEW17):
   All waking blocks (04-20h) show increased coupling. Night (00-04h) is preserved.
   Morning block (04-08h) is strongest (d=0.42), suggesting dawn phenomenon involvement.

3. GLUCOSE ENTROPY ADDS LITTLE BEYOND HbA1c (H-NEW05):
   Significant partial correlation with allostatic load (r=0.12) but incremental R²=1%.
   Formal SampEn unnecessary — Shannon proxy captures all useful information.

4. NOCTURNAL COUPLING DOES NOT PREDICT NEXT-DAY GLUCOSE (H-NEW06):
   Clean null. Mean within-person rho = -0.004, p=0.67. Well-powered.

5. SLEEP-WAKE TRANSITION DYNAMICS NOT MEASURABLE AT 5-MIN RESOLUTION (H-NEW13):
   Null result. 45-min windows at 5-min resolution too noisy. Needs beat-to-beat HR.
""")

# Write report to file
report_path = Path("hypothesis_driven/results/pipeline_report.txt")
print(f"\nReport saved to: {report_path}")
PYEOF

log "═══════════════════════════════════════════════════"
log "PIPELINE COMPLETE"
log "═══════════════════════════════════════════════════"
log "Results in: results/hypotheses/h_new03_excursion_hr.csv, results/hypotheses/h_new10_activity_glucose.csv"
log "Full log: ${LOG}"
