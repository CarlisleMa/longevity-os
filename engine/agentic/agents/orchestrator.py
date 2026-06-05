"""Orchestrator: decomposes questions, routes to agents, synthesizes answers.

The top-level coordinator that manages the multi-agent workflow:
1. Decompose a research question into sub-tasks
2. Identify which modality/reasoning agents are needed
3. Dispatch tasks to agents
4. Validate findings via the critic
5. Synthesize a coherent answer
"""

import json

import anthropic

from . import config
from .base import BaseAgent, AgentResult
from .workspace import Workspace, StatisticalFinding
from .memory import Memory
from .critic import CriticAgent


ORCHESTRATOR_PROMPT = """\
You are the Orchestrator for an AI-READI multi-agent analysis system. You coordinate \
specialized agents to answer research questions about a multimodal health dataset \
(2,280 participants with clinical labs, ECG, CGM, wearable, retinal imaging, and \
environmental sensor data).

YOUR ROLE:
1. Decompose the user's question into specific sub-tasks.
2. Identify which agents are needed for each sub-task.
3. Describe each sub-task clearly so the agent can execute it.

AVAILABLE AGENTS:
  Tier 1 (Modality — data-facing, can execute code):
    ClinicalAgent:    Clinical feature matrix (125 cols), OMOP tables, lab comparisons
    GlucoseAgent:     CGM data, glycemic metrics (TIR, MAGE, AGP, dawn phenomenon)
    CardiacAgent:     12-lead ECG, intervals (QTc, PR), HRV (RMSSD)
    WearableAgent:    Garmin data — sleep architecture, circadian metrics, HR, SpO2, activity
    RetinalAgent:     OCT, OCTA, fundus photography, FLIO manifests and images
    EnvironmentAgent: Light spectrum, PM2.5, temperature, screen time

  Tier 2 (Reasoning — consume Tier 1 outputs):
    HypothesisAgent:  Proposes testable hypotheses from observed patterns
    CausalAgent:      Designs causal analyses (Granger, transfer entropy, CCM, PCMCI, mediation)
                      Also computes pairwise coupling measures for the coupling atlas:
                      cross-correlation, transfer entropy, cross-predictability, wavelet coherence,
                      and phase coherence between modality pairs
    PhenotypeAgent:   Clusters participants into data-driven subtypes
                      Also runs tensor decomposition for latent physiological modes
    AgingClockAgent:  Coordinates per-organ age estimation and cross-organ analysis
                      Also builds coupling-based aging clocks from inter-organ coupling features
    LiteratureAgent:  Provides domain context, thresholds, citations

  Validation:
    CriticAgent:      Reviews every finding (confounders, site bias, FDR, effect sizes)

OUTPUT FORMAT:
Respond with a JSON array of tasks. Each task has:
  - "agent": agent name (e.g. "ClinicalAgent")
  - "task": clear description of what the agent should do
  - "depends_on": list of task indices this depends on (empty if independent)

Example:
[
  {"agent": "ClinicalAgent", "task": "Load the feature matrix and compute mean HbA1c by study_group, adjusting for age. Report effect size.", "depends_on": []},
  {"agent": "GlucoseAgent", "task": "Compute per-person CGM TIR and CV for all participants with CGM data.", "depends_on": []},
  {"agent": "CausalAgent", "task": "Test whether HbA1c is correlated with TIR after adjusting for age, using data from ClinicalAgent and GlucoseAgent.", "depends_on": [0, 1]}
]

RULES:
- Break complex questions into specific, actionable sub-tasks.
- Independent tasks should have empty depends_on (they can run in parallel).
- Always include a CriticAgent task at the end for validation.
- Be specific about what each agent should compute and return.
"""


