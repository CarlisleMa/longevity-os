# Execution Specs

Execution specs are the only approved path from an agentic method plan to Slurm.
Agents cannot submit arbitrary shell commands.

New analyses should be staged first through `python -m agentic_discovery compile`
or the MCP tools `propose_execution`, `validate_execution_proposal`, and
`promote_execution_proposal`. Proposed scripts/specs live under ignored
`agentic_discovery/state/execution_proposals/` until validation passes and the
reviewer gate approves them.

Promotion requires:

- static proposal validation with no blockers
- a `scientific-critic` review with verdict `pass` and no blockers
- a `feasibility-leakage` review with verdict `pass` and no blockers
- a `mechanical-verifier` review with verdict `pass` and no blockers

The CLI uses the generic `compile review` command for human/audit use. SDK
agents receive role-specific review tools instead:
`scientific_critic_review_execution_proposal`,
`feasibility_leakage_review_execution_proposal`, and
`mechanical_verifier_review_execution_proposal`. The executor agent does not
receive these reviewer tools.

Each `*.json` file declares:

- an approved Python script under `scripts/`, `agentic_discovery/analysis/`, or
  `agentic_discovery/scripts/`
- fixed arguments with limited `{placeholder}` substitution
- required input paths
- expected output artifact paths
- Slurm resources

Promoted generated scripts are copied to `agentic_discovery/analysis/generated/`.

The guarded submitter validates paths, renders a Slurm script under
`agentic_discovery/state/slurm_runs/<run_id>/`, and calls `sbatch` with an
argument list. It never uses `shell=True`. Scientific specs with a candidate,
hypothesis, or method plan also need a passing proposal review gate at submit
time. Dry-run still renders these specs for inspection; submission is blocked
until the gate passes.

Use:

```bash
python -m agentic_discovery compile context EXECPROP-... --include-script
python -m agentic_discovery compile review EXECPROP-... --reviewer scientific-critic --verdict pass
python -m agentic_discovery compile review EXECPROP-... --reviewer feasibility-leakage --verdict pass
python -m agentic_discovery compile review EXECPROP-... --reviewer mechanical-verifier --verdict pass
python -m agentic_discovery compile promote EXECPROP-... --yes
python -m agentic_discovery slurm list-specs
python -m agentic_discovery slurm dry-run smoke_registry_summary
python -m agentic_discovery slurm submit smoke_registry_summary --yes
python -m agentic_discovery slurm status --run-id RUN-...
python -m agentic_discovery slurm ingest RUN-...
```
