"""Claude Agent SDK tool wrappers around the discovery registry tools."""

from __future__ import annotations

import json
from typing import Any, Callable

from claude_agent_sdk import ToolAnnotations, create_sdk_mcp_server, tool

from . import registry_tools


SERVER_NAME = "agentic_discovery"


def build_discovery_mcp_server(state_root: str = ""):
    tools = [
        _registry_summary_tool(state_root),
        _search_registry_tool(state_root),
        _retrieve_context_tool(state_root),
        _deposit_candidate_tool(state_root),
        _update_candidate_status_tool(state_root),
        _register_paper_tool(state_root),
        _register_claim_tool(state_root),
        _register_method_tool(state_root),
        _register_dataset_tool(state_root),
        _register_surprise_tool(state_root),
        _add_edge_tool(state_root),
        _register_method_plan_tool(state_root),
        _register_run_tool(state_root),
        _register_verification_tool(state_root),
        _propose_execution_tool(state_root),
        _list_execution_proposals_tool(state_root),
        _retrieve_execution_proposal_tool(state_root),
        _validate_execution_proposal_tool(state_root),
        _fixed_reviewer_execution_proposal_tool(
            state_root,
            tool_name="scientific_critic_review_execution_proposal",
            reviewer="scientific-critic",
            description="Register the scientific-critic gate verdict for an execution proposal.",
        ),
        _fixed_reviewer_execution_proposal_tool(
            state_root,
            tool_name="feasibility_leakage_review_execution_proposal",
            reviewer="feasibility-leakage",
            description="Register the feasibility-leakage gate verdict for an execution proposal.",
        ),
        _fixed_reviewer_execution_proposal_tool(
            state_root,
            tool_name="mechanical_verifier_review_execution_proposal",
            reviewer="mechanical-verifier",
            description="Register the mechanical-verifier gate verdict for an execution proposal.",
        ),
        _promote_execution_proposal_tool(state_root),
        _list_execution_specs_tool(state_root),
        _dry_run_execution_spec_tool(state_root),
        _submit_execution_spec_tool(state_root),
        _check_slurm_status_tool(state_root),
        _ingest_execution_run_tool(state_root),
    ]
    return create_sdk_mcp_server(name=SERVER_NAME, version="1.0.0", tools=tools)


def allowed_tool_names() -> list[str]:
    return [f"mcp__{SERVER_NAME}__*"]


