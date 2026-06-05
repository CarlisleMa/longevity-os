import type {
  Dashboard,
  Intervention,
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

export const api = {
  meta: () => get<{ run_modes: Record<string, boolean>; knowledge_cards: number }>("/api/meta"),
  dashboard: (userId: string) => get<Dashboard>(`/api/users/${userId}/dashboard`),
  timeline: (userId: string) => get<TimelineEvent[]>(`/api/users/${userId}/timeline`),
  knowledgeCards: () => get<KnowledgeCard[]>("/api/knowledge-cards"),
  knowledgeCard: (id: string) => get<KnowledgeCard>(`/api/knowledge-cards/${id}`),
  observe: (userId: string) => post<Observation>(`/api/users/${userId}/agent/observe`),
  interventions: (userId: string) => get<Intervention[]>(`/api/users/${userId}/interventions`),
  acceptIntervention: (userId: string, id: string) =>
    post<Intervention>(`/api/users/${userId}/interventions/${id}/accept`),
};

export const DEMO_USER = "demo_alex";
