"""Quarantined method-plan to execution-spec compiler.

The live agent is allowed to propose analysis code through this narrow layer
instead of receiving broad filesystem write access. Proposed scripts/specs live
under ignored state, are statically validated, and only proposals approved by
the required scientific, feasibility/leakage, and mechanical reviewers can be
promoted into approved analysis/spec directories used by the guarded Slurm
runner.
"""

from __future__ import annotations

import argparse
import ast
import json
import py_compile
import re
import shutil
from pathlib import Path
from typing import Any

from .retrieval import build_index
from .schemas import VerificationRecord, now_utc, record_to_dict
from .slurm_execution import REPO_ROOT, SAFE_ID, SAFE_TOKEN, SPEC_ROOT, SlurmResources
from .store import AgenticDiscoveryStore


PROPOSAL_PREFIX = "EXECPROP"
GENERATED_ANALYSIS_ROOT = REPO_ROOT / "agentic_discovery" / "analysis" / "generated"
MAX_SCRIPT_CHARS = 120_000
REQUIRED_PROMOTION_REVIEWERS = (
    "scientific-critic",
    "feasibility-leakage",
    "mechanical-verifier",
)
ALLOWED_IMPORT_ROOTS = {
    "__future__",
    "argparse",
    "collections",
    "csv",
    "dataclasses",
    "datetime",
	"functools",
	"hashlib",
	"itertools",
    "json",
    "math",
    "numpy",
    "pandas",
    "pathlib",
    "scipy",
    "statistics",
    "statsmodels",
    "typing",
    "warnings",
}
DENIED_CALL_NAMES = {"eval", "exec", "compile", "__import__", "input", "breakpoint"}
DENIED_ATTRIBUTE_CALLS = {
    ("os", "system"),
    ("os", "popen"),
    ("subprocess", "run"),
    ("subprocess", "Popen"),
    ("subprocess", "call"),
    ("subprocess", "check_call"),
    ("subprocess", "check_output"),
    ("shutil", "rmtree"),
}
DENIED_METHOD_NAMES = {"unlink", "rmdir"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-root", default=None, help="Override registry state directory.")
    sub = parser.add_subparsers(dest="command", required=True)

    list_cmd = sub.add_parser("list", help="List execution proposals.")
    list_cmd.add_argument("--json", action="store_true")

    show = sub.add_parser("show", help="Show one execution proposal manifest.")
    show.add_argument("proposal_id")

    context = sub.add_parser("context", help="Show proposal context for critic/reviewer agents.")
    context.add_argument("proposal_id")
    context.add_argument("--include-script", action="store_true")
    context.add_argument("--json", action="store_true")

    propose = sub.add_parser("propose", help="Create a quarantined script/spec proposal.")
    propose.add_argument("--candidate-id", required=True)
    propose.add_argument("--plan-id", required=True)
    propose.add_argument("--title", required=True)
    propose.add_argument("--script-file", type=Path, required=True)
    propose.add_argument("--spec-json-file", type=Path, required=True)
    propose.add_argument("--notes", default="")
    propose.add_argument("--json", action="store_true")

    validate = sub.add_parser("validate", help="Validate a quarantined proposal.")
    validate.add_argument("proposal_id")
    validate.add_argument("--json", action="store_true")

    review = sub.add_parser("review", help="Register a reviewer gate verdict for a proposal.")
    review.add_argument("proposal_id")
    review.add_argument("--reviewer", required=True, choices=REQUIRED_PROMOTION_REVIEWERS)
    review.add_argument("--verdict", required=True, choices=["pass", "concern", "fail", "inconclusive", "not_checked"])
    review.add_argument("--checks-json", default="{}")
    review.add_argument("--blocker", action="append", default=[], dest="blockers")
    review.add_argument("--recommendation", action="append", default=[], dest="recommendations")
    review.add_argument("--json", action="store_true")

    promote = sub.add_parser("promote", help="Promote a validated proposal to approved script/spec.")
    promote.add_argument("proposal_id")
    promote.add_argument("--yes", action="store_true", help="Required to write approved files.")
    promote.add_argument("--json", action="store_true")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    store = AgenticDiscoveryStore(args.state_root)

    if args.command == "list":
        payload = list_execution_proposals(store)
        return _print(payload, json_output=args.json)

    if args.command == "show":
        print(json.dumps(load_manifest(store, args.proposal_id), indent=2, sort_keys=True))
        return 0

    if args.command == "context":
        payload = retrieve_execution_proposal_context(store, args.proposal_id, include_script=args.include_script)
        return _print(payload, json_output=args.json)

    if args.command == "propose":
        payload = propose_execution(
            store=store,
            candidate_id=args.candidate_id,
            plan_id=args.plan_id,
            title=args.title,
            script_text=args.script_file.read_text(encoding="utf-8"),
            spec_data=json.loads(args.spec_json_file.read_text(encoding="utf-8")),
            notes=args.notes,
            proposed_by="cli",
        )
        return _print(payload, json_output=args.json)

    if args.command == "validate":
        payload = validate_execution_proposal(store, args.proposal_id)
        return _print(payload, json_output=args.json)

    if args.command == "review":
        payload = review_execution_proposal(
            store,
            proposal_id=args.proposal_id,
            reviewer=args.reviewer,
            verdict=args.verdict,
            checks=json.loads(args.checks_json),
            blockers=args.blockers,
            recommendations=args.recommendations,
        )
        return _print(payload, json_output=args.json)

    if args.command == "promote":
        if not args.yes:
            raise SystemExit("Refusing to promote without --yes. Validate first.")
        payload = promote_execution_proposal(store, args.proposal_id)
        return _print(payload, json_output=args.json)

    raise AssertionError(args.command)


def propose_execution(
    store: AgenticDiscoveryStore,
    candidate_id: str,
    plan_id: str,
    title: str,
    script_text: str,
    spec_data: dict[str, Any],
    notes: str = "",
    proposed_by: str = "sdk_agent",
) -> dict[str, Any]:
    """Create a quarantined execution proposal from script text and spec JSON."""

    if not candidate_id.startswith("CAND-"):
        raise ValueError("candidate_id must start with CAND-")
    if not plan_id.startswith("PLAN-"):
        raise ValueError("plan_id must start with PLAN-")
    if not isinstance(spec_data, dict):
        raise ValueError("spec_data must be a JSON object")
    if "\x00" in script_text:
        raise ValueError("script_text contains NUL byte")
    if len(script_text) > MAX_SCRIPT_CHARS:
        raise ValueError(f"script_text exceeds {MAX_SCRIPT_CHARS} characters")

    proposal_id = next_proposal_id(store)
    proposal_dir = proposal_root(store) / proposal_id
    proposal_dir.mkdir(parents=True, exist_ok=False)
    script_filename = "analysis.py"
    spec_filename = "spec.json"
    (proposal_dir / script_filename).write_text(script_text, encoding="utf-8")
    (proposal_dir / spec_filename).write_text(json.dumps(spec_data, indent=2, sort_keys=True), encoding="utf-8")
    manifest = {
        "proposal_id": proposal_id,
        "created_at": now_utc(),
        "updated_at": now_utc(),
        "status": "proposed",
        "candidate_id": candidate_id,
        "plan_id": plan_id,
        "title": title,
        "script_filename": script_filename,
        "spec_filename": spec_filename,
        "proposed_by": proposed_by,
        "notes": notes,
        "validation": {},
        "promotion": {},
    }
    save_manifest(store, manifest)
    return {"proposal": manifest}


def validate_execution_proposal(store: AgenticDiscoveryStore, proposal_id: str) -> dict[str, Any]:
    manifest = load_manifest(store, proposal_id)
    proposal_dir = proposal_path(store, proposal_id)
    script_path = proposal_dir / manifest["script_filename"]
    spec_path = proposal_dir / manifest["spec_filename"]
    spec_data = json.loads(spec_path.read_text(encoding="utf-8"))

    checks: dict[str, Any] = {}
    blockers: list[str] = []
    checks["script_static"] = validate_script(script_path)
    blockers.extend(checks["script_static"]["blockers"])
    checks["spec_static"] = validate_spec_data(spec_data, manifest)
    blockers.extend(checks["spec_static"]["blockers"])
    checks["required_inputs"] = validate_required_inputs(spec_data)
    blockers.extend(checks["required_inputs"]["blockers"])

    verdict = "pass" if not blockers else "fail"
    validation = {
        "validated_at": now_utc(),
        "verdict": verdict,
        "checks": checks,
        "blockers": blockers,
    }
    manifest["validation"] = validation
    manifest["status"] = "validated" if verdict == "pass" else "validation_failed"
    manifest["updated_at"] = now_utc()
    save_manifest(store, manifest)
    return {"proposal": manifest}


def retrieve_execution_proposal_context(
    store: AgenticDiscoveryStore,
    proposal_id: str,
    include_script: bool = False,
) -> dict[str, Any]:
    manifest = load_manifest(store, proposal_id)
    proposal_dir = proposal_path(store, proposal_id)
    script_path = proposal_dir / manifest["script_filename"]
    spec_path = proposal_dir / manifest["spec_filename"]
    candidate = store.candidates.get(manifest["candidate_id"])
    method_plan = store.method_plans.get(manifest["plan_id"])
    spec_data = json.loads(spec_path.read_text(encoding="utf-8"))
    payload: dict[str, Any] = {
        "proposal": manifest,
        "candidate": record_to_dict(candidate) if candidate else None,
        "method_plan": record_to_dict(method_plan) if method_plan else None,
        "spec": spec_data,
        "script_path": str(script_path),
        "script_preview": script_path.read_text(encoding="utf-8")[:5000],
        "reviews": proposal_reviews(store, proposal_id),
        "review_gate": review_gate_status(store, proposal_id),
    }
    if include_script:
        payload["script_text"] = script_path.read_text(encoding="utf-8")
    return payload


def review_execution_proposal(
    store: AgenticDiscoveryStore,
    proposal_id: str,
    reviewer: str,
    verdict: str,
    checks: dict[str, Any] | None = None,
    blockers: list[str] | None = None,
    recommendations: list[str] | None = None,
) -> dict[str, Any]:
    if reviewer not in REQUIRED_PROMOTION_REVIEWERS:
        raise ValueError(f"reviewer must be one of {REQUIRED_PROMOTION_REVIEWERS}")
    load_manifest(store, proposal_id)
    record = VerificationRecord(
        target_id=proposal_id,
        target_type="execution_proposal",
        verdict=verdict,
        checks=checks or {},
        blockers=blockers or [],
        recommendations=recommendations or [],
        reviewer=reviewer,
    )
    record = store.verifications.append(record)
    build_index(store)
    return {
        "verification": record_to_dict(record),
        "review_gate": review_gate_status(store, proposal_id),
    }


def promote_execution_proposal(store: AgenticDiscoveryStore, proposal_id: str) -> dict[str, Any]:
    manifest = load_manifest(store, proposal_id)
    if manifest.get("status") != "validated":
        raise ValueError("Proposal must validate before promotion")
    gate = review_gate_status(store, proposal_id)
    if not gate["pass"]:
        raise ValueError(
            "Proposal cannot be promoted until required reviewer gates pass: "
            + json.dumps(gate, sort_keys=True)
        )

    proposal_dir = proposal_path(store, proposal_id)
    spec_data = json.loads((proposal_dir / manifest["spec_filename"]).read_text(encoding="utf-8"))
    approved_spec = approved_spec_data(spec_data, manifest)
    spec_id = approved_spec["spec_id"]
    script_rel = approved_spec["script"]
    script_dest = REPO_ROOT / script_rel
    spec_dest = SPEC_ROOT / f"{spec_id}.json"

    if script_dest.exists() or spec_dest.exists():
        raise FileExistsError(f"Refusing to overwrite approved execution artifact for spec {spec_id}")

    script_dest.parent.mkdir(parents=True, exist_ok=True)
    SPEC_ROOT.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(proposal_dir / manifest["script_filename"], script_dest)
    spec_dest.write_text(json.dumps(approved_spec, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    # Load through the guarded runner path after writing both files. This catches
    # bad promoted paths before the proposal is marked promoted.
    from .slurm_execution import load_execution_spec

    load_execution_spec(spec_id)

    plan_id = approved_spec.get("plan_id", "")
    plan_update: dict[str, Any] = {}
    if plan_id:
        plan = store.method_plans.get(plan_id)
        if plan:
            command = "python " + script_rel + " " + " ".join(approved_spec.get("args", []))
            updated_notes = (
                plan.notes
                + f"\nPromoted execution spec {spec_id} from proposal {proposal_id} at {now_utc()}."
            ).strip()
            plan = store.method_plans.update(
                plan_id,
                script_path=script_rel,
                command_template=command,
                status="ready",
                notes=updated_notes,
            )
            plan_update = {
                "plan_id": plan.plan_id,
                "status": plan.status,
                "script_path": plan.script_path,
                "command_template": plan.command_template,
            }
            build_index(store)

    manifest["status"] = "promoted"
    manifest["updated_at"] = now_utc()
    manifest["promotion"] = {
        "promoted_at": now_utc(),
        "spec_id": spec_id,
        "script_path": script_rel,
        "spec_path": str(spec_dest.relative_to(REPO_ROOT)),
        "plan_update": plan_update,
    }
    save_manifest(store, manifest)
    return {"proposal": manifest, "approved_spec": approved_spec, "review_gate": gate}


def list_execution_proposals(store: AgenticDiscoveryStore) -> dict[str, Any]:
    root = proposal_root(store)
    proposals = []
    if root.exists():
        for path in sorted(root.glob(f"{PROPOSAL_PREFIX}-*/manifest.json")):
            proposals.append(json.loads(path.read_text(encoding="utf-8")))
    return {"proposal_root": str(root), "proposals": proposals}


def proposal_reviews(store: AgenticDiscoveryStore, proposal_id: str) -> list[dict[str, Any]]:
    reviews = [
        record_to_dict(review)
        for review in store.verifications.all()
        if review.target_id == proposal_id and review.target_type == "execution_proposal"
    ]
    return sorted(reviews, key=lambda item: (item.get("created_at", ""), item.get("verification_id", "")))


def review_gate_status(store: AgenticDiscoveryStore, proposal_id: str) -> dict[str, Any]:
    manifest = load_manifest(store, proposal_id)
    validation = manifest.get("validation") or {}
    reviews = proposal_reviews(store, proposal_id)
    latest_by_reviewer: dict[str, dict[str, Any]] = {}
    for review in reviews:
        reviewer = str(review.get("reviewer", ""))
        if reviewer in REQUIRED_PROMOTION_REVIEWERS:
            latest_by_reviewer[reviewer] = review
    required = {}
    missing = []
    failing = []
    for reviewer in REQUIRED_PROMOTION_REVIEWERS:
        review = latest_by_reviewer.get(reviewer)
        if review is None:
            missing.append(reviewer)
            required[reviewer] = {"status": "missing"}
            continue
        verdict = review.get("verdict")
        required[reviewer] = {
            "status": "pass" if verdict == "pass" and not review.get("blockers") else "blocked",
            "verdict": verdict,
            "verification_id": review.get("verification_id"),
            "blockers": review.get("blockers", []),
        }
        if verdict != "pass" or review.get("blockers"):
            failing.append(reviewer)
    static_pass = validation.get("verdict") == "pass"
    return {
        "pass": bool(static_pass and not missing and not failing),
        "static_validation_pass": static_pass,
        "required_reviewers": list(REQUIRED_PROMOTION_REVIEWERS),
        "reviews": required,
        "missing_reviewers": missing,
        "failing_reviewers": failing,
    }


def validate_script(script_path: Path) -> dict[str, Any]:
    blockers: list[str] = []
    try:
        source = script_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(script_path))
    except SyntaxError as exc:
        return {"pass": False, "blockers": [f"syntax_error: {exc}"], "imports": []}

    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split(".", 1)[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module.split(".", 1)[0])
        elif isinstance(node, ast.Call):
            violation = denied_call(node)
            if violation:
                blockers.append(violation)

    denied_imports = sorted(root for root in imports if root not in ALLOWED_IMPORT_ROOTS)
    blockers.extend(f"import_not_allowed:{root}" for root in denied_imports)
    try:
        py_compile.compile(str(script_path), doraise=True)
    except py_compile.PyCompileError as exc:
        blockers.append(f"py_compile_failed:{exc.msg}")
    return {"pass": not blockers, "blockers": blockers, "imports": sorted(imports)}


def denied_call(node: ast.Call) -> str:
    func = node.func
    if isinstance(func, ast.Name) and func.id in DENIED_CALL_NAMES:
        return f"call_not_allowed:{func.id}"
    if isinstance(func, ast.Attribute):
        if func.attr in DENIED_METHOD_NAMES:
            return f"method_not_allowed:{func.attr}"
        value = func.value
        if isinstance(value, ast.Name) and (value.id, func.attr) in DENIED_ATTRIBUTE_CALLS:
            return f"call_not_allowed:{value.id}.{func.attr}"
    return ""


def validate_spec_data(spec_data: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    spec_id = str(spec_data.get("spec_id") or "")
    if not SAFE_ID.match(spec_id):
        blockers.append(f"unsafe_or_missing_spec_id:{spec_id}")
    if spec_data.get("candidate_id") != manifest["candidate_id"]:
        blockers.append("candidate_id_mismatch")
    if spec_data.get("plan_id") != manifest["plan_id"]:
        blockers.append("plan_id_mismatch")
    if "expected_outputs" not in spec_data or not isinstance(spec_data.get("expected_outputs"), list):
        blockers.append("expected_outputs_required")
    if "args" in spec_data and not isinstance(spec_data["args"], list):
        blockers.append("args_must_be_list")
    for key in ["args", "required_inputs", "expected_outputs"]:
        for value in spec_data.get(key, []):
            if not isinstance(value, str) or not safe_template_token(value):
                blockers.append(f"unsafe_{key}:{value}")
    output_dir = spec_data.get("output_dir", "results/agentic_discovery/{spec_id}/{run_id}")
    if not isinstance(output_dir, str) or not safe_template_token(output_dir):
        blockers.append(f"unsafe_output_dir:{output_dir}")
    for output in spec_data.get("expected_outputs", []):
        if not output.startswith(("results/", "agentic_discovery/state/")):
            blockers.append(f"output_not_under_approved_root:{output}")
    slurm = spec_data.get("slurm", {})
    if slurm and not isinstance(slurm, dict):
        blockers.append("slurm_must_be_object")
    else:
        try:
            SlurmResources(**slurm)
        except TypeError as exc:
            blockers.append(f"invalid_slurm:{exc}")
    return {"pass": not blockers, "blockers": blockers, "spec_id": spec_id}


def validate_required_inputs(spec_data: dict[str, Any]) -> dict[str, Any]:
    blockers = []
    inputs = []
    approved_roots = approved_required_input_roots()
    for raw in spec_data.get("required_inputs", []):
        rendered = render_validation_template(raw, spec_data)
        path = (REPO_ROOT / rendered).resolve() if not Path(rendered).is_absolute() else Path(rendered).resolve()
        inputs.append(str(path))
        if not any(is_relative_to(path, root) for root in approved_roots):
            blockers.append(f"required_input_escapes_approved_roots:{raw}")
        elif not path.exists():
            blockers.append(f"required_input_missing:{raw}")
    return {"pass": not blockers, "blockers": blockers, "inputs": inputs}


def approved_required_input_roots() -> list[Path]:
    roots = [REPO_ROOT.resolve()]
    data_root = REPO_ROOT / "data"
    if data_root.exists():
        resolved_data = data_root.resolve()
        if not any(is_relative_to(resolved_data, root) or resolved_data == root for root in roots):
            roots.append(resolved_data)
    return roots


def approved_spec_data(spec_data: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    spec_id = str(spec_data["spec_id"])
    script_rel = f"agentic_discovery/analysis/generated/{spec_id}.py"
    approved = {
        "spec_id": spec_id,
        "description": spec_data.get("description", manifest.get("title", "")),
        "script": script_rel,
        "args": list(spec_data.get("args", [])),
        "proposal_id": manifest["proposal_id"],
        "candidate_id": manifest["candidate_id"],
        "hypothesis_id": spec_data.get("hypothesis_id", ""),
        "plan_id": manifest["plan_id"],
        "split_id": spec_data.get("split_id", ""),
        "required_inputs": list(spec_data.get("required_inputs", [])),
        "expected_outputs": list(spec_data.get("expected_outputs", [])),
        "output_dir": spec_data.get("output_dir", "results/agentic_discovery/{spec_id}/{run_id}"),
        "slurm": spec_data.get("slurm", {}),
        "notes": (
            spec_data.get("notes", "")
            + f"\nPromoted from quarantined execution proposal {manifest['proposal_id']}."
        ).strip(),
    }
    return approved


def render_validation_template(value: str, spec_data: dict[str, Any]) -> str:
    context = {
        "spec_id": str(spec_data.get("spec_id", "SPEC")),
        "run_id": "RUN-VALIDATION",
        "candidate_id": str(spec_data.get("candidate_id", "")),
        "plan_id": str(spec_data.get("plan_id", "")),
        "split_id": str(spec_data.get("split_id", "")),
        "state_root": "agentic_discovery/state",
        "repo_root": str(REPO_ROOT),
    }
    try:
        return value.format(**context)
    except KeyError as exc:
        raise ValueError(f"Unknown template placeholder in {value!r}: {exc}") from exc


def safe_template_token(value: str) -> bool:
    if "\n" in value or "\x00" in value:
        return False
    check = re.sub(r"\{[A-Za-z0-9_.-]+\}", "PLACEHOLDER", value)
    return bool(SAFE_TOKEN.match(check))


def next_proposal_id(store: AgenticDiscoveryStore) -> str:
    root = proposal_root(store)
    root.mkdir(parents=True, exist_ok=True)
    date_token = now_utc()[:10].replace("-", "")
    pattern = re.compile(rf"^{PROPOSAL_PREFIX}-{date_token}-(\d+)$")
    max_seen = 0
    for path in root.glob(f"{PROPOSAL_PREFIX}-{date_token}-*"):
        match = pattern.match(path.name)
        if match:
            max_seen = max(max_seen, int(match.group(1)))
    return f"{PROPOSAL_PREFIX}-{date_token}-{max_seen + 1:04d}"


def proposal_root(store: AgenticDiscoveryStore) -> Path:
    return store.root / "execution_proposals"


def proposal_path(store: AgenticDiscoveryStore, proposal_id: str) -> Path:
    if not SAFE_ID.match(proposal_id):
        raise ValueError(f"Unsafe proposal_id: {proposal_id}")
    path = (proposal_root(store) / proposal_id).resolve()
    if not is_relative_to(path, proposal_root(store).resolve()):
        raise ValueError("Proposal path escapes proposal root")
    return path


def load_manifest(store: AgenticDiscoveryStore, proposal_id: str) -> dict[str, Any]:
    path = proposal_path(store, proposal_id) / "manifest.json"
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def save_manifest(store: AgenticDiscoveryStore, manifest: dict[str, Any]) -> None:
    path = proposal_path(store, manifest["proposal_id"]) / "manifest.json"
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _print(payload: Any, json_output: bool) -> int:
    if json_output:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