def _registry_summary_tool(state_root: str):
    @tool(
        "registry_summary",
        "Return registry counts and current candidate queue summary.",
        {},
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    async def registry_summary(args: dict[str, Any]) -> dict[str, Any]:
        return _ok(registry_tools.registry_summary_tool(state_root=state_root))

    return registry_summary


def _search_registry_tool(state_root: str):
    @tool(
        "search_registry",
        "Search candidates, knowledge records, evidence records, and legacy hypotheses.",
        _schema(
            {
                "query": {"type": "string"},
                "kinds_csv": {"type": "string", "default": ""},
                "limit": {"type": "integer", "default": 8},
            },
            required=["query"],
        ),
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    async def search_registry(args: dict[str, Any]) -> dict[str, Any]:
        return _ok(
            registry_tools.search_registry_tool(
                query=args["query"],
                kinds_csv=args.get("kinds_csv", ""),
                limit=int(args.get("limit", 8)),
                state_root=state_root,
            )
        )

    return search_registry


def _retrieve_context_tool(state_root: str):
    @tool(
        "retrieve_context",
        "Retrieve prior project context for a candidate or legacy hypothesis.",
        _schema(
            {
                "target_id": {"type": "string"},
                "target_type": {"type": "string", "default": "candidate"},
                "limit": {"type": "integer", "default": 10},
            },
            required=["target_id"],
        ),
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    async def retrieve_context(args: dict[str, Any]) -> dict[str, Any]:
        return _ok(
            registry_tools.retrieve_context_tool(
                target_id=args["target_id"],
                target_type=args.get("target_type", "candidate"),
                limit=int(args.get("limit", 10)),
                state_root=state_root,
            )
        )

    return retrieve_context


def _deposit_candidate_tool(state_root: str):
    @tool(
        "deposit_candidate",
        "Deposit a quarantined hypothesis candidate. CSV fields are comma-separated lists.",
        _schema(
            {
                "title": {"type": "string"},
                "claim": {"type": "string"},
                "mechanism": {"type": "string", "default": ""},
                "expected_direction": {"type": "string", "default": ""},
                "required_modalities_csv": {"type": "string", "default": ""},
                "primary_outcome": {"type": "string", "default": ""},
                "confounders_csv": {"type": "string", "default": ""},
                "negative_controls_csv": {"type": "string", "default": ""},
                "leakage_risks_csv": {"type": "string", "default": ""},
                "needs_csv": {"type": "string", "default": ""},
                "priority": {"type": "number", "default": 0.5},
                "origin_type": {"type": "string", "default": "agent_round"},
                "origin_agent": {"type": "string", "default": "claude_agent"},
                "origin_detail": {"type": "string", "default": ""},
                "trigger_artifacts_csv": {"type": "string", "default": ""},
                "tags_csv": {"type": "string", "default": ""},
                "notes": {"type": "string", "default": ""},
            },
            required=["title", "claim"],
        ),
    )
    async def deposit_candidate(args: dict[str, Any]) -> dict[str, Any]:
        return _call(
            registry_tools.deposit_candidate_tool,
            state_root=state_root,
            **args,
        )

    return deposit_candidate


def _update_candidate_status_tool(state_root: str):
    @tool(
        "update_candidate_status",
        "Update candidate lifecycle status with an optional note.",
        _schema(
            {
                "candidate_id": {"type": "string"},
                "status": {"type": "string"},
                "note": {"type": "string", "default": ""},
            },
            required=["candidate_id", "status"],
        ),
    )
    async def update_candidate_status(args: dict[str, Any]) -> dict[str, Any]:
        return _call(registry_tools.update_candidate_status_tool, state_root=state_root, **args)

    return update_candidate_status


def _register_paper_tool(state_root: str):
    @tool(
        "register_paper",
        "Register a paper in the literature registry. CSV fields are comma-separated lists.",
        _schema(
            {
                "title": {"type": "string"},
                "authors_csv": {"type": "string", "default": ""},
                "year": {"type": "integer", "default": 0},
                "venue": {"type": "string", "default": ""},
                "doi": {"type": "string", "default": ""},
                "url": {"type": "string", "default": ""},
                "abstract": {"type": "string", "default": ""},
                "topics_csv": {"type": "string", "default": ""},
                "modalities_csv": {"type": "string", "default": ""},
                "aging_relevance": {"type": "string", "default": ""},
                "disease_relevance": {"type": "string", "default": ""},
                "evidence_level": {"type": "string", "default": ""},
                "source": {"type": "string", "default": ""},
                "tags_csv": {"type": "string", "default": ""},
                "notes": {"type": "string", "default": ""},
            },
            required=["title"],
        ),
    )
    async def register_paper(args: dict[str, Any]) -> dict[str, Any]:
        return _call(registry_tools.register_paper_tool, state_root=state_root, **args)

    return register_paper


def _register_claim_tool(state_root: str):
    @tool(
        "register_claim",
        "Register an extracted claim from a paper, result, dataset, or method note.",
        _schema(
            {
                "statement": {"type": "string"},
                "paper_id": {"type": "string", "default": ""},
                "direction": {"type": "string", "default": ""},
                "population": {"type": "string", "default": ""},
                "modality": {"type": "string", "default": ""},
                "outcome": {"type": "string", "default": ""},
                "mechanism": {"type": "string", "default": ""},
                "methods_csv": {"type": "string", "default": ""},
                "caveats_csv": {"type": "string", "default": ""},
                "supports_hypotheses_csv": {"type": "string", "default": ""},
                "contradicts_hypotheses_csv": {"type": "string", "default": ""},
                "tags_csv": {"type": "string", "default": ""},
            },
            required=["statement"],
        ),
    )
    async def register_claim(args: dict[str, Any]) -> dict[str, Any]:
        return _call(registry_tools.register_claim_tool, state_root=state_root, **args)

    return register_claim


def _register_method_tool(state_root: str):
    @tool(
        "register_method",
        "Register a computational tool, method, or model that agents may use.",
        _schema(
            {
                "name": {"type": "string"},
                "purpose": {"type": "string"},
                "version": {"type": "string", "default": ""},
                "source_url": {"type": "string", "default": ""},
                "task_types_csv": {"type": "string", "default": ""},
                "modalities_csv": {"type": "string", "default": ""},
                "inputs_csv": {"type": "string", "default": ""},
                "outputs_csv": {"type": "string", "default": ""},
                "install_notes": {"type": "string", "default": ""},
                "validation_notes": {"type": "string", "default": ""},
                "limitations_csv": {"type": "string", "default": ""},
                "license": {"type": "string", "default": ""},
                "tags_csv": {"type": "string", "default": ""},
            },
            required=["name", "purpose"],
        ),
    )
    async def register_method(args: dict[str, Any]) -> dict[str, Any]:
        return _call(registry_tools.register_method_tool, state_root=state_root, **args)

    return register_method


def _register_dataset_tool(state_root: str):
    @tool(
        "register_dataset",
        "Register a relevant internal or external dataset.",
        _schema(
            {
                "name": {"type": "string"},
                "source_url": {"type": "string", "default": ""},
                "population": {"type": "string", "default": ""},
                "modalities_csv": {"type": "string", "default": ""},
                "outcomes_csv": {"type": "string", "default": ""},
                "access_status": {"type": "string", "default": ""},
                "sample_size": {"type": "integer", "default": 0},
                "age_range": {"type": "string", "default": ""},
                "disease_groups_csv": {"type": "string", "default": ""},
                "time_resolution": {"type": "string", "default": ""},
                "strengths_csv": {"type": "string", "default": ""},
                "limitations_csv": {"type": "string", "default": ""},
                "leakage_risks_csv": {"type": "string", "default": ""},
                "external_validation_uses_csv": {"type": "string", "default": ""},
                "tags_csv": {"type": "string", "default": ""},
                "notes": {"type": "string", "default": ""},
            },
            required=["name"],
        ),
    )
    async def register_dataset(args: dict[str, Any]) -> dict[str, Any]:
        return _call(registry_tools.register_dataset_tool, state_root=state_root, **args)

    return register_dataset


def _register_surprise_tool(state_root: str):
    @tool(
        "register_surprise",
        "Register an unexpected finding that may seed follow-up hypotheses.",
        _schema(
            {
                "summary": {"type": "string"},
                "origin_artifact": {"type": "string", "default": ""},
                "details": {"type": "string", "default": ""},
                "modality": {"type": "string", "default": ""},
                "signal": {"type": "string", "default": ""},
                "candidate_ids_csv": {"type": "string", "default": ""},
                "hypothesis_ids_csv": {"type": "string", "default": ""},
                "severity": {"type": "string", "default": "medium"},
                "p_hacking_risk": {"type": "string", "default": ""},
                "follow_up_needed_csv": {"type": "string", "default": ""},
                "tags_csv": {"type": "string", "default": ""},
            },
            required=["summary"],
        ),
    )
    async def register_surprise(args: dict[str, Any]) -> dict[str, Any]:
        return _call(registry_tools.register_surprise_tool, state_root=state_root, **args)

    return register_surprise


def _add_edge_tool(state_root: str):
    @tool(
        "add_edge",
        "Add a graph edge between candidates, hypotheses, papers, runs, or verifications.",
        _schema(
            {
                "source_id": {"type": "string"},
                "target_id": {"type": "string"},
                "edge_type": {"type": "string"},
                "rationale": {"type": "string", "default": ""},
                "evidence_ids_csv": {"type": "string", "default": ""},
                "confidence": {"type": "number", "default": 0.5},
                "created_by": {"type": "string", "default": "claude_agent"},
            },
            required=["source_id", "target_id", "edge_type"],
        ),
    )
    async def add_edge(args: dict[str, Any]) -> dict[str, Any]:
        return _call(registry_tools.add_edge_tool, state_root=state_root, **args)

    return add_edge


def _register_method_plan_tool(state_root: str):
    @tool(
        "register_method_plan",
        "Register a method plan before any execution is launched.",
        _schema(
            {
                "target_id": {"type": "string"},
                "objective": {"type": "string"},
                "target_type": {"type": "string", "default": "candidate"},
                "inputs_csv": {"type": "string", "default": ""},
                "outputs_csv": {"type": "string", "default": ""},
                "split_id": {"type": "string", "default": ""},
                "adjustment_set_csv": {"type": "string", "default": ""},
                "negative_controls_csv": {"type": "string", "default": ""},
                "leakage_checks_csv": {"type": "string", "default": ""},
                "statistical_tests_csv": {"type": "string", "default": ""},
                "execution_steps_csv": {"type": "string", "default": ""},
                "script_path": {"type": "string", "default": ""},
                "command_template": {"type": "string", "default": ""},
                "status": {"type": "string", "default": "draft"},
                "created_by": {"type": "string", "default": "claude_agent"},
                "notes": {"type": "string", "default": ""},
            },
            required=["target_id", "objective"],
        ),
    )
    async def register_method_plan(args: dict[str, Any]) -> dict[str, Any]:
        return _call(registry_tools.register_method_plan_tool, state_root=state_root, **args)

    return register_method_plan


def _register_run_tool(state_root: str):
    @tool(
        "register_run",
        "Register a planned, submitted, running, completed, or failed execution run.",
        _schema(
            {
                "hypothesis_id": {"type": "string", "default": ""},
                "candidate_id": {"type": "string", "default": ""},
                "split_id": {"type": "string", "default": ""},
                "script_path": {"type": "string", "default": ""},
                "command": {"type": "string", "default": ""},
                "artifacts_csv": {"type": "string", "default": ""},
                "metrics_json": {"type": "string", "default": "{}"},
                "mechanical_checks_json": {"type": "string", "default": "{}"},
                "status": {"type": "string", "default": "planned"},
                "notes": {"type": "string", "default": ""},
            },
        ),
    )
    async def register_run(args: dict[str, Any]) -> dict[str, Any]:
        return _call(registry_tools.register_run_tool, state_root=state_root, **args)

    return register_run


def _register_verification_tool(state_root: str):
    @tool(
        "register_verification",
        "Register a mechanical verification or critic outcome.",
        _schema(
            {
                "target_id": {"type": "string"},
                "target_type": {"type": "string"},
                "verdict": {"type": "string", "default": "not_checked"},
                "checks_json": {"type": "string", "default": "{}"},
                "blockers_csv": {"type": "string", "default": ""},
                "recommendations_csv": {"type": "string", "default": ""},
                "reviewer": {"type": "string", "default": "claude_agent"},
            },
            required=["target_id", "target_type"],
        ),
    )
    async def register_verification(args: dict[str, Any]) -> dict[str, Any]:
        return _call(registry_tools.register_verification_tool, state_root=state_root, **args)

    return register_verification


def _list_execution_specs_tool(state_root: str):
    @tool(
        "list_execution_specs",
        "List approved execution specs that may be submitted to Slurm. Read-only.",
        {},
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    async def list_execution_specs(args: dict[str, Any]) -> dict[str, Any]:
        return _ok(registry_tools.list_execution_specs_tool(state_root=state_root))

    return list_execution_specs


def _propose_execution_tool(state_root: str):
    @tool(
        "propose_execution",
        "Write a quarantined Python analysis script plus execution-spec JSON for a method plan. Does not approve or submit.",
        _schema(
            {
                "candidate_id": {"type": "string"},
                "plan_id": {"type": "string"},
                "title": {"type": "string"},
                "script_text": {"type": "string"},
                "spec_json": {"type": "string"},
                "notes": {"type": "string", "default": ""},
            },
            required=["candidate_id", "plan_id", "title", "script_text", "spec_json"],
        ),
    )
    async def propose_execution(args: dict[str, Any]) -> dict[str, Any]:
        return _call(registry_tools.propose_execution_tool, state_root=state_root, **args)

    return propose_execution


def _list_execution_proposals_tool(state_root: str):
    @tool(
        "list_execution_proposals",
        "List quarantined execution proposals and their validation/promotion status.",
        {},
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    async def list_execution_proposals(args: dict[str, Any]) -> dict[str, Any]:
        return _ok(registry_tools.list_execution_proposals_tool(state_root=state_root))

    return list_execution_proposals


def _retrieve_execution_proposal_tool(state_root: str):
    @tool(
        "retrieve_execution_proposal",
        "Retrieve proposal context for scientific/feasibility/mechanical review, including candidate, method plan, spec, script preview, and review gate.",
        _schema(
            {
                "proposal_id": {"type": "string"},
                "include_script": {"type": "boolean", "default": False},
            },
            required=["proposal_id"],
        ),
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    async def retrieve_execution_proposal(args: dict[str, Any]) -> dict[str, Any]:
        return _call(registry_tools.retrieve_execution_proposal_tool, state_root=state_root, **args)

    return retrieve_execution_proposal


def _validate_execution_proposal_tool(state_root: str):
    @tool(
        "validate_execution_proposal",
        "Statically validate a quarantined execution proposal before promotion.",
        _schema({"proposal_id": {"type": "string"}}, required=["proposal_id"]),
    )
    async def validate_execution_proposal(args: dict[str, Any]) -> dict[str, Any]:
        return _call(registry_tools.validate_execution_proposal_tool, state_root=state_root, **args)

    return validate_execution_proposal


def _fixed_reviewer_execution_proposal_tool(
    state_root: str,
    tool_name: str,
    reviewer: str,
    description: str,
):
    @tool(
        tool_name,
        description,
        _schema(
            {
                "proposal_id": {"type": "string"},
                "verdict": {"type": "string", "default": "not_checked"},
                "checks_json": {"type": "string", "default": "{}"},
                "blockers_csv": {"type": "string", "default": ""},
                "recommendations_csv": {"type": "string", "default": ""},
            },
            required=["proposal_id", "verdict"],
        ),
    )
    async def review_execution_proposal(args: dict[str, Any]) -> dict[str, Any]:
        return _call(
            registry_tools.review_execution_proposal_tool,
            state_root=state_root,
            proposal_id=args["proposal_id"],
            reviewer=reviewer,
            verdict=args["verdict"],
            checks_json=args.get("checks_json", "{}"),
            blockers_csv=args.get("blockers_csv", ""),
            recommendations_csv=args.get("recommendations_csv", ""),
        )

    return review_execution_proposal


def _promote_execution_proposal_tool(state_root: str):
    @tool(
        "promote_execution_proposal",
        "Promote a validated and reviewer-approved execution proposal into approved analysis/generated and execution_specs files. Requires confirm=true.",
        _schema(
            {
                "proposal_id": {"type": "string"},
                "confirm": {"type": "boolean", "default": False},
            },
            required=["proposal_id"],
        ),
    )
    async def promote_execution_proposal(args: dict[str, Any]) -> dict[str, Any]:
        return _call(registry_tools.promote_execution_proposal_tool, state_root=state_root, **args)

    return promote_execution_proposal


def _dry_run_execution_spec_tool(state_root: str):
    @tool(
        "dry_run_execution_spec",
        "Validate and render a guarded Slurm execution spec without submitting.",
        _schema(
            {
                "spec_id": {"type": "string"},
                "params_json": {"type": "string", "default": "{}"}
            },
            required=["spec_id"],
        ),
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    async def dry_run_execution_spec(args: dict[str, Any]) -> dict[str, Any]:
        return _call(registry_tools.dry_run_execution_spec_tool, state_root=state_root, **args)

    return dry_run_execution_spec


def _submit_execution_spec_tool(state_root: str):
    @tool(
        "submit_execution_spec",
        "Submit an approved execution spec to Slurm. Requires confirm=true and prior dry-run review.",
        _schema(
            {
                "spec_id": {"type": "string"},
                "params_json": {"type": "string", "default": "{}"},
                "confirm": {"type": "boolean", "default": False}
            },
            required=["spec_id"],
        ),
    )
    async def submit_execution_spec(args: dict[str, Any]) -> dict[str, Any]:
        return _call(registry_tools.submit_execution_spec_tool, state_root=state_root, **args)

    return submit_execution_spec


def _check_slurm_status_tool(state_root: str):
    @tool(
        "check_slurm_status",
        "Check Slurm status for a registered run ID or job ID.",
        _schema(
            {
                "run_id": {"type": "string", "default": ""},
                "job_id": {"type": "string", "default": ""}
            },
        ),
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    async def check_slurm_status(args: dict[str, Any]) -> dict[str, Any]:
        return _call(registry_tools.check_slurm_status_tool, state_root=state_root, **args)

    return check_slurm_status


def _ingest_execution_run_tool(state_root: str):
    @tool(
        "ingest_execution_run",
        "Validate expected artifacts and register run ingestion verification.",
        _schema({"run_id": {"type": "string"}}, required=["run_id"]),
    )
    async def ingest_execution_run(args: dict[str, Any]) -> dict[str, Any]:
        return _call(registry_tools.ingest_execution_run_tool, state_root=state_root, **args)

    return ingest_execution_run


def _schema(properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": required or [],
        "additionalProperties": False,
    }


def _call(func: Callable[..., str], **kwargs: Any) -> dict[str, Any]:
    try:
        return _ok(func(**kwargs))
    except Exception as exc:
        return {"content": [{"type": "text", "text": f"{type(exc).__name__}: {exc}"}], "is_error": True}


def _ok(payload: str) -> dict[str, Any]:
    try:
        structured = json.loads(payload)
    except json.JSONDecodeError:
        structured = {"result": payload}
    return {
        "content": [{"type": "text", "text": payload}],
        "structuredContent": structured,
    }
