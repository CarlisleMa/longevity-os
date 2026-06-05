# Agentic Discovery

This package is a separate implementation track for the hypothesis-first
agentic discovery plan. It does not replace `hypothesis_driven/`. The older
prototype remains a legacy hypothesis workspace; this package adds durable
registries and retrieval utilities that can be used by humans or agents before
proposing, criticizing, executing, or verifying scientific work.

## Purpose

The high-level project goal is an autonomous multimodal discovery system for
aging, diabetes, disease burden, and coordinated physiology. A chronological
aging clock is one baseline task, but the larger goal is a cumulative system
that can:

- deposit new hypothesis candidates from human ideas, data analysis, literature,
  critic objections, tools, datasets, and surprising findings
- keep papers, extracted claims, tools, datasets, results, and verification
  records machine-readable
- retrieve relevant prior state before an agent reasons or runs code
- represent relationships between candidates, legacy hypotheses, evidence, and
  follow-up ideas
- plan discovery rounds without losing provenance

## Current Scope

This is the first infrastructure layer. It provides:

- typed records in `schemas.py`
- JSONL registries in `state/`
- a SQLite retrieval index over the new registries plus legacy
  `hypothesis_driven/hypotheses/*.json`
- CLI entry points for candidate deposition, knowledge registration, graph
  edges, and round planning
- SDK-backed agent definitions for literature/tool/dataset enrichment,
  hypothesis deposition, critique, feasibility/leakage review, method planning,
  execution record registration, verification, surprise mining, and synthesis

Live SDK runs use the Claude Agent SDK by default. The runner uses the bundled
Claude Code binary shipped with `claude-agent-sdk`, so it does not depend on a
system `node` executable. It can authenticate through Claude Code login or
through `ANTHROPIC_API_KEY`. As of 2026-05-15, Anthropic's separate monthly
Claude-plan Agent SDK credit is documented as starting on 2026-06-15; API-key
usage remains separate pay-as-you-go billing.

It can submit Slurm jobs only through approved execution specs and only when a
human explicitly authorizes guarded submission. New execution proposals must pass
static validation and the required reviewer gate before they can be promoted.

## Commands

Deposit a candidate without writing:

```bash
python -m agentic_discovery candidates deposit \
  --title "Activity-to-glucose recovery delay" \
  --claim "Post-activity glucose recovery is slower in diabetes groups than controls." \
  --modality cgm \
  --modality wearable \
  --confounder age \
  --confounder site \
  --negative-control "random non-activity windows" \
  --leakage-risk "same participant crossing train/test split" \
  --dry-run
```

Register a paper:

```bash
python -m agentic_discovery knowledge add-paper \
  --title "Paper title" \
  --author "First Author" \
  --year 2024 \
  --topic "second-generation aging clocks" \
  --modality clinical
```

Register a surprising finding:

```bash
python -m agentic_discovery knowledge add-surprise \
  --summary "Retinal clock acceleration is strongest in a site-specific subgroup" \
  --origin-artifact results/clocks/retinal_age_metrics.csv \
  --p-hacking-risk "post-hoc subgroup pattern; requires preregistered follow-up" \
  --follow-up-needed "deposit and critique a site-stratified replication candidate"
```

Build and query the retrieval index:

```bash
python -m agentic_discovery knowledge index
python -m agentic_discovery knowledge search "retinal aging diabetes clock"
```

Archive exploratory registry state and import legacy hypotheses:

```bash
python -m agentic_discovery migrate legacy-hypotheses --dry-run
python -m agentic_discovery migrate legacy-hypotheses \
  --clear-existing \
  --archive-label first_live_claude_run \
  --status-policy reset
python -m agentic_discovery migrate archive-runtime \
  --archive-dir agentic_discovery/state/archive/<timestamp>_first_live_claude_run
```

Register an execution artifact and verification:

```bash
python -m agentic_discovery evidence add-plan \
  --target-id CAND-20260514-0001 \
  --objective "Test post-activity glucose recovery delay with balanced split" \
  --split-id balanced_split_v1 \
  --adjust age \
  --adjust site \
  --negative-control "random non-activity windows" \
  --leakage-check "participant-disjoint split" \
  --statistical-test "group-adjusted mixed model" \
  --status registered

python -m agentic_discovery evidence add-run \
  --hypothesis-id H-NEW10 \
  --split-id balanced_split_v1 \
  --script-path scripts/hypothesis/h_new10_activity_glucose.py \
  --artifact results/hypotheses/h_new10_activity_glucose.csv \
  --metric primary_p=0.01 \
  --check participant_split_leakage=false \
  --status completed

python -m agentic_discovery evidence add-verification \
  --target-id H-NEW10 \
  --target-type run \
  --verdict concern \
  --check age_site_balance=true \
  --blocker "needs negative-control replication"
```

