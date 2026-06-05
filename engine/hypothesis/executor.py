"""Executor Agent: generates analysis scripts, submits Slurm jobs, collects results.

Subclass of BaseAgent with code execution enabled.
Flow: generate_script() → submit_slurm() → wait_for_completion() → collect_results()
"""

from __future__ import annotations

import ast
import json
import logging
import subprocess
import time
from pathlib import Path

from agents.base import BaseAgent
from agents.workspace import Workspace
from agents.memory import Memory
from agents import config

from .schemas import Hypothesis, HypothesisResult, SensitivityCheck
from .workspace import HypothesisWorkspace

log = logging.getLogger(__name__)

PROJECT_DIR = config.PROJECT_ROOT
RESULTS_DIR = config.RESULTS_DIR
SCRIPTS_DIR = PROJECT_DIR / "scripts" / "hypothesis_auto"
SHARDS_DIR = RESULTS_DIR / "hypothesis_auto_shards"
RESULTS_AUTO_DIR = RESULTS_DIR / "hypothesis_auto"

# Slurm defaults
SLURM_ACCOUNT = "twc"
SLURM_PARTITION = "batch"
SLURM_CONDA_ENV = "aireadi"

EXECUTOR_PROMPT = """\
You are a scientific analysis code generator for the AI-READI dataset.
Given a hypothesis with a detailed test plan, generate a complete Python analysis script.

THE SCRIPT MUST:
1. Accept --num-shards, --shard-index, --output CLI arguments (argparse)
2. Load participant IDs from results/coupling_features.parquet index
3. Shard participants: shard_ids = [pid for i, pid in enumerate(all_ids) if i % num_shards == shard_index]
4. For each participant, load aligned time series and compute the hypothesis-specific features
5. Save per-shard output as parquet to --output path

AVAILABLE DATA LOADERS:
  from scripts.loaders.cgm import load_cgm  # -> (DataFrame, meta)
  from scripts.loaders.wearable import load_wearable_submodality  # -> DataFrame
  from scripts.utils.temporal import align_timeseries  # -> aligned DataFrame
  from scripts.utils.timezone import get_timezone  # -> timezone string
  from scripts.config import RESULTS_DIR

ALIGNMENT PATTERN (copy exactly):
  sources = {}
  cgm, _ = load_cgm(person_id)
  sources["cgm"] = cgm[["glucose_mg_dl"]].apply(pd.to_numeric, errors="coerce").dropna()
  hr = load_wearable_submodality(person_id, "heart_rate")
  hr_num = hr[["value"]].apply(pd.to_numeric, errors="coerce").rename(columns={"value": "bpm"}).dropna()
  sources["hr"] = hr_num
  aligned = align_timeseries(sources, freq="5min", method="nearest", tolerance="10min")

STATISTICAL TESTING CONSTANTS:
  STUDY_GROUP_ORDER = ("healthy", "pre_diabetes_lifestyle_controlled",
    "oral_medication_and_or_non_insulin_injectable_medication_controlled", "insulin_dependent")

ALSO GENERATE A POSTPROCESS COMPANION SCRIPT that:
1. Merges all shards from results/hypothesis_auto_shards/{hypothesis_id}_shard_*.parquet
2. Joins with participant_index.parquet, feature_matrix.parquet, clinical_scores.parquet
3. Runs Kruskal-Wallis + Spearman trend + Cohen's d (H vs ID) for each feature
4. Applies FDR correction (statsmodels.stats.multitest.multipletests)
5. Writes CSV results to results/hypothesis_auto/{hypothesis_id}_results.csv
6. Writes a JSON summary to results/hypothesis_auto/{hypothesis_id}_summary.json with:
   {"sample_size": N, "primary_metric": "...", "primary_value": X, "effect_size": X,
    "effect_size_type": "cohen_d", "p_value": X, "fdr_p_value": X,
    "group_values": {"healthy": X, ...}, "group_ns": {"healthy": N, ...},
    "features_tested": N, "features_significant": N}

OUTPUT FORMAT: Two Python code blocks, clearly separated:
```python
# === SHARD SCRIPT: {hypothesis_id}.py ===
...
```

```python
# === POSTPROCESS SCRIPT: {hypothesis_id}_postprocess.py ===
...
```
"""


