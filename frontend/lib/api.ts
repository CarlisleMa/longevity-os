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

export type DebateEvent =
  | { kind: "turn"; phase: string; agent: AgentCard }
  | { kind: "token"; text: string }
  | { kind: "end_turn"; citations: string[] }
  | { kind: "done"; citations: string[]; safety: { passed: boolean; note: string }; reply: string };

/** Stream a multi-agent team debate (SSE). Calls onEvent for each event. */
export async function streamDebate(
  userId: string,
  message: string,
  onEvent: (e: DebateEvent) => void,
  signal?: AbortSignal,
) {
  const res = await fetch(`${BASE}/api/users/${userId}/coach/debate`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ message }),
    signal,
  });
  if (!res.ok || !res.body) throw new Error(`${res.status}`);
  const reader = res.body.getReader();
  const dec = new TextDecoder();
  let buf = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    let i: number;
    while ((i = buf.indexOf("\n\n")) >= 0) {
      const line = buf.slice(0, i).trim();
      buf = buf.slice(i + 2);
      if (line.startsWith("data:")) {
        try {
          onEvent(JSON.parse(line.slice(5).trim()));
        } catch {
          /* ignore keep-alives */
        }
      }
    }
  }
}
