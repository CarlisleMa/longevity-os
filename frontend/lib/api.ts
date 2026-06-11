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

// The demo user's data is static (a fixed synthetic record), so we bundle it as
// JSON into the frontend and serve it from Vercel's CDN. This makes every page
// load instantly and removes the dependency on the (sleepy, free-tier) backend
// for reads — the backend is only needed for the live AI Coach and write actions.
async function getStatic<T>(file: string): Promise<T> {
  const res = await fetch(`/demo/${file}`, { cache: "force-cache" });
  if (!res.ok) throw new Error(`${res.status} /demo/${file}`);
  return res.json() as Promise<T>;
}

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
  // Reads — served instantly from the bundled static demo data (Vercel CDN).
  meta: () =>
    getStatic<{ version: string; run_modes: Record<string, boolean>; knowledge_cards: number }>(
      "meta.json",
    ),
  dashboard: (_userId: string) => getStatic<Dashboard>("dashboard.json"),
  timeline: (_userId: string) => getStatic<TimelineEvent[]>("timeline.json"),
  knowledgeBase: (_userId: string) => getStatic<KnowledgeBaseResponse>("knowledge-base.json"),
  knowledgeCards: () => getStatic<KnowledgeCard[]>("knowledge-cards.json"),
  knowledgeCard: async (id: string) => {
    const cards = await getStatic<KnowledgeCard[]>("knowledge-cards.json");
    const card = cards.find((c) => c.id === id);
    if (!card) throw new Error(`404 knowledge-card ${id}`);
    return card;
  },
  observations: (_userId: string) => getStatic<Observation[]>("observations.json"),
  interventions: (_userId: string) => getStatic<Intervention[]>("interventions.json"),
  day: (_userId: string) => getStatic<DayResponse>("day.json"),
  coachRoster: () => getStatic<{ agents: AgentCard[] }>("coach-agents.json"),

  // "Re-observe" — pick a fresh insight from the bundled set (no backend needed).
  observe: async (_userId: string) => {
    const obs = await getStatic<Observation[]>("observations.json");
    if (!obs.length) throw new Error("no observations");
    return obs[Math.floor(Math.random() * obs.length)];
  },

  // Writes & live AI — these still go to the backend (BASE).
  acceptIntervention: (userId: string, id: string) =>
    post<Intervention>(`/api/users/${userId}/interventions/${id}/accept`),
  dismissIntervention: (userId: string, id: string) =>
    post<Intervention>(`/api/users/${userId}/interventions/${id}/dismiss`),
  coach: (userId: string, message: string, history: CoachTurn[] = []) =>
    postJson<CoachResponse>(`/api/users/${userId}/coach`, { message, history }),
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
