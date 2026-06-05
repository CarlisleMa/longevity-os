// Mirrors backend/longevityos_api/schemas.py — keep in sync.

export interface ScoreCard {
  chronological_age: number;
  biological_age: number;
  age_accel: number;
  age_accel_percentile?: number | null;
  delta_vs_baseline?: number | null;
  as_of: string;
  status: string;
}

export interface SystemScore {
  system: string;
  age_accel: number;
  percentile?: number | null;
  status: string;
}

export interface CouplingMetric {
  key: string;
  label: string;
  value: number;
  baseline?: number | null;
  delta_vs_baseline?: number | null;
  unit?: string | null;
  read?: string | null;
  evidence_card?: string | null;
}

export interface GateVerdict {
  gate: string;
  passed: boolean;
  note: string;
}

export interface Observation {
  id: string;
  text: string;
  evidence_cards: string[];
  as_of: string;
}

export interface Intervention {
  id: string;
  title: string;
  rationale: string;
  evidence_cards: string[];
  gates: GateVerdict[];
  expected_benefit?: string | null;
  effort?: string | null;
  status: string;
  reasoning_trace?: string | null;
}

export interface KnowledgeCard {
  id: string;
  title: string;
  finding: string;
  interpretation: string;
  individual_application: string;
  evidence_strength: string;
  source: Record<string, string>;
  modalities: string[];
  metrics: string[];
  caveats?: string | null;
}

export interface TimelineEvent {
  timestamp: string;
  label: string;
  biological_age?: number | null;
  modalities_present: string[];
}

export interface Dashboard {
  user_id: string;
  display_name: string;
  scorecard: ScoreCard;
  systems: SystemScore[];
  coupling: CouplingMetric[];
  latest_observation?: Observation | null;
  top_intervention?: Intervention | null;
}

export interface KnowledgeBaseItem {
  modality: string;
  label: string;
  value: string;
  trend?: string | null;
  as_of?: string | null;
  evidence_card?: string | null;
}

export interface KnowledgeBaseResponse {
  user_id: string;
  groups: Record<string, KnowledgeBaseItem[]>;
}
