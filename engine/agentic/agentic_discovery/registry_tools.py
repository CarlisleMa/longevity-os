"""Plain Python tools for discovery agents.

The functions here intentionally do not import any provider SDK. They can be
called directly in tests or wrapped by the Claude Agent SDK tool layer.
"""

from __future__ import annotations

import json
from typing import Any

from . import execution_proposals
from .retrieval import build_index, retrieve_context_for_candidate, retrieve_context_for_hypothesis, search
from .schemas import (
    DatasetRecord,
    ExecutionRun,
    ExtractedClaim,
    HypothesisCandidate,
    HypothesisEdge,
    MethodPlanRecord,
    PaperRecord,
    SurpriseRecord,
    ToolRecord,
    VerificationRecord,
    record_to_dict,
)
from .slurm_execution import check_status, ingest_run, list_execution_specs, prepared_summary, prepare_execution, submit_execution
from .store import AgenticDiscoveryStore


def registry_summary_tool(state_root: str = "") -> str:
    """Return registry counts and current candidate queue summary as JSON."""
    store = _store(state_root)
    candidates = sorted(store.candidates.all(), key=lambda item: (-item.priority, item.created_at))
    payload = {
        "state_root": str(store.root),
        "counts": store.counts(),
        "top_candidates": [
            {
                "candidate_id": candidate.candidate_id,
                "status": candidate.status,
                "priority": candidate.priority,
                "title": candidate.title,
                "needs": candidate.needs,
            }
            for candidate in candidates[:10]
        ],
    }
    return _json(payload)


def search_registry_tool(query: str, kinds_csv: str = "", limit: int = 8, state_root: str = "") -> str:
    """Search candidates, knowledge records, evidence, and legacy hypotheses."""
    store = _store(state_root)
    kinds = _csv(kinds_csv)
    hits = search(query, store=store, kinds=kinds or None, limit=limit)
    return _json(_strip_payloads(hits))


def retrieve_context_tool(target_id: str, target_type: str = "candidate", limit: int = 10, state_root: str = "") -> str:
    """Retrieve prior project context for a candidate or legacy hypothesis."""
    store = _store(state_root)
    if target_type == "candidate" or target_id.startswith("CAND-"):
        context = retrieve_context_for_candidate(target_id, store=store, limit=limit)
    else:
        context = retrieve_context_for_hypothesis(target_id, store=store, limit=limit)
    context["hits"] = _strip_payloads(context["hits"])
    return _json(context)


def deposit_candidate_tool(
    title: str,
    claim: str,
    mechanism: str = "",
    expected_direction: str = "",
    required_modalities_csv: str = "",
    primary_outcome: str = "",
    confounders_csv: str = "",
    negative_controls_csv: str = "",
    leakage_risks_csv: str = "",
    needs_csv: str = "",
    priority: float = 0.5,
    origin_type: str = "agent_round",
    origin_agent: str = "sdk_agent",
    origin_detail: str = "",
    trigger_artifacts_csv: str = "",
    tags_csv: str = "",
    notes: str = "",
    state_root: str = "",
) -> str:
    """Deposit a quarantined hypothesis candidate and update retrieval."""
    store = _store(state_root)
    candidate = HypothesisCandidate(
        title=title,
        claim=claim,
        mechanism=mechanism,
        expected_direction=expected_direction,
        required_modalities=_csv(required_modalities_csv),
        primary_outcome=primary_outcome,
        confounders=_csv(confounders_csv),
        negative_controls=_csv(negative_controls_csv),
        leakage_risks=_csv(leakage_risks_csv),
        needs=_csv(needs_csv),
        priority=priority,
        origin_type=origin_type,
        origin_agent=origin_agent,
        origin_detail=origin_detail,
        trigger_artifacts=_csv(trigger_artifacts_csv),
        tags=_csv(tags_csv),
        notes=notes,
    )
    candidate = store.candidates.append(candidate)
    build_index(store)
    return _json({"candidate": record_to_dict(candidate)})


def update_candidate_status_tool(
    candidate_id: str,
    status: str,
    note: str = "",
    state_root: str = "",
) -> str:
    """Update candidate lifecycle status."""
    store = _store(state_root)
    candidate = store.candidates.get(candidate_id)
    if candidate is None:
        raise KeyError(f"Candidate not found: {candidate_id}")
    notes = candidate.notes
    if note:
        notes = f"{notes}\n{note}".strip()
    updated = store.candidates.update(candidate_id, status=status, notes=notes)
    build_index(store)
    return _json({"candidate": record_to_dict(updated)})


