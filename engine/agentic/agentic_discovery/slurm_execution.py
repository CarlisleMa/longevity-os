"""Guarded Slurm execution layer for agentic discovery.

This module intentionally does not expose raw shell execution. Analyses must be
declared in JSON execution specs, paths must resolve under approved directories,
and submission defaults to dry-run. Actual ``sbatch`` uses ``subprocess`` with a
list of arguments, never ``shell=True``.
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .retrieval import build_index
from .schemas import ExecutionRun, VerificationRecord, now_utc, record_to_dict
from .store import AgenticDiscoveryStore


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC_ROOT = Path(__file__).resolve().parent / "execution_specs"
RUN_ROOT = REPO_ROOT / "agentic_discovery" / "state" / "slurm_runs"
APPROVED_SCRIPT_ROOTS = [
    REPO_ROOT / "scripts",
    REPO_ROOT / "agentic_discovery" / "analysis",
    REPO_ROOT / "agentic_discovery" / "scripts",
]
APPROVED_OUTPUT_ROOTS = [
    REPO_ROOT / "results",
    REPO_ROOT / "agentic_discovery" / "state",
]
APPROVED_READ_ROOTS = [
    REPO_ROOT,
]
if (REPO_ROOT / "data").exists():
    APPROVED_READ_ROOTS.append((REPO_ROOT / "data").resolve())
SAFE_TOKEN = re.compile(r"^[A-Za-z0-9_.:@%+=,/-]+$")
SAFE_ID = re.compile(r"^[A-Za-z0-9_.-]+$")
JOB_ID_RE = re.compile(r"Submitted batch job\s+(\d+)")


@dataclass
class SlurmResources:
    job_name: str = "agentic-discovery"
    partition: str = "batch"
    account: str = "twc"
    time: str = "00:30:00"
    cpus_per_task: int = 1
    mem: str = "4G"
    gres: str = ""
    constraint: str = ""
    extra_directives: list[str] = field(default_factory=list)


@dataclass
class ExecutionSpec:
    spec_id: str
    description: str
    script: str
    args: list[str] = field(default_factory=list)
    interpreter: str = ""
    proposal_id: str = ""
    candidate_id: str = ""
    hypothesis_id: str = ""
    plan_id: str = ""
    split_id: str = ""
    required_inputs: list[str] = field(default_factory=list)
    expected_outputs: list[str] = field(default_factory=list)
    output_dir: str = "results/agentic_discovery/{spec_id}/{run_id}"
    slurm: SlurmResources = field(default_factory=SlurmResources)
    notes: str = ""


@dataclass
class PreparedExecution:
    spec: ExecutionSpec
    run_id_hint: str
    run_dir: Path
    output_dir: Path
    slurm_script: Path
    stdout_path: Path
    stderr_path: Path
    command: list[str]
    expected_outputs: list[Path]
    required_inputs: list[Path]
    slurm_text: str
    review_gate: dict[str, Any] = field(default_factory=dict)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-root", default=None, help="Override registry state directory.")
    sub = parser.add_subparsers(dest="command", required=True)

    list_specs = sub.add_parser("list-specs", help="List approved execution specs.")
    list_specs.add_argument("--json", action="store_true")

    show = sub.add_parser("show-spec", help="Show one execution spec.")
    show.add_argument("spec_id")

    dry_run = sub.add_parser("dry-run", help="Render and validate a Slurm script without submitting.")
    dry_run.add_argument("spec_id")
    dry_run.add_argument("--param", action="append", default=[], dest="params", help="key=value template parameter.")
    dry_run.add_argument("--json", action="store_true")

    submit = sub.add_parser("submit", help="Submit an approved spec with sbatch.")
    submit.add_argument("spec_id")
    submit.add_argument("--param", action="append", default=[], dest="params", help="key=value template parameter.")
    submit.add_argument("--yes", action="store_true", help="Required for actual sbatch submission.")
    submit.add_argument("--json", action="store_true")

    status = sub.add_parser("status", help="Check run/job status.")
    status.add_argument("--run-id", default="")
    status.add_argument("--job-id", default="")
    status.add_argument("--json", action="store_true")

    ingest = sub.add_parser("ingest", help="Validate expected artifacts and update run/verification records.")
    ingest.add_argument("run_id")
    ingest.add_argument("--json", action="store_true")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    store = AgenticDiscoveryStore(args.state_root)

    if args.command == "list-specs":
        specs = [spec_summary(spec) for spec in list_execution_specs()]
        return _print(specs, args.json)

    if args.command == "show-spec":
        spec = load_execution_spec(args.spec_id)
        print(json.dumps(spec_to_dict(spec), indent=2, sort_keys=True))
        return 0

    if args.command == "dry-run":
        prepared = prepare_execution(args.spec_id, store=store, params=parse_params(args.params))
        payload = prepared_summary(prepared)
        payload["slurm_script_text"] = prepared.slurm_text
        return _print(payload, args.json)

    if args.command == "submit":
        if not args.yes:
            raise SystemExit("Refusing to submit without --yes. Use dry-run first.")
        payload = submit_execution(args.spec_id, store=store, params=parse_params(args.params))
        return _print(payload, args.json)

    if args.command == "status":
        payload = check_status(store=store, run_id=args.run_id, job_id=args.job_id)
        return _print(payload, args.json)

    if args.command == "ingest":
        payload = ingest_run(args.run_id, store=store)
        return _print(payload, args.json)

    raise AssertionError(args.command)


def list_execution_specs() -> list[ExecutionSpec]:
    SPEC_ROOT.mkdir(parents=True, exist_ok=True)
    specs = []
    for path in sorted(SPEC_ROOT.glob("*.json")):
        specs.append(load_execution_spec(path.stem))
    return specs


def load_execution_spec(spec_id: str) -> ExecutionSpec:
    if not SAFE_ID.match(spec_id):
        raise ValueError(f"Unsafe spec_id: {spec_id}")
    path = (SPEC_ROOT / f"{spec_id}.json").resolve()
    if not _is_relative_to(path, SPEC_ROOT.resolve()):
        raise ValueError("Spec path escapes execution spec root")
    data = json.loads(path.read_text())
    slurm = SlurmResources(**data.get("slurm", {}))
    spec = ExecutionSpec(
        spec_id=data["spec_id"],
        description=data.get("description", ""),
        script=data["script"],
        args=list(data.get("args", [])),
        interpreter=data.get("interpreter", ""),
        proposal_id=data.get("proposal_id", ""),
        candidate_id=data.get("candidate_id", ""),
        hypothesis_id=data.get("hypothesis_id", ""),
        plan_id=data.get("plan_id", ""),
        split_id=data.get("split_id", ""),
        required_inputs=list(data.get("required_inputs", [])),
        expected_outputs=list(data.get("expected_outputs", [])),
        output_dir=data.get("output_dir", "results/agentic_discovery/{spec_id}/{run_id}"),
        slurm=slurm,
        notes=data.get("notes", ""),
    )
    validate_spec(spec)
    return spec


def validate_spec(spec: ExecutionSpec) -> None:
    if spec.spec_id and not SAFE_ID.match(spec.spec_id):
        raise ValueError(f"Unsafe spec_id: {spec.spec_id}")
    _validate_safe_list("args", spec.args, allow_placeholders=True)
    _validate_safe_list("required_inputs", spec.required_inputs, allow_placeholders=True)
    _validate_safe_list("expected_outputs", spec.expected_outputs, allow_placeholders=True)
    _validate_safe_list("extra_directives", spec.slurm.extra_directives, allow_placeholders=False)
    if spec.interpreter:
        _validate_token("interpreter", spec.interpreter, allow_placeholders=False)
    for value_name, value in [
        ("job_name", spec.slurm.job_name),
        ("partition", spec.slurm.partition),
        ("account", spec.slurm.account),
        ("time", spec.slurm.time),
        ("mem", spec.slurm.mem),
        ("gres", spec.slurm.gres),
        ("constraint", spec.slurm.constraint),
    ]:
        if value:
            _validate_token(value_name, value, allow_placeholders=False)
    script_path = _resolve_repo_path(spec.script)
    if not any(_is_relative_to(script_path, root.resolve()) for root in APPROVED_SCRIPT_ROOTS):
        raise ValueError(f"Script is outside approved roots: {script_path}")


def prepare_execution(
    spec_id: str,
    store: AgenticDiscoveryStore,
    params: dict[str, str] | None = None,
) -> PreparedExecution:
    spec = load_execution_spec(spec_id)
    params = params or {}
    for key, value in params.items():
        if not SAFE_ID.match(key):
            raise ValueError(f"Unsafe param key: {key}")
        _validate_token(f"param[{key}]", value, allow_placeholders=False)
    run_id_hint = store.runs.next_id()
    base_context = {
        "repo_root": str(REPO_ROOT),
        "state_root": str(store.root),
        "spec_id": spec.spec_id,
        "run_id": run_id_hint,
        "candidate_id": spec.candidate_id,
        "hypothesis_id": spec.hypothesis_id,
        "plan_id": spec.plan_id,
        "split_id": spec.split_id,
    }
    context = {**base_context, **params}
    output_dir = _resolve_approved_output(_format(spec.output_dir, context))
    run_dir = (RUN_ROOT / run_id_hint).resolve()
    if not _is_relative_to(run_dir, RUN_ROOT.resolve()):
        raise ValueError("Run directory escapes run root")
    run_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    script_path = _resolve_repo_path(_format(spec.script, context))
    interpreter = _format(spec.interpreter, context) if spec.interpreter else str(Path(__import__("sys").executable))
    command = [interpreter, str(script_path)] + [_format(arg, context) for arg in spec.args]
    for token in command:
        _validate_command_token(token)
    required_inputs = [_resolve_repo_path(_format(item, context)) for item in spec.required_inputs]
    expected_outputs = [_resolve_approved_output(_format(item, context)) for item in spec.expected_outputs]
    missing = [str(path) for path in required_inputs if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing required inputs: {missing}")

    stdout_path = run_dir / "slurm.out"
    stderr_path = run_dir / "slurm.err"
    slurm_script = run_dir / "job.slurm"
    slurm_text = _render_slurm(spec, command, stdout_path, stderr_path)
    slurm_script.write_text(slurm_text, encoding="utf-8")
    review_gate = review_gate_for_spec(spec, store)
    return PreparedExecution(
        spec=spec,
        run_id_hint=run_id_hint,
        run_dir=run_dir,
        output_dir=output_dir,
        slurm_script=slurm_script,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        command=command,
        expected_outputs=expected_outputs,
        required_inputs=required_inputs,
        slurm_text=slurm_text,
        review_gate=review_gate,
    )


def submit_execution(
    spec_id: str,
    store: AgenticDiscoveryStore,
    params: dict[str, str] | None = None,
) -> dict[str, Any]:
    prepared = prepare_execution(spec_id, store=store, params=params)
    gate = prepared.review_gate
    if gate.get("required") and not gate.get("pass"):
        blockers = ["execution_spec_review_gate_not_passed"]
        if gate.get("missing_reviewers"):
            blockers.append("missing_reviewers:" + ",".join(gate["missing_reviewers"]))
        if gate.get("failing_reviewers"):
            blockers.append("failing_reviewers:" + ",".join(gate["failing_reviewers"]))
        if not gate.get("proposal_id"):
            blockers.append("missing_proposal_id")
        verification = VerificationRecord(
            target_id=prepared.spec.spec_id,
            target_type="execution_spec",
            verdict="fail",
            checks={"review_gate": gate},
            blockers=blockers,
            recommendations=[
                "Run the required proposal reviews or create a replacement execution proposal before submission."
            ],
            reviewer="guarded_slurm_submitter",
        )
        verification = store.verifications.append(verification)
        build_index(store)
        return {
            "submitted": False,
            "blocked_by_review_gate": True,
            "verification": record_to_dict(verification),
            "prepared": prepared_summary(prepared),
        }
    result = subprocess.run(
        ["sbatch", str(prepared.slurm_script)],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        verification = VerificationRecord(
            target_id=prepared.spec.spec_id,
            target_type="execution_spec",
            verdict="fail",
            checks={"sbatch_returncode": result.returncode},
            blockers=[result.stderr.strip() or result.stdout.strip() or "sbatch failed"],
            recommendations=["Inspect rendered Slurm script before retrying."],
            reviewer="guarded_slurm_submitter",
        )
        verification = store.verifications.append(verification)
        build_index(store)
        return {
            "submitted": False,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "verification": record_to_dict(verification),
            "prepared": prepared_summary(prepared),
        }
    match = JOB_ID_RE.search(result.stdout)
    job_id = match.group(1) if match else ""
    run = ExecutionRun(
        hypothesis_id=prepared.spec.hypothesis_id,
        candidate_id=prepared.spec.candidate_id,
        split_id=prepared.spec.split_id,
        script_path=str(_resolve_repo_path(prepared.spec.script)),
        command=shlex.join(prepared.command),
        artifacts=[str(path) for path in prepared.expected_outputs],
        metrics={"slurm_job_id": job_id, "execution_spec_id": prepared.spec.spec_id},
        mechanical_checks={
            "guarded_execution_spec": True,
            "proposal_review_gate": gate,
            "required_inputs_exist": True,
            "shell_execution": False,
            "slurm_script": str(prepared.slurm_script),
            "stdout_path": str(prepared.stdout_path),
            "stderr_path": str(prepared.stderr_path),
            "submitted_at": now_utc(),
        },
        status="submitted",
        notes=f"Submitted via guarded Slurm execution spec {prepared.spec.spec_id}.",
    )
    run.run_id = prepared.run_id_hint
    run = store.runs.append(run)
    build_index(store)
    return {
        "submitted": True,
        "job_id": job_id,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "run": record_to_dict(run),
        "prepared": prepared_summary(prepared),
    }


def check_status(store: AgenticDiscoveryStore, run_id: str = "", job_id: str = "") -> dict[str, Any]:
    run = store.runs.get(run_id) if run_id else None
    if run and not job_id:
        job_id = str(run.metrics.get("slurm_job_id", ""))
    if not job_id:
        raise ValueError("Provide --job-id or a run_id whose metrics include slurm_job_id")
    squeue = subprocess.run(["squeue", "-j", job_id, "-h", "-o", "%T"], check=False, capture_output=True, text=True)
    sacct = subprocess.run(
        ["sacct", "-j", job_id, "--format=JobID,State,ExitCode", "--parsable2", "--noheader"],
        check=False,
        capture_output=True,
        text=True,
    )
    state = (squeue.stdout.strip().splitlines() or [""])[0]
    if not state and sacct.stdout.strip():
        first = sacct.stdout.strip().splitlines()[0].split("|")
        if len(first) >= 2:
            state = first[1]
    mapped = _map_slurm_state(state)
    if run and mapped and run.status != mapped:
        run = store.runs.update(run.run_id, status=mapped)
        build_index(store)
    return {
        "job_id": job_id,
        "slurm_state": state,
        "mapped_status": mapped,
        "squeue": {"returncode": squeue.returncode, "stdout": squeue.stdout, "stderr": squeue.stderr},
        "sacct": {"returncode": sacct.returncode, "stdout": sacct.stdout, "stderr": sacct.stderr},
        "run": record_to_dict(run) if run else None,
    }


def ingest_run(run_id: str, store: AgenticDiscoveryStore) -> dict[str, Any]:
    run = store.runs.get(run_id)
    if run is None:
        raise KeyError(f"Run not found: {run_id}")
    artifacts = [Path(path).resolve() for path in run.artifacts]
    missing = [str(path) for path in artifacts if not path.exists()]
    metrics: dict[str, Any] = dict(run.metrics)
    artifact_summaries = []
    for path in artifacts:
        if path.exists():
            artifact_summaries.append(_artifact_summary(path))
            if path.suffix == ".json":
                try:
                    payload = json.loads(path.read_text())
                except json.JSONDecodeError:
                    payload = {}
                if isinstance(payload, dict):
                    metrics.update({f"artifact:{key}": value for key, value in payload.get("metrics", {}).items()})
    verdict = "pass" if not missing else "fail"
    blockers = [] if not missing else [f"Missing expected artifact: {path}" for path in missing]
    updated = store.runs.update(
        run_id,
        status="completed" if not missing else "failed",
        metrics=metrics,
        mechanical_checks={
            **run.mechanical_checks,
            "expected_artifacts_present": not missing,
            "artifact_summaries": artifact_summaries,
            "ingested_at": now_utc(),
        },
    )
    verification = VerificationRecord(
        target_id=run_id,
        target_type="execution_run",
        verdict=verdict,
        checks={"expected_artifacts_present": not missing, "artifact_count": len(artifacts)},
        blockers=blockers,
        recommendations=[] if not missing else ["Inspect Slurm stdout/stderr and rerun after fixing artifacts."],
        reviewer="guarded_artifact_ingestor",
    )
    verification = store.verifications.append(verification)
    build_index(store)
    return {"run": record_to_dict(updated), "verification": record_to_dict(verification)}


def parse_params(items: list[str]) -> dict[str, str]:
    params = {}
    for item in items:
        if "=" not in item:
            raise ValueError(f"Expected key=value param, got {item}")
        key, value = item.split("=", 1)
        params[key] = value
    return params


def spec_summary(spec: ExecutionSpec) -> dict[str, Any]:
    return {
        "spec_id": spec.spec_id,
        "description": spec.description,
        "proposal_id": spec.proposal_id,
        "candidate_id": spec.candidate_id,
        "plan_id": spec.plan_id,
        "script": spec.script,
        "expected_outputs": spec.expected_outputs,
        "slurm": record_slurm(spec.slurm),
    }


def spec_to_dict(spec: ExecutionSpec) -> dict[str, Any]:
    return {
        **spec_summary(spec),
        "hypothesis_id": spec.hypothesis_id,
        "split_id": spec.split_id,
        "args": spec.args,
        "interpreter": spec.interpreter,
        "required_inputs": spec.required_inputs,
        "output_dir": spec.output_dir,
        "notes": spec.notes,
    }


def prepared_summary(prepared: PreparedExecution) -> dict[str, Any]:
    return {
        "spec_id": prepared.spec.spec_id,
        "run_id_hint": prepared.run_id_hint,
        "run_dir": str(prepared.run_dir),
        "output_dir": str(prepared.output_dir),
        "slurm_script": str(prepared.slurm_script),
        "stdout_path": str(prepared.stdout_path),
        "stderr_path": str(prepared.stderr_path),
        "command": prepared.command,
        "required_inputs": [str(path) for path in prepared.required_inputs],
        "expected_outputs": [str(path) for path in prepared.expected_outputs],
        "review_gate": prepared.review_gate,
    }


def review_gate_for_spec(spec: ExecutionSpec, store: AgenticDiscoveryStore) -> dict[str, Any]:
    required = bool(spec.candidate_id or spec.hypothesis_id or spec.plan_id)
    base = {
        "required": required,
        "proposal_id": spec.proposal_id,
        "pass": not required,
        "reason": "not_scientific_execution_spec" if not required else "",
    }
    if not required:
        return base
    if not spec.proposal_id:
        return {
            **base,
            "reason": "scientific_execution_spec_missing_proposal_id",
            "static_validation_pass": False,
            "missing_reviewers": [],
            "failing_reviewers": [],
        }
    from .execution_proposals import review_gate_status

    gate = review_gate_status(store, spec.proposal_id)
    return {
        **gate,
        "required": True,
        "proposal_id": spec.proposal_id,
        "reason": "proposal_review_gate",
    }


def record_slurm(slurm: SlurmResources) -> dict[str, Any]:
    return {
        "job_name": slurm.job_name,
        "partition": slurm.partition,
        "account": slurm.account,
        "time": slurm.time,
        "cpus_per_task": slurm.cpus_per_task,
        "mem": slurm.mem,
        "gres": slurm.gres,
        "constraint": slurm.constraint,
        "extra_directives": slurm.extra_directives,
    }


def _render_slurm(spec: ExecutionSpec, command: list[str], stdout_path: Path, stderr_path: Path) -> str:
    lines = ["#!/usr/bin/env bash"]
    slurm = spec.slurm
    directives = [
        ("--job-name", slurm.job_name),
        ("--output", str(stdout_path)),
        ("--error", str(stderr_path)),
        ("--time", slurm.time),
        ("--cpus-per-task", str(slurm.cpus_per_task)),
        ("--mem", slurm.mem),
    ]
    if slurm.partition:
        directives.append(("--partition", slurm.partition))
    if slurm.account:
        directives.append(("--account", slurm.account))
    if slurm.gres:
        directives.append(("--gres", slurm.gres))
    if slurm.constraint:
        directives.append(("--constraint", slurm.constraint))
    for key, value in directives:
        lines.append(f"#SBATCH {key}={value}")
    for extra in slurm.extra_directives:
        if not extra.startswith("#SBATCH "):
            raise ValueError(f"extra_directive must start with '#SBATCH ': {extra}")
        lines.append(extra)
    lines.extend(["", "set -euo pipefail", f"cd {shlex.quote(str(REPO_ROOT))}", shlex.join(command), ""])
    return "\n".join(lines)


def _resolve_repo_path(path_text: str) -> Path:
    path = Path(path_text)
    if not path.is_absolute():
        path = REPO_ROOT / path
    path = path.resolve()
    if not any(_is_relative_to(path, root.resolve()) for root in APPROVED_READ_ROOTS):
        raise ValueError(f"Path escapes approved read roots: {path}")
    return path


def _resolve_approved_output(path_text: str) -> Path:
    path = _resolve_repo_path(path_text)
    if not any(_is_relative_to(path, root.resolve()) for root in APPROVED_OUTPUT_ROOTS):
        raise ValueError(f"Output path outside approved roots: {path}")
    return path


def _format(template: str, context: dict[str, str]) -> str:
    try:
        value = template.format(**context)
    except KeyError as exc:
        raise ValueError(f"Unknown template placeholder in {template!r}: {exc}") from exc
    if "\n" in value or "\x00" in value:
        raise ValueError(f"Unsafe formatted value contains newline/NUL: {template!r}")
    return value


def _validate_safe_list(name: str, values: list[str], allow_placeholders: bool) -> None:
    for value in values:
        _validate_token(name, value, allow_placeholders=allow_placeholders)


def _validate_token(name: str, value: str, allow_placeholders: bool) -> None:
    if "\n" in value or "\x00" in value:
        raise ValueError(f"Unsafe {name}: newline/NUL not allowed")
    check = value
    if allow_placeholders:
        check = re.sub(r"\{[A-Za-z0-9_.-]+\}", "PLACEHOLDER", check)
    if not SAFE_TOKEN.match(check) and not value.startswith("#SBATCH "):
        raise ValueError(f"Unsafe {name}: {value}")


def _validate_command_token(value: str) -> None:
    if "\n" in value or "\x00" in value:
        raise ValueError("Command token contains newline/NUL")


def _map_slurm_state(state: str) -> str:
    state = state.upper()
    if state in {"PENDING", "CONFIGURING", "COMPLETING"}:
        return "submitted"
    if state in {"RUNNING"}:
        return "running"
    if state in {"COMPLETED"}:
        return "completed"
    if state in {"FAILED", "CANCELLED", "TIMEOUT", "OUT_OF_MEMORY", "NODE_FAIL", "PREEMPTED"}:
        return "failed"
    return ""


def _artifact_summary(path: Path) -> dict[str, Any]:
    summary = {"path": str(path), "bytes": path.stat().st_size, "suffix": path.suffix}
    if path.suffix == ".json":
        try:
            data = json.loads(path.read_text())
        except json.JSONDecodeError:
            summary["json_valid"] = False
        else:
            summary["json_valid"] = True
            if isinstance(data, dict):
                summary["keys"] = sorted(data.keys())[:25]
    return summary


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _print(payload: Any, json_output: bool) -> int:
    if json_output:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        if isinstance(payload, list):
            for item in payload:
                print(json.dumps(item, sort_keys=True))
        else:
            print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