class ExecutorAgent(BaseAgent):
    """Generates analysis scripts, submits to Slurm, monitors, collects results."""

    name = "ExecutorAgent"
    system_prompt = EXECUTOR_PROMPT
    can_execute_code = True

    def __init__(
        self,
        hyp_workspace: HypothesisWorkspace,
        memory: Memory,
        model: str | None = None,
    ):
        ws = Workspace()
        super().__init__(workspace=ws, memory=memory, model=model)
        self.hyp_workspace = hyp_workspace

    # ── Script generation ─────────────────────────────────────────────

    def generate_script(self, h: Hypothesis) -> tuple[Path, Path]:
        """Generate shard + postprocess scripts from the hypothesis test plan.

        Returns (shard_script_path, postprocess_script_path).
        """
        SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)

        task = (
            f"Generate a complete analysis script for this hypothesis:\n\n"
            f"{h.full_report()}\n\n"
            f"The hypothesis ID is: {h.id}\n"
            f"Shard output dir: results/hypothesis_auto_shards/\n"
            f"Results output dir: results/hypothesis_auto/\n"
        )

        result = self.run(task)

        # Extract code blocks from LLM output
        shard_code, post_code = self._extract_scripts(result.answer, h.id)

        # Validate syntax
        for label, code in [("shard", shard_code), ("postprocess", post_code)]:
            try:
                ast.parse(code)
            except SyntaxError as e:
                log.error("Generated %s script has syntax error: %s", label, e)
                raise

        # Write scripts
        # Convert hypothesis ID to valid module name
        module_name = h.id.replace("-", "_").lower()
        shard_path = SCRIPTS_DIR / f"{module_name}.py"
        post_path = SCRIPTS_DIR / f"{module_name}_postprocess.py"

        shard_path.write_text(shard_code)
        post_path.write_text(post_code)

        # Ensure __init__.py exists
        init_path = SCRIPTS_DIR / "__init__.py"
        if not init_path.exists():
            init_path.write_text("")

        log.info("Generated scripts: %s, %s", shard_path.name, post_path.name)
        return shard_path, post_path

    def _extract_scripts(self, text: str, hypothesis_id: str) -> tuple[str, str]:
        """Extract two Python code blocks from LLM output."""
        blocks = []
        parts = text.split("```python")
        for part in parts[1:]:  # skip text before first code block
            code = part.split("```")[0].strip()
            if code:
                blocks.append(code)

        if len(blocks) >= 2:
            return blocks[0], blocks[1]
        if len(blocks) == 1:
            # Single block — treat as shard script, generate minimal postprocess
            log.warning("Only 1 code block found, generating minimal postprocess")
            return blocks[0], self._minimal_postprocess(hypothesis_id)

        raise ValueError(f"No Python code blocks found in LLM output ({len(text)} chars)")

    def _minimal_postprocess(self, hypothesis_id: str) -> str:
        """Generate a minimal postprocess script."""
        module = hypothesis_id.replace("-", "_").lower()
        return f'''\
"""Minimal postprocess for {hypothesis_id}."""
import pandas as pd
import json
from pathlib import Path
from scipy import stats
from statsmodels.stats.multitest import multipletests

RESULTS_DIR = Path("results")
SHARDS_DIR = RESULTS_DIR / "hypothesis_auto_shards"
OUT_DIR = RESULTS_DIR / "hypothesis_auto"
OUT_DIR.mkdir(parents=True, exist_ok=True)

shards = sorted(SHARDS_DIR.glob("{module}_shard_*.parquet"))
if not shards:
    print("No shards found")
    exit(1)

df = pd.concat([pd.read_parquet(s) for s in shards])
df = df[~df.index.duplicated(keep="first")]
pi = pd.read_parquet(RESULTS_DIR / "participant_index.parquet")
df = df.join(pi[["study_group"]], how="left")

print(f"Combined: {{len(df)}} participants")
summary = {{"sample_size": len(df), "hypothesis_id": "{hypothesis_id}"}}
with open(OUT_DIR / "{module}_summary.json", "w") as f:
    json.dump(summary, f, indent=2)
print("Done")
'''

    # ── Slurm submission ──────────────────────────────────────────────

    def submit_slurm(
        self, h: Hypothesis, shard_path: Path, post_path: Path
    ) -> tuple[int, int]:
        """Submit shard array job + postprocess dependency.

        Returns (array_job_id, postprocess_job_id).
        """
        SHARDS_DIR.mkdir(parents=True, exist_ok=True)
        RESULTS_AUTO_DIR.mkdir(parents=True, exist_ok=True)
        (RESULTS_DIR / "logs").mkdir(parents=True, exist_ok=True)

        module_name = h.id.replace("-", "_").lower()

        # Determine shard count from computational cost
        cost = h.feasibility.computational_cost if h.feasibility else "medium"
        n_shards = {"low": 8, "medium": 16, "high": 32}.get(cost, 16)

        # Array job
        shard_cmd = (
            f"sbatch --parsable"
            f" --job-name=hyp_{module_name}"
            f" --account={SLURM_ACCOUNT}"
            f" --partition={SLURM_PARTITION}"
            f" --array=0-{n_shards - 1}"
            f" --cpus-per-task=2"
            f" --mem=16G"
            f" --time=3:00:00"
            f" --output=results/logs/hyp_{module_name}_%A_%a.log"
            f" --error=results/logs/hyp_{module_name}_%A_%a.err"
            f' --wrap="cd {PROJECT_DIR}'
            f" && eval \\\"\\$(conda shell.bash hook 2>/dev/null)\\\""
            f" && conda activate {SLURM_CONDA_ENV}"
            f" && python -u -m scripts.hypothesis_auto.{module_name}"
            f" --output results/hypothesis_auto_shards/{module_name}_shard_${{SLURM_ARRAY_TASK_ID}}.parquet"
            f" --num-shards ${{SLURM_ARRAY_TASK_COUNT}}"
            f' --shard-index ${{SLURM_ARRAY_TASK_ID}}"'
        )

        log.info("Submitting shard array job (%d shards)...", n_shards)
        result = subprocess.run(shard_cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"sbatch failed: {result.stderr}")
        array_job_id = int(result.stdout.strip())
        log.info("  Array job: %d", array_job_id)

        # Postprocess with dependency
        post_cmd = (
            f"sbatch --parsable"
            f" --dependency=afterok:{array_job_id}"
            f" --job-name=hyp_{module_name}_post"
            f" --account={SLURM_ACCOUNT}"
            f" --partition={SLURM_PARTITION}"
            f" --cpus-per-task=4"
            f" --mem=32G"
            f" --time=1:00:00"
            f" --output=results/logs/hyp_{module_name}_post_%j.log"
            f" --error=results/logs/hyp_{module_name}_post_%j.err"
            f' --wrap="cd {PROJECT_DIR}'
            f" && eval \\\"\\$(conda shell.bash hook 2>/dev/null)\\\""
            f" && conda activate {SLURM_CONDA_ENV}"
            f' && python -u -m scripts.hypothesis_auto.{module_name}_postprocess"'
        )

        result = subprocess.run(post_cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"sbatch postprocess failed: {result.stderr}")
        post_job_id = int(result.stdout.strip())
        log.info("  Postprocess job: %d (depends on %d)", post_job_id, array_job_id)

        return array_job_id, post_job_id

    # ── Job monitoring ────────────────────────────────────────────────

    def wait_for_completion(
        self, job_ids: list[int], poll_interval: int = 60, timeout: int = 14400
    ) -> bool:
        """Poll squeue until all jobs complete. Returns True on success."""
        start = time.time()
        job_str = ",".join(str(j) for j in job_ids)

        while time.time() - start < timeout:
            result = subprocess.run(
                f"squeue -j {job_str} --noheader",
                shell=True, capture_output=True, text=True,
            )
            remaining = len([l for l in result.stdout.strip().split("\n") if l.strip()])
            elapsed = int(time.time() - start)

            if remaining == 0:
                log.info("All jobs complete (elapsed: %ds)", elapsed)
                # Check exit status
                for jid in job_ids:
                    sacct = subprocess.run(
                        f"sacct -j {jid} --format=State --noheader --parsable2",
                        shell=True, capture_output=True, text=True,
                    )
                    states = [s.strip() for s in sacct.stdout.strip().split("\n") if s.strip()]
                    failed = [s for s in states if s not in ("COMPLETED", "")]
                    if failed:
                        log.warning("Job %d had non-COMPLETED states: %s", jid, failed)
                return True

            log.debug("  %d jobs remaining (elapsed: %ds)", remaining, elapsed)
            time.sleep(poll_interval)

        log.error("Timeout after %ds waiting for jobs %s", timeout, job_str)
        # Cancel remaining
        subprocess.run(f"scancel {job_str}", shell=True, capture_output=True)
        return False

    # ── Result collection ─────────────────────────────────────────────

    def collect_results(self, h: Hypothesis) -> HypothesisResult | None:
        """Read the JSON summary written by the postprocess script."""
        module_name = h.id.replace("-", "_").lower()
        summary_path = RESULTS_AUTO_DIR / f"{module_name}_summary.json"

        if not summary_path.exists():
            log.error("Summary not found: %s", summary_path)
            return None

        with open(summary_path) as f:
            data = json.load(f)

        return HypothesisResult(
            method_used=data.get("method_used", h.test_plan.primary_method if h.test_plan else ""),
            sample_size=data.get("sample_size", 0),
            primary_metric=data.get("primary_metric", ""),
            primary_value=data.get("primary_value", 0.0),
            effect_size=data.get("effect_size", 0.0),
            effect_size_type=data.get("effect_size_type", "cohen_d"),
            p_value=data.get("p_value", 1.0),
            fdr_p_value=data.get("fdr_p_value", 1.0),
            confidence_interval=tuple(data["confidence_interval"]) if data.get("confidence_interval") else None,
            confounders_adjusted=data.get("confounders_adjusted", []),
            sensitivity_checks=[
                SensitivityCheck(**sc) if isinstance(sc, dict) else sc
                for sc in data.get("sensitivity_checks", [])
            ],
            group_values=data.get("group_values", {}),
            group_ns=data.get("group_ns", {}),
            interpretation=data.get("interpretation", ""),
            surprises=data.get("surprises", ""),
            output_files=data.get("output_files", [str(summary_path)]),
        )

    # ── Full execution flow ───────────────────────────────────────────

    def execute(self, h: Hypothesis, workspace: HypothesisWorkspace) -> HypothesisResult | None:
        """Full execution: generate → submit → wait → collect.

        Returns HypothesisResult on success, None on failure.
        """
        log.info("=" * 50)
        log.info("Executing %s: %s", h.id, h.title)
        log.info("=" * 50)

        workspace.update_status(h.id, "executing")

        try:
            # 1. Generate scripts
            shard_path, post_path = self.generate_script(h)

            # 2. Submit to Slurm
            array_id, post_id = self.submit_slurm(h, shard_path, post_path)

            # 3. Wait for completion
            success = self.wait_for_completion([array_id, post_id])
            if not success:
                log.error("Jobs timed out for %s", h.id)
                workspace.update_status(h.id, "validated")  # Return to queue
                return None

            # 4. Collect results
            result = self.collect_results(h)
            if result is None:
                log.error("No results collected for %s", h.id)
                workspace.update_status(h.id, "validated")
                return None

            # 5. Update workspace
            workspace.set_results(h.id, result)
            log.info("Execution complete: %s = %.3f (p=%.2e)",
                     result.primary_metric, result.primary_value, result.p_value)
            return result

        except Exception as e:
            log.error("Execution failed for %s: %s", h.id, e, exc_info=True)
            workspace.update_status(h.id, "validated")  # Return to queue for retry
            return None