def register_paper_tool(
    title: str,
    authors_csv: str = "",
    year: int = 0,
    venue: str = "",
    doi: str = "",
    url: str = "",
    abstract: str = "",
    topics_csv: str = "",
    modalities_csv: str = "",
    aging_relevance: str = "",
    disease_relevance: str = "",
    evidence_level: str = "",
    source: str = "",
    tags_csv: str = "",
    notes: str = "",
    state_root: str = "",
) -> str:
    """Register a paper in the literature registry."""
    store = _store(state_root)
    record = PaperRecord(
        title=title,
        authors=_csv(authors_csv),
        year=year or None,
        venue=venue,
        doi=doi,
        url=url,
        abstract=abstract,
        topics=_csv(topics_csv),
        modalities=_csv(modalities_csv),
        aging_relevance=aging_relevance,
        disease_relevance=disease_relevance,
        evidence_level=evidence_level,
        source=source,
        tags=_csv(tags_csv),
        notes=notes,
    )
    record = store.papers.append(record)
    build_index(store)
    return _json({"paper": record_to_dict(record)})


def register_claim_tool(
    statement: str,
    paper_id: str = "",
    direction: str = "",
    population: str = "",
    modality: str = "",
    outcome: str = "",
    mechanism: str = "",
    methods_csv: str = "",
    caveats_csv: str = "",
    supports_hypotheses_csv: str = "",
    contradicts_hypotheses_csv: str = "",
    tags_csv: str = "",
    state_root: str = "",
) -> str:
    """Register an extracted claim from a paper, dataset, or result artifact."""
    store = _store(state_root)
    record = ExtractedClaim(
        statement=statement,
        paper_id=paper_id,
        direction=direction,
        population=population,
        modality=modality,
        outcome=outcome,
        mechanism=mechanism,
        methods=_csv(methods_csv),
        caveats=_csv(caveats_csv),
        supports_hypotheses=_csv(supports_hypotheses_csv),
        contradicts_hypotheses=_csv(contradicts_hypotheses_csv),
        tags=_csv(tags_csv),
    )
    record = store.claims.append(record)
    build_index(store)
    return _json({"claim": record_to_dict(record)})


def register_method_tool(
    name: str,
    purpose: str,
    version: str = "",
    source_url: str = "",
    task_types_csv: str = "",
    modalities_csv: str = "",
    inputs_csv: str = "",
    outputs_csv: str = "",
    install_notes: str = "",
    validation_notes: str = "",
    limitations_csv: str = "",
    license: str = "",
    tags_csv: str = "",
    state_root: str = "",
) -> str:
    """Register a computational tool, method, or model that agents may use."""
    store = _store(state_root)
    record = ToolRecord(
        name=name,
        purpose=purpose,
        version=version,
        source_url=source_url,
        task_types=_csv(task_types_csv),
        modalities=_csv(modalities_csv),
        inputs=_csv(inputs_csv),
        outputs=_csv(outputs_csv),
        install_notes=install_notes,
        validation_notes=validation_notes,
        limitations=_csv(limitations_csv),
        license=license,
        tags=_csv(tags_csv),
    )
    record = store.tools.append(record)
    build_index(store)
    return _json({"tool": record_to_dict(record)})


def register_dataset_tool(
    name: str,
    source_url: str = "",
    population: str = "",
    modalities_csv: str = "",
    outcomes_csv: str = "",
    access_status: str = "",
    sample_size: int = 0,
    age_range: str = "",
    disease_groups_csv: str = "",
    time_resolution: str = "",
    strengths_csv: str = "",
    limitations_csv: str = "",
    leakage_risks_csv: str = "",
    external_validation_uses_csv: str = "",
    tags_csv: str = "",
    notes: str = "",
    state_root: str = "",
) -> str:
    """Register a relevant internal or external dataset."""
    store = _store(state_root)
    record = DatasetRecord(
        name=name,
        source_url=source_url,
        population=population,
        modalities=_csv(modalities_csv),
        outcomes=_csv(outcomes_csv),
        access_status=access_status,
        sample_size=sample_size or None,
        age_range=age_range,
        disease_groups=_csv(disease_groups_csv),
        time_resolution=time_resolution,
        strengths=_csv(strengths_csv),
        limitations=_csv(limitations_csv),
        leakage_risks=_csv(leakage_risks_csv),
        external_validation_uses=_csv(external_validation_uses_csv),
        tags=_csv(tags_csv),
        notes=notes,
    )
    record = store.datasets.append(record)
    build_index(store)
    return _json({"dataset": record_to_dict(record)})


