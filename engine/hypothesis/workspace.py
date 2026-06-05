"""Hypothesis workspace: persistent store for the hypothesis-driven discovery pipeline.

JSON-backed workspace that tracks hypotheses through their lifecycle:
  proposed -> critiqued -> validated -> queued -> executing -> completed -> verified

Agents interact with this workspace to:
  - Deposit new hypotheses (proposer)
  - Validate and prioritize (critic)
  - Pick next hypothesis to test (executor)
  - Record results (executor)
  - Verify results (verifier)
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .schemas import (
    CriticVerdict,
    Hypothesis,
    HypothesisResult,
    TestPlan,
    load_all_hypotheses,
    save_hypothesis,
)


class HypothesisWorkspace:
    """Persistent hypothesis store backed by a directory of JSON files."""

    def __init__(self, root: str | Path = None):
        if root is None:
            root = Path(__file__).parent / "hypotheses"
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._cache: dict[str, Hypothesis] = {}
        self._load_all()

    def _load_all(self):
        """Load all hypotheses from disk."""
        self._cache = {}
        for h in load_all_hypotheses(self.root):
            self._cache[h.id] = h

    def reload(self):
        """Reload from disk (useful after external modifications)."""
        self._load_all()

    # --- Queries ---

    def all(self) -> list[Hypothesis]:
        return sorted(self._cache.values(), key=lambda h: -h.priority)

    def get(self, hypothesis_id: str) -> Hypothesis | None:
        return self._cache.get(hypothesis_id)

    def by_status(self, status: str) -> list[Hypothesis]:
        return sorted(
            [h for h in self._cache.values() if h.status == status],
            key=lambda h: -h.priority,
        )

    def by_category(self, category: str) -> list[Hypothesis]:
        return sorted(
            [h for h in self._cache.values() if h.category == category],
            key=lambda h: -h.priority,
        )

    def validated_queue(self) -> list[Hypothesis]:
        """Hypotheses ready for execution, ordered by priority."""
        return self.by_status("validated") + self.by_status("queued")

    def next_to_execute(self) -> Hypothesis | None:
        """Pick the highest-priority validated hypothesis."""
        queue = self.validated_queue()
        return queue[0] if queue else None

    # --- Mutations ---

    def add(self, h: Hypothesis) -> str:
        """Add a hypothesis to the workspace."""
        h.updated = datetime.now().isoformat()
        self._cache[h.id] = h
        save_hypothesis(h, self.root)
        return h.id

    def update_status(self, hypothesis_id: str, status: str) -> None:
        h = self._cache[hypothesis_id]
        h.status = status
        h.updated = datetime.now().isoformat()
        save_hypothesis(h, self.root)

    def set_priority(self, hypothesis_id: str, priority: float) -> None:
        h = self._cache[hypothesis_id]
        h.priority = priority
        h.updated = datetime.now().isoformat()
        save_hypothesis(h, self.root)

    def set_test_plan(self, hypothesis_id: str, plan: TestPlan) -> None:
        h = self._cache[hypothesis_id]
        h.test_plan = plan
        h.updated = datetime.now().isoformat()
        save_hypothesis(h, self.root)

    def set_results(self, hypothesis_id: str, results: HypothesisResult) -> None:
        h = self._cache[hypothesis_id]
        h.results = results
        h.status = "completed"
        h.updated = datetime.now().isoformat()
        save_hypothesis(h, self.root)

    def set_verdict(self, hypothesis_id: str, verdict: CriticVerdict) -> None:
        h = self._cache[hypothesis_id]
        h.critic_verdict = verdict
        h.status = "verified"
        h.updated = datetime.now().isoformat()
        save_hypothesis(h, self.root)

    # --- Reports ---

    def summary(self) -> str:
        """Text summary for injection into agent prompts."""
        lines = [f"=== Hypothesis Workspace: {len(self._cache)} hypotheses ===\n"]

        # Status counts
        from collections import Counter
        status_counts = Counter(h.status for h in self._cache.values())
        lines.append("Status breakdown:")
        for status, count in sorted(status_counts.items()):
            lines.append(f"  {status}: {count}")
        lines.append("")

        # Category counts
        cat_counts = Counter(h.category for h in self._cache.values())
        lines.append("Category breakdown:")
        for cat, count in sorted(cat_counts.items()):
            lines.append(f"  {cat}: {count}")
        lines.append("")

        # Top-priority hypotheses
        validated = self.validated_queue()
        if validated:
            lines.append(f"Top {min(5, len(validated))} in execution queue:")
            for h in validated[:5]:
                lines.append(f"  {h.summary()}")
            lines.append("")

        # Recently completed
        completed = [h for h in self._cache.values() if h.status in ("completed", "verified", "supported", "refuted")]
        if completed:
            completed.sort(key=lambda h: h.updated, reverse=True)
            lines.append(f"Recently completed ({len(completed)} total):")
            for h in completed[:5]:
                lines.append(f"  {h.summary()}")

        return "\n".join(lines)

    def full_report(self) -> str:
        """Full markdown report of all hypotheses."""
        lines = ["# Hypothesis Workspace Report\n"]
        lines.append(f"Generated: {datetime.now().isoformat()}\n")
        lines.append(self.summary())
        lines.append("\n---\n")

        for h in self.all():
            lines.append(h.full_report())
            lines.append("\n---\n")

        return "\n".join(lines)