Plan the next discovery round:

```bash
python -m agentic_discovery rounds plan --limit 5
```

Compile method plans into approved Slurm execution specs:

```bash
python -m agentic_discovery compile propose \
  --candidate-id CAND-LEGACY-H-MIG01 \
  --plan-id PLAN-20260515-0001 \
  --title h_mig01_glucose_hr_retest \
  --script-file /path/to/proposed_analysis.py \
  --spec-json-file /path/to/proposed_spec.json
python -m agentic_discovery compile validate EXECPROP-...
python -m agentic_discovery compile context EXECPROP-... --include-script
python -m agentic_discovery compile review EXECPROP-... \
  --reviewer scientific-critic \
  --verdict pass \
  --checks-json '{"hypothesis_alignment": true}'
python -m agentic_discovery compile review EXECPROP-... \
  --reviewer feasibility-leakage \
  --verdict pass \
  --checks-json '{"leakage_controls_checked": true}'
python -m agentic_discovery compile review EXECPROP-... \
  --reviewer mechanical-verifier \
  --verdict pass \
  --checks-json '{"paths_and_artifacts_checked": true}'
python -m agentic_discovery compile promote EXECPROP-... --yes
```

Promotion copies validated and reviewer-approved proposal code into
`agentic_discovery/analysis/generated/`, writes an approved JSON spec under
`agentic_discovery/execution_specs/`, and marks the linked method plan `ready`.
The required promotion reviewers are `scientific-critic`,
`feasibility-leakage`, and `mechanical-verifier`. Any missing reviewer, non-pass
verdict, or reviewer blocker prevents promotion.

Validate and submit approved Slurm execution specs:

```bash
python -m agentic_discovery slurm list-specs
python -m agentic_discovery slurm dry-run smoke_registry_summary
python -m agentic_discovery slurm dry-run h_mig01_glucose_hr_retest
python -m agentic_discovery slurm submit smoke_registry_summary --yes
python -m agentic_discovery slurm status --run-id RUN-20260515-0001
python -m agentic_discovery slurm ingest RUN-20260515-0001
```

Agents only receive guarded execution tools:

- `propose_execution`
- `list_execution_proposals`
- `retrieve_execution_proposal`
- `validate_execution_proposal`
- `scientific_critic_review_execution_proposal`
- `feasibility_leakage_review_execution_proposal`
- `mechanical_verifier_review_execution_proposal`
- `promote_execution_proposal`
- `list_execution_specs`
- `dry_run_execution_spec`
- `submit_execution_spec`
- `check_slurm_status`
- `ingest_execution_run`

They do not receive raw shell execution. The executor agent also does not receive
reviewer-gate tools. Submission validates script paths, input paths, output
roots, fixed Slurm resources, expected artifacts, and the proposal review gate
for scientific specs. Dry-run remains available for inspection even when a
pre-gate spec is not submit-eligible.

## SDK Runner

Check whether the Claude Agent SDK is available and authenticated:

```bash
python -m agentic_discovery sdk diagnose
```

Produce a deterministic non-LLM preflight plan:

```bash
python -m agentic_discovery sdk dry-run --limit 5
```

Run one SDK-backed discovery round:

```bash
python -m agentic_discovery sdk run \
  --limit 3 \
  --model sonnet \
  --instruction "Enrich and critique the top candidate, then register a method plan only if feasibility is adequate."
```

The manager coordinates these specialist agents:

- Literature Tool Dataset Agent
- Hypothesis Depositor Agent
- Scientific Critic Agent
- Feasibility Leakage Agent
- Method Planner Agent
- Executor Agent
- Mechanical Verifier Agent
- Surprise Miner Agent
- Synthesis Round Report Agent

## State Files

The default state root is `agentic_discovery/state/`.

- `candidates.jsonl`
- `papers.jsonl`
- `claims.jsonl`
- `tools.jsonl`
- `datasets.jsonl`
- `surprises.jsonl`
- `edges.jsonl`
- `method_plans.jsonl`
- `runs.jsonl`
- `verifications.jsonl`

The retrieval index `retrieval_index.sqlite` is derived state and should not be
treated as the source of truth.
