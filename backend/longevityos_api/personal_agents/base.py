"""Base types for personal agents."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AgentNote:
    """One agent's contribution to a consult."""

    key: str
    name: str
    title: str
    glyph: str
    text: str
    brief: str = ""
    citations: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)


class PersonalAgent:
    key = ""
    name = ""
    title = ""
    role = "specialist"  # specialist | orchestrator | safety | synthesis
    glyph = ""
    keywords: tuple[str, ...] = ()

    def card(self) -> dict:
        return {"key": self.key, "name": self.name, "title": self.title, "role": self.role, "glyph": self.glyph}

    def relevance(self, q: str, ctx: dict) -> float:
        if not self.keywords:
            return 0.0
        hits = sum(1 for w in self.keywords if w in q)
        return min(1.0, hits * 0.5)

    def contribute(self, q: str, ctx: dict) -> Optional[AgentNote]:
        return None
