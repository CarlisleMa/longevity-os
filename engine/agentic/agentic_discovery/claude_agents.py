"""Claude Agent SDK configuration for hypothesis-first discovery."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from claude_agent_sdk import AgentDefinition, ClaudeAgentOptions

from .claude_runtime import require_claude_runtime
from .claude_tools import allowed_tool_names, build_discovery_mcp_server


BASE_DISCOVERY_POLICY = """
You are operating inside a hypothesis-first scientific discovery system for
AI-READI aging, diabetes, disease burden, and multimodal physiology research.

Rules:
- Retrieve prior context before proposing, criticizing, or planning work.
- Treat data-derived surprises as quarantined candidates first, not conclusions.
- Every hypothesis must state mechanism, direction, required modalities,
  confounders, leakage risks, negative controls, and refutation logic.
- Do not claim a result is supported until execution artifacts and mechanical
  verification have been registered.
- Prefer registering structured records through tools over free-text memory.
- Preserve provenance: cite candidate IDs, paper IDs, tool IDs, dataset IDs,
  run IDs, verification IDs, artifact paths, and graph edges when available.
- Do not run raw shell commands or mutate source files. Slurm submission is
  allowed only through the guarded execution-spec tools, only when the human
  instruction explicitly asks for execution, and only after dry-run validation.