class Orchestrator:
    """Coordinates multi-agent workflows."""

    def __init__(self, workspace: Workspace, memory: Memory):
        self.workspace = workspace
        self.memory = memory
        self.model = config.MODEL_ORCHESTRATOR
        self.client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        self.critic = CriticAgent()

        # Agent registry — populated by register_agent()
        self.agents: dict[str, BaseAgent] = {}

    def register_agent(self, agent: BaseAgent):
        """Register an agent by its name."""
        self.agents[agent.name] = agent

    def register_agents(self, agents: list[BaseAgent]):
        for agent in agents:
            self.register_agent(agent)

    def decompose(self, question: str) -> list[dict]:
        """Decompose a question into agent-addressable sub-tasks."""
        mem_context = self.memory.get_relevant(question)
        ws_context = self.workspace.summary()

        user_msg = f"Question: {question}"
        if ws_context != "(workspace is empty)":
            user_msg += f"\n\nCurrent workspace state:\n{ws_context}"
        if mem_context:
            user_msg += f"\n\n{mem_context}"

        response = self.client.messages.create(
            model=self.model,
            max_tokens=config.MAX_TOKENS,
            temperature=0.0,
            system=ORCHESTRATOR_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )

        raw = response.content[0].text

        # Parse JSON from response (may be wrapped in ```json ... ```)
        json_str = raw
        if "```json" in raw:
            json_str = raw.split("```json")[1].split("```")[0]
        elif "```" in raw:
            json_str = raw.split("```")[1].split("```")[0]

        try:
            tasks = json.loads(json_str)
        except json.JSONDecodeError:
            # Fallback: single task using the full question
            tasks = [{"agent": "ClinicalAgent", "task": question, "depends_on": []}]

        return tasks

    def dispatch(self, task_spec: dict) -> AgentResult:
        """Dispatch a single task to the specified agent."""
        agent_name = task_spec["agent"]
        task_description = task_spec["task"]

        agent = self.agents.get(agent_name)
        if agent is None:
            return AgentResult(
                answer=f"[ERROR: Agent '{agent_name}' not registered]",
                turns=0,
            )

        return agent.run(task_description)

    def run(self, question: str) -> str:
        """Full orchestration pipeline: decompose -> dispatch -> validate -> synthesize."""

        # 1. Decompose
        task_specs = self.decompose(question)

        # 2. Dispatch (respecting dependencies)
        results: list[tuple[dict, AgentResult]] = []
        completed_indices: set[int] = set()

        # Simple sequential execution respecting depends_on
        for i, spec in enumerate(task_specs):
            deps = spec.get("depends_on", [])
            # In a production system, independent tasks would run in parallel.
            # For now, sequential execution is simpler and sufficient.
            for dep in deps:
                if dep not in completed_indices:
                    pass  # dependency not met, but we execute sequentially anyway

            if spec["agent"] == "CriticAgent":
                # Critic reviews accumulated findings
                for finding in self.workspace.findings:
                    if not any(v.finding_id == finding.id for v in self.workspace.verdicts):
                        verdict = self.critic.review(
                            finding_id=finding.id,
                            finding_text=finding.interpretation,
                            code_history=f"Feature: {finding.feature}, Test: {finding.test}, "
                                         f"p={finding.pvalue}, effect_size={finding.effect_size}",
                        )
                        self.workspace.add_verdict(verdict)
            else:
                result = self.dispatch(spec)
                results.append((spec, result))

            completed_indices.add(i)

        # 3. Synthesize
        return self._synthesize(question, task_specs, results)

    def _synthesize(self, question: str, task_specs: list[dict],
                    results: list[tuple[dict, AgentResult]]) -> str:
        """Synthesize agent results into a coherent answer."""
        parts = [f"Question: {question}\n"]

        for spec, result in results:
            parts.append(f"\n--- {spec['agent']} ---")
            parts.append(f"Task: {spec['task']}")
            parts.append(f"Answer: {result.answer[:2000]}")

        ws_summary = self.workspace.summary()
        if ws_summary != "(workspace is empty)":
            parts.append(f"\n--- Workspace ---\n{ws_summary}")

        # Use LLM to synthesize
        synthesis_prompt = (
            "You are synthesizing results from multiple specialist agents into a coherent "
            "answer to a research question. Include key statistics, effect sizes, and caveats. "
            "Note any critic concerns."
        )

        response = self.client.messages.create(
            model=self.model,
            max_tokens=config.MAX_TOKENS,
            temperature=0.0,
            system=synthesis_prompt,
            messages=[{"role": "user", "content": "\n".join(parts)}],
        )

        return response.content[0].text
