# Knowledge Cards

Validated (and refuted) findings from the AI-READI research engine, distilled into **evidence
priors** the personal agent cites when reasoning about an individual. These are what the
frontend `EvidenceChip` links to and what keeps every recommendation grounded in a tested claim
rather than a vibe.

- Source of truth: `knowledge_cards.json` (array of cards).
- Each card traces to a real artifact in `engine/hypothesis/hypotheses/*.json` or the JEPA summary
  in `docs/research_engine/reports/`.
- `evidence_strength` is honest: `supported` / `completed` / `exploratory` / `refuted`. The
  refuted card is included on purpose — the system records negative evidence too.

## Card schema

```jsonc
{
  "id": "KC-...",                    // stable id, referenced by interventions & UI
  "title": "...",
  "finding": "...",                  // what was observed in the cohort
  "interpretation": "...",           // plain-language meaning
  "individual_application": "...",   // how to apply it N-of-1 to one user
  "evidence_strength": "supported",  // supported|completed|exploratory|refuted
  "source": { "system": "hypothesis", "ref": "H-MIG01" },
  "modalities": ["glucose", "wearable"],
  "metrics": ["glucose_hr_coupling"],
  "caveats": "..."                   // honest limits; agents must surface these
}
```

Add cards as the research engine validates more. Keep `caveats` truthful — the agent is
instructed to present them alongside the finding.
