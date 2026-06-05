"""CLI entry point for the AI-READI multi-agent system.

Usage:
    # Single question (orchestrator decomposes and dispatches)
    python -m agents.run "What is the mean HbA1c for each study group?"

    # Interactive mode
    python -m agents.run

    # Run a specific task pipeline
    python -m agents.run --task aging_clocks
    python -m agents.run --task causal_discovery
    python -m agents.run --task phenotyping
    python -m agents.run --task biomarkers
    python -m agents.run --task cross_modal
    python -m agents.run --task coupling_atlas

    # Single agent mode (bypass orchestrator)
    python -m agents.run --agent ClinicalAgent "Compare HbA1c across groups"

    # Options
    python -m agents.run --verbose "question"    # print full conversation
    python -m agents.run --critic "question"     # enable critic review
"""

import argparse
import sys

from . import config
from .workspace import Workspace
from .memory import Memory, create_default_memory
from .orchestrator import Orchestrator
from .critic import CriticAgent
from .modality import (
    ClinicalAgent, GlucoseAgent, CardiacAgent,
    WearableAgent, RetinalAgent, EnvironmentAgent,
)
from .reasoning import (
    HypothesisAgent, CausalAgent, PhenotypeAgent,
    AgingClockAgent, LiteratureAgent,
)


def build_system(workspace: Workspace | None = None,
                 memory: Memory | None = None) -> Orchestrator:
    """Build the full multi-agent system."""
    ws = workspace or Workspace()
    mem = memory or create_default_memory()

    orchestrator = Orchestrator(ws, mem)

    # Register all agents
    orchestrator.register_agents([
        # Tier 1: Modality agents
        ClinicalAgent(ws, mem),
        GlucoseAgent(ws, mem),
        CardiacAgent(ws, mem),
        WearableAgent(ws, mem),
        RetinalAgent(ws, mem),
        EnvironmentAgent(ws, mem),
        # Tier 2: Reasoning agents
        HypothesisAgent(ws, mem),
        CausalAgent(ws, mem),
        PhenotypeAgent(ws, mem),
        AgingClockAgent(ws, mem),
        LiteratureAgent(ws, mem),
    ])

    return orchestrator


def run_task_pipeline(task_name: str, orchestrator: Orchestrator) -> str:
    """Run a named task pipeline."""
    if task_name == "aging_clocks":
        from .tasks.aging_clocks import run_aging_clock_pipeline
        return run_aging_clock_pipeline(orchestrator)
    elif task_name == "causal_discovery":
        from .tasks.causal_discovery import run_causal_battery
        results = run_causal_battery(orchestrator)
        return "\n\n===\n\n".join(f"## {k}\n{v}" for k, v in results.items())
    elif task_name == "phenotyping":
        from .tasks.phenotyping import run_phenotyping_pipeline
        return run_phenotyping_pipeline(orchestrator)
    elif task_name == "biomarkers":
        from .tasks.biomarkers import run_biomarker_discovery
        results = run_biomarker_discovery(orchestrator)
        return "\n\n===\n\n".join(f"## {k}\n{v}" for k, v in results.items())
    elif task_name == "cross_modal":
        from .tasks.cross_modal import run_cross_modal_analysis
        results = run_cross_modal_analysis(orchestrator)
        return "\n\n===\n\n".join(f"## {k}\n{v}" for k, v in results.items())
    elif task_name == "coupling_atlas":
        from .tasks.coupling_atlas import run_coupling_atlas
        results = run_coupling_atlas(orchestrator)
        return "\n\n===\n\n".join(f"## Step {k}\n{v}" for k, v in results.items())
    else:
        return (
            f"Unknown task: {task_name}. Available: aging_clocks, causal_discovery, "
            "phenotyping, biomarkers, cross_modal, coupling_atlas"
        )


def main():
    parser = argparse.ArgumentParser(
        description="AI-READI multi-agent analysis system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("query", nargs="?", help="Research question to answer")
    parser.add_argument(
        "--task",
        help=(
            "Run a task pipeline (aging_clocks, causal_discovery, phenotyping, "
            "biomarkers, cross_modal, coupling_atlas)"
        ),
    )
    parser.add_argument("--agent", help="Run a specific agent directly (bypass orchestrator)")
    parser.add_argument("--critic", action="store_true", help="Enable critic review of findings")
    parser.add_argument("--verbose", action="store_true", help="Print full conversation history")
    parser.add_argument("--model", help="Override model name")
    args = parser.parse_args()

    if args.model:
        config.MODEL = args.model

    if not config.ANTHROPIC_API_KEY:
        print("Error: ANTHROPIC_API_KEY environment variable not set.", file=sys.stderr)
        sys.exit(1)

    # Build the system
    ws = Workspace()
    mem = create_default_memory()
    orchestrator = build_system(ws, mem)

    # Task pipeline mode
    if args.task:
        print(f"Running task pipeline: {args.task}")
        result = run_task_pipeline(args.task, orchestrator)
        print(result)
        mem.save()
        return

    # Single agent mode
    if args.agent and args.query:
        agent = orchestrator.agents.get(args.agent)
        if not agent:
            print(f"Unknown agent: {args.agent}", file=sys.stderr)
            print(f"Available: {', '.join(orchestrator.agents.keys())}", file=sys.stderr)
            sys.exit(1)
        result = agent.run(args.query)
        if args.verbose:
            for msg in result.history:
                print(f"\n--- {msg['role']} ---")
                if isinstance(msg["content"], str):
                    print(msg["content"][:2000])
                elif isinstance(msg["content"], list):
                    for block in msg["content"]:
                        if hasattr(block, "text"):
                            print(block.text[:1000])
                        elif isinstance(block, dict) and "content" in block:
                            print(str(block["content"])[:1000])
        print(result.answer)
        mem.save()
        return

    # Single query via orchestrator
    if args.query:
        answer = orchestrator.run(args.query)
        print(answer)

        if args.critic:
            critic = CriticAgent()
            for finding in ws.findings:
                if not any(v.finding_id == finding.id for v in ws.verdicts):
                    verdict = critic.review(
                        finding.id, finding.interpretation,
                        f"Feature: {finding.feature}, p={finding.pvalue}"
                    )
                    ws.add_verdict(verdict)
                    print(f"\n[Critic: {verdict.status}] {verdict.raw_text[:300]}")

        mem.save()
        return

    # Interactive mode
    print("AI-READI Multi-Agent Analysis System")
    print(f"Model: {config.MODEL}")
    print(f"Agents: {', '.join(orchestrator.agents.keys())}")
    print(f"{mem.summary()}")
    print("Type 'quit' to exit, 'workspace' to see state, 'memory' to see memory.\n")

    while True:
        try:
            query = input(">>> ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not query:
            continue
        if query.lower() in ("quit", "exit"):
            break
        if query.lower() == "workspace":
            print(ws.summary())
            continue
        if query.lower() == "memory":
            print(mem.summary())
            continue

        answer = orchestrator.run(query)
        print(answer)
        print()

    mem.save()
    print("Session saved.")


if __name__ == "__main__":
    main()