def register_surprise_tool(
    summary: str,
    origin_artifact: str = "",
    details: str = "",
    modality: str = "",
    signal: str = "",
    candidate_ids_csv: str = "",
    hypothesis_ids_csv: str = "",
    severity: str = "medium",
    p_hacking_risk: str = "",
    follow_up_needed_csv: str = "",
    tags_csv: str = "",
    state_root: str = "",
) -> str:
    """Register an unexpected finding that may seed follow-up hypotheses."""
    store = _store(state_root)
    record = SurpriseRecord(
        summary=summary,
        origin_artifact=origin_artifact,
        details=details,
        modality=modality,
        signal=signal,
        candidate_ids=_csv(candidate_ids_csv),
        hypothesis_ids=_csv(hypothesis_ids_csv),
        severity=severity,
        p_hacking_risk=p_hacking_risk,
        follow_up_needed=_csv(follow_up_needed_csv),
        tags=_csv(tags_csv),
    )
    record = store.surprises.append(record)
    build_index(store)
    return _json({"surprise": record_to_dict(record)})


def add_edge_tool(
    source_id: str,
    target_id: str,
    edge_type: str,
    rationale: str = "",
    evidence_ids_csv: str = "",
    confidence: float = 0.5,
    created_by: str = "sdk_agent",
    state_root: str = "",
) -> str:
    """Add a graph edge between candidates, hypotheses, papers, runs, or verifications."""
    store = _store(state_root)
    edge = HypothesisEdge(
        source_id=source_id,
        target_id=target_id,
        edge_type=edge_type,
        rationale=rationale,
        evidence_ids=_csv(evidence_ids_csv),
        confidence=confidence,
        created_by=created_by,
    )
    edge = store.edges.append(edge)
    return _json({"edge": record_to_dict(edge)})


def register_method_plan_tool(
    target_id: str,
    objective: str,
    target_type: str = "candidate",
    inputs_csv: str = "",
    outputs_csv: str = "",
    split_id: str = "",
    adjustment_set_csv: str = "",
    negative_controls_csv: str = "",
    leakage_checks_csv: str = "",
    statistical_tests_csv: str = "",
    execution_steps_csv: str = "",
    script_path: str = "",
    command_template: str = "",
    status: str = "draft",
    created_by: str = "sdk_agent",
    notes: str = "",
    state_root: str = "",
) -> str:
    """Register a method plan before any execution is launched."""
    store = _store(state_root)
    record = MethodPlanRecord(
        target_id=target_id,
        target_type=target_type,
        objective=objective,
        inputs=_csv(inputs_csv),
        outputs=_csv(outputs_csv),
        split_id=split_id,
        adjustment_set=_csv(adjustment_set_csv),
        negative_controls=_csv(negative_controls_csv),
        leakage_checks=_csv(leakage_checks_csv),
        statistical_tests=_csv(statistical_tests_csv),
        execution_steps=_csv(execution_steps_csv),
        script_path=script_path,
        command_template=command_template,
        status=status,
        created_by=created_by,
        notes=notes,
    )
    record = store.method_plans.append(record)
    build_index(store)
    return _json({"method_plan": record_to_dict(record)})


def register_run_tool(
    hypothesis_id: str = "",
    candidate_id: str = "",
    split_id: str = "",
    script_path: str = "",
    command: str = "",
    artifacts_csv: str = "",
    metrics_json: str = "{}",
    mechanical_checks_json: str = "{}",
    status: str = "planned",
    notes: str = "",
    state_root: str = "",
) -> str:
    """Register a planned, submitted, or completed execution run."""
    store = _store(state_root)
    record = ExecutionRun(
        hypothesis_id=hypothesis_id,
        candidate_id=candidate_id,
        split_id=split_id,
        script_path=script_path,
        command=command,
        artifacts=_csv(artifacts_csv),
        metrics=_json_dict(metrics_json),
        mechanical_checks=_json_dict(mechanical_checks_json),
        status=status,
        notes=notes,
    )
    record = store.runs.append(record)
    build_index(store)
    return _json({"run": record_to_dict(record)})


def register_verification_tool(
    target_id: str,
    target_type: str,
    verdict: str = "not_checked",
    checks_json: str = "{}",
    blockers_csv: str = "",
    recommendations_csv: str = "",
    reviewer: str = "sdk_agent",
    state_root: str = "",
) -> str:
    """Register a mechanical verification or critic outcome."""
    store = _store(state_root)
    record = VerificationRecord(
        target_id=target_id,
        target_type=target_type,
        verdict=verdict,
        checks=_json_dict(checks_json),
        blockers=_csv(blockers_csv),
        recommendations=_csv(recommendations_csv),
        reviewer=reviewer,
    )
    record = store.verifications.append(record)
    build_index(store)
    return _json({"verification": record_to_dict(record)})


def list_execution_specs_tool(state_root: str = "") -> str:
    """List approved execution specs that may be submitted to Slurm."""
    specs = []
    for spec in list_execution_specs():
        specs.append(
            {
                "spec_id": spec.spec_id,
                "description": spec.description,
                "candidate_id": spec.candidate_id,
                "plan_id": spec.plan_id,
                "script": spec.script,
                "expected_outputs": spec.expected_outputs,
            }
        )
    return _json({"execution_specs": specs})


