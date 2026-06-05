import type {
  AgentCard,
  CoachResponse,
  CoachTurn,
  Dashboard,
  DayResponse,
  Intervention,
  KnowledgeBaseResponse,
  KnowledgeCard,
  Observation,
  TimelineEvent,
} from "./types";

const BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`${res.status} ${path}`);
  return res.json() as Promise<T>;
}

async function post<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { method: "POST" });
  if (!res.ok) throw new Error(`${res.status} ${path}`);
  return res.json() as Promise<T>;
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`${res.status} ${path}`);
  return res.json() as Promise<T>;
}

export const api = {
  meta: () =>
    get<{ version: string; run_modes: Record<string, boolean>; knowledge_cards: number }>(
      "/api/meta",
    ),
  dashboard: (userId: string) => get<Dashboard>(`/api/users/${userId}/dashboard`),
  timeline: (userId: string) => get<TimelineEvent[]>(`/api/users/${userId}/timeline`),
  knowledgeBase: (userId: string) =>
    get<KnowledgeBaseResponse>(`/api/users/${userId}/knowledge-base`),
  knowledgeCards: () => get<KnowledgeCard[]>("/api/knowledge-cards"),
  knowledgeCard: (id: string) => get<KnowledgeCard>(`/api/knowledge-cards/${id}`),
  observe: (userId: string) => post<Observation>(`/api/users/${userId}/agent/observe`),
  observations: (userId: string) =>
    get<Observation[]>(`/api/users/${userId}/agent/observations`),
  interventions: (userId: string) => get<Intervention[]>(`/api/users/${userId}/interventions`),
  acceptIntervention: (userId: string, id: string) =>
    post<Intervention>(`/api/users/${userId}/interventions/${id}/accept`),
  dismissIntervention: (userId: string, id: string) =>
    post<Intervention>(`/api/users/${userId}/interventions/${id}/dismiss`),
  day: (userId: string) => get<DayResponse>(`/api/users/${userId}/day`),
  coach: (userId: string, message: string, history: CoachTurn[] = []) =>
    postJson<CoachResponse>(`/api/users/${userId}/coach`, { message, history }),
  coachRoster: () => get<{ agents: AgentCard[] }>("/api/coach/agents"),
};

export const DEMO_USER = "demo_alex";
