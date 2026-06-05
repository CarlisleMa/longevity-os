"""Autonomous hypothesis discovery pipeline.

Runs the full cycle: propose → critique → execute → verify.
No human in the loop.

Usage:
    python -m hypothesis_driven.run_pipeline --max-cycles 5
    python -m hypothesis_driven.run_pipeline --max-cycles 1 --dry-run  # propose + critique only
    python -m hypothesis_driven                                        # alias via __main__.py
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

from agents import config
from agents.memory import Memory

from .workspace import HypothesisWorkspace
from .proposer import ProposerAgent
from .hypothesis_critic import HypothesisCriticAgent
from .executor import ExecutorAgent
from .verifier import VerifierAgent

LOG_DIR = config.RESULTS_DIR / "logs"


def setup_logging(log_dir: Path) -> logging.Logger:
    """Configure logging to file + console."""
    log_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = log_dir / f"pipeline_{timestamp}.log"

    logger = logging.getLogger("hypothesis_driven")
    logger.setLevel(logging.DEBUG)

    # File handler (detailed)
    fh = logging.FileHandler(log_path)
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(fh)

    # Console handler (info only)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("[%(asctime)s] %(message)s", datefmt="%H:%M:%S"))
    logger.addHandler(ch)

    logger.info("Pipeline log: %s", log_path)
    return logger


def run_cycle(
    cycle: int,
    workspace: HypothesisWorkspace,
    proposer: ProposerAgent,
    critic: HypothesisCriticAgent,
    executor: ExecutorAgent,
    verifier: VerifierAgent,
    batch_size: int,
    dry_run: bool,
    log: logging.Logger,
) -> str:
    """Run one pipeline cycle. Returns a status string."""
    log.info("=" * 60)
    log.info("CYCLE %d", cycle + 1)
    log.info("=" * 60)

    workspace.reload()

    # Check for completed hypotheses that need verification
    completed = workspace.by_status("completed")
    if completed:
        h = completed[0]
        log.info("Verifying completed hypothesis: %s", h.id)
        status = verifier.verify(h, workspace)
        log.info("  → %s", status)
        return f"verified:{h.id}:{status}"

    # Check for hypotheses ready to execute
    h = workspace.next_to_execute()
    if h is not None:
        if dry_run:
            log.info("DRY RUN: Would execute %s (P=%.2f): %s", h.id, h.priority, h.title)
            return f"dry_run:would_execute:{h.id}"

        log.info("Executing top hypothesis: %s (P=%.2f): %s", h.id, h.priority, h.title)
        result = executor.execute(h, workspace)
        if result:
            log.info("  → Completed. Primary: %s = %.3f",
                     result.primary_metric, result.primary_value)
            return f"executed:{h.id}"
        log.warning("  → Execution failed, returned to queue")
        return f"failed:{h.id}"

    # Queue empty — propose new batch
    log.info("Queue empty. Proposing %d new hypotheses...", batch_size)
    ids = proposer.propose_and_deposit(n=batch_size)
    log.info("  Proposed %d hypotheses: %s", len(ids), ids)

    # Critique each
    for hid in ids:
        h = workspace.get(hid)
        if h is None:
            continue
        log.info("  Critiquing %s: %s", h.id, h.title)
        verdict = critic.review_and_update(h, workspace)
        log.info("    → %s (score=%.2f)", verdict.verdict, verdict.overall_score)

    validated = workspace.by_status("validated")
    log.info("  %d hypotheses validated and queued", len(validated))
    return f"proposed:{len(ids)}:validated:{len(validated)}"


def main():
    parser = argparse.ArgumentParser(description="Autonomous hypothesis discovery pipeline")
    parser.add_argument("--max-cycles", type=int, default=5,
                        help="Maximum number of pipeline cycles")
    parser.add_argument("--batch-size", type=int, default=3,
                        help="Number of hypotheses to propose per batch")
    parser.add_argument("--poll-interval", type=int, default=60,
                        help="Seconds between Slurm job status polls")
    parser.add_argument("--dry-run", action="store_true",
                        help="Propose + critique only, do not submit Slurm jobs")
    parser.add_argument("--workspace-dir", type=str, default=None,
                        help="Hypothesis workspace directory")
    parser.add_argument("--model", type=str, default=None,
                        help="Override Claude model for all agents")
    args = parser.parse_args()

    # Check API key
    if not config.ANTHROPIC_API_KEY:
        print("ERROR: ANTHROPIC_API_KEY not set. Check .env file.", file=sys.stderr)
        sys.exit(1)

    log = setup_logging(LOG_DIR)
    log.info("Hypothesis Discovery Pipeline starting")
    log.info("  max_cycles=%d, batch_size=%d, dry_run=%s",
             args.max_cycles, args.batch_size, args.dry_run)

    # Initialize components
    workspace = HypothesisWorkspace(root=args.workspace_dir)
    memory = Memory()

    model = args.model
    proposer = ProposerAgent(hyp_workspace=workspace, memory=memory, model=model)
    critic = HypothesisCriticAgent(model=model)
    executor = ExecutorAgent(hyp_workspace=workspace, memory=memory, model=model)
    verifier = VerifierAgent(model=model)

    log.info("Workspace: %d hypotheses", len(workspace.all()))
    log.info(workspace.summary())

    # Main loop
    cycle_results = []
    try:
        for cycle in range(args.max_cycles):
            result = run_cycle(
                cycle, workspace, proposer, critic, executor, verifier,
                args.batch_size, args.dry_run, log,
            )
            cycle_results.append(result)
            log.info("Cycle %d result: %s", cycle + 1, result)

            # Brief pause between cycles
            if cycle < args.max_cycles - 1:
                time.sleep(2)

    except KeyboardInterrupt:
        log.info("Pipeline interrupted by user")
    except Exception as e:
        log.error("Pipeline error: %s", e, exc_info=True)
    finally:
        # Final summary
        log.info("=" * 60)
        log.info("PIPELINE COMPLETE")
        log.info("=" * 60)
        log.info("Cycles run: %d", len(cycle_results))
        for i, r in enumerate(cycle_results):
            log.info("  Cycle %d: %s", i + 1, r)
        log.info("\nFinal workspace state:")
        log.info(workspace.summary())


if __name__ == "__main__":
    main()