def propose_execution_tool(
    candidate_id: str,
    plan_id: str,
    title: str,
    script_text: str,
    spec_json: str,
    notes: str = "",
    state_root: str = "",
) -> str:
    """Create a quarantined execution script/spec proposal."""
    store = _store(state_root)
    payload = execution_proposals.propose_execution(
        store=store,
        candidate_id=candidate_id,
        plan_id=plan_id,
        title=title,
        script_text=script_text,
        spec_data=_json_dict(spec_json),
        notes=notes,
        proposed_by="sdk_agent",
    )
    return _json(payload)


def list_execution_proposals_tool(state_root: str = "") -> str:
    """List quarantined execution proposals."""
    store = _store(state_root)
    return _json(execution_proposals.list_execution_proposals(store))


def retrieve_execution_proposal_tool(
    proposal_id: str,
    include_script: bool = False,
    state_root: str = "",
) -> str:
    """Return proposal, candidate, plan, spec, validation, and reviews for reviewer agents."""
    store = _store(state_root)
    payload = execution_proposals.retrieve_execution_proposal_context(
        store,
        proposal_id=proposal_id,
        include_script=include_script,
    )
    return _json(payload)


def validate_execution_proposal_tool(proposal_id: str, state_root: str = "") -> str:
    """Validate a quarantined execution proposal."""
    store = _store(state_root)
    return _json(execution_proposals.validate_execution_proposal(store, proposal_id))


def review_execution_proposal_tool(
    proposal_id: str,
    reviewer: str,
    verdict: str,
    checks_json: str = "{}",
    blockers_csv: str = "",
    recommendations_csv: str = "",
    state_root: str = "",
) -> str:
    """Register a mandatory reviewer gate verdict for an execution proposal."""
    store = _store(state_root)
    return _json(
        execution_proposals.review_execution_proposal(
            store,
            proposal_id=proposal_id,
            reviewer=reviewer,
            verdict=verdict,
            checks=_json_dict(checks_json),
            blockers=_csv(blockers_csv),
            recommendations=_csv(recommendations_csv),
        )
    )


def promote_execution_proposal_tool(
    proposal_id: str,
    confirm: bool = False,
    state_root: str = "",
) -> str:
    """Promote a validated proposal into approved analysis/spec files."""
    if not confirm:
        raise PermissionError("promote_execution_proposal requires confirm=true after validation.")
    store = _store(state_root)
    return _json(execution_proposals.promote_execution_proposal(store, proposal_id))


def dry_run_execution_spec_tool(spec_id: str, params_json: str = "{}", state_root: str = "") -> str:
    """Validate and render an execution spec without submitting it."""
    store = _store(state_root)
    prepared = prepare_execution(spec_id, store=store, params=_json_dict(params_json))
    return _json({"prepared": prepared_summary(prepared), "slurm_script_text": prepared.slurm_text})


def submit_execution_spec_tool(
    spec_id: str,
    params_json: str = "{}",
    confirm: bool = False,
    state_root: str = "",
) -> str:
    """Submit an approved execution spec to Slurm only when confirm=true."""
    if not confirm:
        raise PermissionError("submit_execution_spec requires confirm=true after dry_run_execution_spec.")
    store = _store(state_root)
    payload = submit_execution(spec_id, store=store, params=_json_dict(params_json))
    return _json(payload)


def check_slurm_status_tool(run_id: str = "", job_id: str = "", state_root: str = "") -> str:
    """Check Slurm status for a run/job and update run status when possible."""
    store = _store(state_root)
    return _json(check_status(store=store, run_id=run_id, job_id=job_id))


def ingest_execution_run_tool(run_id: str, state_root: str = "") -> str:
    """Validate expected artifacts and register run ingestion verification."""
    store = _store(state_root)
    return _json(ingest_run(run_id, store=store))


def _store(state_root: str) -> AgenticDiscoveryStore:
    return AgenticDiscoveryStore(state_root or None)


def _csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _json_dict(value: str) -> dict[str, Any]:
    if not value.strip():
        return {}
    data = json.loads(value)
    if not isinstance(data, dict):
        raise ValueError("Expected a JSON object")
    return data


def _json(payload: Any) -> str:
    return json.dumps(payload, indent=2, sort_keys=True)


def _strip_payloads(hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    stripped = []
    for hit in hits:
        stripped.append(
            {
                "doc_id": hit.get("doc_id"),
                "kind": hit.get("kind"),
                "title": hit.get("title"),
                "source_path": hit.get("source_path"),
                "score": hit.get("score"),
                "snippet": hit.get("snippet"),
            }
        )
    return stripped