""".strip()


MANAGER_PROMPT = (
    BASE_DISCOVERY_POLICY
    + """

	Role: Discovery Round Manager.
	Coordinate specialist subagents. A normal round should retrieve context, enrich
	literature/tools/datasets, critique, check feasibility/leakage, register a
	method plan when appropriate, optionally use guarded Slurm execution specs when
	explicitly authorized, register evidence/verification if supplied, and deposit
	follow-up candidates or surprises. Execution proposals must be reviewed by the
	scientific-critic, feasibility-leakage, and mechanical-verifier subagents before
	promotion; do not substitute a manager-written verification for those gates.
	Keep the final output concise and grounded in registered record IDs.
	"""
)


def build_claude_options(
    state_root: str,
    model: str | None = None,
    max_turns: int | None = None,
    cwd: str | Path | None = None,
    effort: str | None = None,
) -> ClaudeAgentOptions:
    server = build_discovery_mcp_server(state_root=state_root)
    tool_names = ["Read", "Glob", "Grep", "Agent"] + allowed_tool_names()
    return ClaudeAgentOptions(
        cli_path=require_claude_runtime(),
        cwd=str(cwd) if cwd else None,
        model=model,
        max_turns=max_turns,
        effort=effort,
        system_prompt=MANAGER_PROMPT,
        tools=["Read", "Glob", "Grep", "Agent"],
        allowed_tools=tool_names,
        mcp_servers={"agentic_discovery": server},
        agents=_agent_definitions(),
    )


def _agent_definitions() -> dict[str, Any]:
    def mcp(tool_name: str) -> str:
        return f"mcp__agentic_discovery__{tool_name}"

    common_read_tools = [
        "Read",
        "Glob",
        "Grep",
        mcp("registry_summary"),
        mcp("search_registry"),
        mcp("retrieve_context"),
    ]
    literature_tools = common_read_tools + [
        mcp("register_paper"),
        mcp("register_claim"),
        mcp("register_method"),
        mcp("register_dataset"),
        mcp("add_edge"),
    ]
    hypothesis_tools = common_read_tools + [
        mcp("deposit_candidate"),
        mcp("update_candidate_status"),
        mcp("add_edge"),
    ]
    scientific_tools = common_read_tools + [
        mcp("retrieve_execution_proposal"),
        mcp("register_verification"),
        mcp("scientific_critic_review_execution_proposal"),
        mcp("add_edge"),
    ]
    feasibility_tools = common_read_tools + [
        mcp("retrieve_execution_proposal"),
        mcp("register_verification"),
        mcp("feasibility_leakage_review_execution_proposal"),
        mcp("add_edge"),
    ]
    method_planner_tools = common_read_tools + [
        mcp("register_method_plan"),
        mcp("register_verification"),
        mcp("update_candidate_status"),
        mcp("add_edge"),
    ]
    executor_tools = common_read_tools + [
        mcp("propose_execution"),
        mcp("list_execution_proposals"),
        mcp("retrieve_execution_proposal"),
        mcp("validate_execution_proposal"),
        mcp("promote_execution_proposal"),
        mcp("list_execution_specs"),
        mcp("dry_run_execution_spec"),
        mcp("submit_execution_spec"),
        mcp("check_slurm_status"),
        mcp("ingest_execution_run"),
        mcp("register_run"),
    ]
    mechanical_tools = common_read_tools + [
        mcp("retrieve_execution_proposal"),
        mcp("list_execution_proposals"),
        mcp("list_execution_specs"),
        mcp("dry_run_execution_spec"),
        mcp("check_slurm_status"),
        mcp("ingest_execution_run"),
        mcp("register_verification"),
        mcp("mechanical_verifier_review_execution_proposal"),
    ]
    surprise_tools = common_read_tools + [
        mcp("register_surprise"),
        mcp("deposit_candidate"),
        mcp("add_edge"),
    ]
    synthesis_tools = common_read_tools + [
        mcp("list_execution_proposals"),
        mcp("list_execution_specs"),
        mcp("check_slurm_status"),
    ]
    return {
        "literature-tool-dataset": AgentDefinition(
            description="Finds and registers relevant papers, extracted claims, computational tools, and datasets.",
            prompt=BASE_DISCOVERY_POLICY
            + "\n\nRegister literature, tools, datasets, and extracted claims that affect feasibility, novelty, biological plausibility, or redundancy.",
            tools=literature_tools,
        ),
        "hypothesis-depositor": AgentDefinition(
            description="Turns ideas, surprises, literature, critic objections, and results into quarantined candidates.",
            prompt=BASE_DISCOVERY_POLICY
            + "\n\nDeposit structured hypothesis candidates and add graph edges to parents or evidence.",
            tools=hypothesis_tools,
        ),
        "scientific-critic": AgentDefinition(
            description="Critiques mechanism, falsifiability, confounding, leakage, feasibility, and inductive bias.",
            prompt=BASE_DISCOVERY_POLICY
            + "\n\nRegister verification records with pass, concern, fail, or inconclusive verdicts. When asked to review an execution proposal, retrieve the full proposal context, check biological alignment, endpoint validity, statistical design, refutation logic, and whether the code actually tests the hypothesis, then record your gate verdict with scientific_critic_review_execution_proposal.",
            tools=scientific_tools,
        ),
        "feasibility-leakage": AgentDefinition(
            description="Reviews data feasibility, participant splits, balance, leakage, missingness, and negative controls.",
            prompt=BASE_DISCOVERY_POLICY
            + "\n\nFocus on AI-READI modality coverage, split integrity, preprocessing leakage, age/site/disease-group balance, and target leakage. When asked to review an execution proposal, retrieve the proposal context, inspect required inputs, split/confounder handling, missingness assumptions, leakage controls, and negative controls, then record your gate verdict with feasibility_leakage_review_execution_proposal.",
            tools=feasibility_tools,
        ),
        "method-planner": AgentDefinition(
            description="Registers method plans for feasible candidates without executing them.",
            prompt=BASE_DISCOVERY_POLICY
            + "\n\nSpecify inputs, outputs, split ID, adjustment set, negative controls, leakage checks, tests, execution steps, and artifacts.",
            tools=method_planner_tools,
        ),
        "executor-record": AgentDefinition(
            description="Compiles feasible method plans into quarantined execution proposals, promotes validated specs, and uses guarded Slurm tools.",
            prompt=BASE_DISCOVERY_POLICY
            + "\n\nFor new analyses, use propose_execution and validate_execution_proposal, then wait for scientific-critic, feasibility-leakage, and mechanical-verifier reviews before promote_execution_proposal. You do not have reviewer-gate tools; ask the manager to dispatch reviewer agents. For execution, use only list_execution_specs, dry_run_execution_spec, submit_execution_spec, check_slurm_status, and ingest_execution_run. Never invent arbitrary commands.",
            tools=executor_tools,
        ),
        "mechanical-verifier": AgentDefinition(
            description="Registers mechanical verification outcomes and follow-up blockers.",
            prompt=BASE_DISCOVERY_POLICY
            + "\n\nCheck split integrity, target/input separation, adjustment, FDR, negative controls, reproducibility, and artifact provenance. When asked to review an execution proposal, retrieve the proposal context, check static-validation results, script/spec consistency, approved paths, expected artifacts, Slurm-resource reasonableness, and reproducibility metadata, then record your gate verdict with mechanical_verifier_review_execution_proposal.",
            tools=mechanical_tools,
        ),
        "surprise-miner": AgentDefinition(
            description="Registers unexpected findings and follow-up candidates.",
            prompt=BASE_DISCOVERY_POLICY
            + "\n\nConvert surprises into SurpriseRecord objects and quarantined follow-up candidates with p-hacking risks.",
            tools=surprise_tools,
        ),
        "synthesis-reporter": AgentDefinition(
            description="Summarizes the registry state, what changed, blockers, and next queue.",
            prompt=BASE_DISCOVERY_POLICY
            + "\n\nWrite concise synthesis grounded in record IDs and artifact paths.",
            tools=synthesis_tools,
        ),
    }
