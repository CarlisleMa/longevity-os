"use client";

import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, DEMO_USER, streamDebate } from "@/lib/api";
import type { AgentCard, AgentNote, CoachTurn } from "@/lib/types";
import { PageHeader } from "@/components/page-header";
import { EvidenceChip } from "@/components/evidence-chip";
import { cn } from "@/lib/utils";
import {
  Activity,
  ChevronDown,
  ClipboardList,
  Compass,
  Dumbbell,
  FlaskConical,
  Leaf,
  Mic,
  Moon,
  Phone,
  PhoneOff,
  ScrollText,
  Send,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Swords,
  Users,
  Utensils,
  type LucideIcon,
} from "lucide-react";

const GLYPH: Record<string, { Icon: LucideIcon; color: string }> = {
  compass: { Icon: Compass, color: "#575ecf" },
  utensils: { Icon: Utensils, color: "#ff5a1f" },
  dumbbell: { Icon: Dumbbell, color: "#dc4a2b" },
  moon: { Icon: Moon, color: "#6d5dd3" },
  pulse: { Icon: Activity, color: "#2f9e8f" },
  flask: { Icon: FlaskConical, color: "#c77d1a" },
  leaf: { Icon: Leaf, color: "#4e8c6a" },
  clipboard: { Icon: ClipboardList, color: "#d99a2b" },
  shield: { Icon: ShieldCheck, color: "#6e695e" },
  scroll: { Icon: ScrollText, color: "#8b8577" },
};
const gstyle = (g: string) => GLYPH[g] ?? { Icon: Sparkles, color: "#575ecf" };

function AgentAvatar({ glyph, size = 28 }: { glyph: string; size?: number }) {
  const { Icon, color } = gstyle(glyph);
  return (
    <span
      className="grid shrink-0 place-items-center rounded-lg"
      style={{ width: size, height: size, background: color + "1f", color }}
    >
      <Icon size={size * 0.5} />
    </span>
  );
}

const PHASE: Record<string, string> = {
  frame: "convenes the team",
  opening: "opening statement",
  rebuttal: "rebuttal",
  safety: "safety review",
  verdict: "verdict",
};

function DebateView({
  turns,
  debating,
  onStart,
  suggestions,
  live,
}: {
  turns: DebateTurn[];
  debating: boolean;
  onStart: (q: string) => void;
  suggestions: string[];
  live: boolean;
}) {
  const [q, setQ] = useState("");
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    ref.current?.scrollTo({ top: ref.current.scrollHeight, behavior: "smooth" });
  }, [turns]);

  return (
    <div className="flex h-[62vh] flex-col overflow-hidden rounded-2xl border border-border bg-surface shadow-card">
      <div className="flex items-center justify-between border-b border-border px-4 py-2.5">
        <div className="flex items-center gap-2 text-sm font-medium">
          <Swords size={15} className="text-vital-soft" /> Team debate
        </div>
        <span
          className={cn(
            "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px]",
            live ? "border-good/30 bg-good/10 text-good" : "border-border-strong bg-surface-2 text-muted",
          )}
          title={live ? "Each agent is a live Claude call" : "Grounded agents (set ANTHROPIC_API_KEY for live Claude)"}
        >
          <Sparkles size={11} /> {live ? "Live · Claude" : "Grounded"}
        </span>
      </div>

      <div ref={ref} className="flex-1 space-y-4 overflow-y-auto p-5">
        {turns.length === 0 && !debating && (
          <div className="grid h-full place-items-center text-center text-sm text-muted">
            Pose a question and watch the team debate it — opening statements, rebuttals, then a verdict.
          </div>
        )}
        {turns.map((t, i) => {
          const verdict = t.phase === "verdict";
          const last = i === turns.length - 1;
          return (
            <div key={i} className="flex gap-2.5">
              <AgentAvatar glyph={t.agent.glyph} size={28} />
              <div className="min-w-0 flex-1">
                <div className="mb-1 flex items-center gap-1.5 text-[11px] text-faint">
                  <span className="font-medium" style={{ color: gstyle(t.agent.glyph).color }}>
                    {t.agent.name}
                  </span>
                  <span>· {PHASE[t.phase] ?? t.phase}</span>
                </div>
                <div
                  className={cn(
                    "rounded-2xl rounded-tl-sm border px-4 py-2.5 text-sm leading-relaxed",
                    verdict ? "border-vital/30 bg-vital/5" : "border-border bg-surface-2/50",
                    t.phase === "rebuttal" && "italic",
                  )}
                >
                  {t.text}
                  {last && debating && (
                    <span className="ml-0.5 inline-block h-3.5 w-1.5 animate-pulse bg-fg/50 align-middle" />
                  )}
                </div>
                {t.citations && t.citations.length > 0 && (
                  <div className="mt-1.5 flex flex-wrap gap-1.5">
                    {t.citations.map((c) => (
                      <EvidenceChip key={c} id={c} />
                    ))}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      <div className="border-t border-border p-3">
        <div className="mb-2 flex flex-wrap gap-1.5">
          {suggestions.map((s) => (
            <button
              key={s}
              onClick={() => onStart(s)}
              disabled={debating}
              className="rounded-full border border-border bg-surface px-3 py-1 text-xs text-muted hover:text-fg disabled:opacity-50"
            >
              {s}
            </button>
          ))}
        </div>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            onStart(q);
            setQ("");
          }}
          className="flex items-center gap-2"
        >
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Pose a question to the team…  e.g. should I do cardio or lift tonight?"
            className="flex-1 rounded-xl border border-border bg-surface-2/40 px-4 py-2.5 text-sm outline-none focus:border-vital/50"
          />
          <button
            type="submit"
            disabled={debating || !q.trim()}
            className="inline-flex items-center gap-1.5 rounded-xl bg-gradient-to-r from-vital to-ai px-4 py-2.5 text-sm font-medium text-white transition-transform hover:-translate-y-px disabled:opacity-50"
          >
            <Swords size={15} /> {debating ? "Debating…" : "Debate"}
          </button>
        </form>
      </div>
    </div>
  );
}

type Safety = { passed: boolean; note: string };
type DebateTurn = { agent: AgentCard; phase: string; text: string; citations?: string[] };
type Msg = {
  role: "user" | "assistant";
  text: string;
  agents?: AgentCard[];
  notes?: AgentNote[];
  citations?: string[];
  safety?: Safety;
};

const GREETING =
  "Hi Alex — I'm your LongevityOS care team. Ask about food, exercise, sleep, supplements, or your numbers and the Care Coordinator will route you to the right specialists.";
const START = ["What should I eat tonight?", "Best exercise for me?", "How's my sleep?", "How am I doing overall?"];

export default function CoachPage() {
  const roster = useQuery({ queryKey: ["coach-roster"], queryFn: () => api.coachRoster(), retry: false });
  const meta = useQuery({ queryKey: ["meta"], queryFn: () => api.meta(), retry: false });
  const live = !!meta.data?.run_modes?.agent_live;
  const [messages, setMessages] = useState<Msg[]>([{ role: "assistant", text: GREETING }]);
  const [debateTurns, setDebateTurns] = useState<DebateTurn[]>([]);
  const [debating, setDebating] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>(START);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [mode, setMode] = useState<"chat" | "call" | "debate">("chat");
  const [teamOpen, setTeamOpen] = useState(true);
  const [openNotes, setOpenNotes] = useState<Set<number>>(new Set());
  const [speaking, setSpeaking] = useState(false);
  const [listening, setListening] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const recog = useRef<any>(null);

  const last = [...messages].reverse().find((m) => m.role === "assistant");
  const sttSupported =
    typeof window !== "undefined" &&
    !!((window as any).SpeechRecognition || (window as any).webkitSpeechRecognition);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, busy]);

  function speak(text: string) {
    if (typeof window === "undefined" || !window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.rate = 1.03;
    u.onstart = () => setSpeaking(true);
    u.onend = () => setSpeaking(false);
    window.speechSynthesis.speak(u);
  }

  async function send(text: string) {
    const q = text.trim();
    if (!q || busy) return;
    const history: CoachTurn[] = messages.map((m) => ({ role: m.role, text: m.text }));
    setMessages((m) => [...m, { role: "user", text: q }]);
    setInput("");
    setBusy(true);
    try {
      const r = await api.coach(DEMO_USER, q, history);
      setMessages((m) => [
        ...m,
        { role: "assistant", text: r.reply, agents: r.agents, notes: r.notes, citations: r.citations, safety: r.safety },
      ]);
      setSuggestions(r.suggestions);
      if (mode === "call") speak(r.reply);
    } catch {
      setMessages((m) => [...m, { role: "assistant", text: "I couldn't reach the backend — is it running on :8000?" }]);
    } finally {
      setBusy(false);
    }
  }

  function listen() {
    const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SR) return;
    if (listening) return recog.current?.stop?.();
    const r = new SR();
    r.lang = "en-US";
    r.interimResults = false;
    r.onstart = () => setListening(true);
    r.onend = () => setListening(false);
    r.onresult = (e: any) => send(e.results[0][0].transcript);
    recog.current = r;
    r.start();
  }
  function endCall() {
    setMode("chat");
    window.speechSynthesis?.cancel();
    recog.current?.stop?.();
  }

  async function runDebate(q: string) {
    const m = q.trim();
    if (!m || debating) return;
    setDebateTurns([]);
    setDebating(true);
    try {
      await streamDebate(DEMO_USER, m, (e) => {
        if (e.kind === "turn") {
          setDebateTurns((t) => [...t, { agent: e.agent, phase: e.phase, text: "" }]);
        } else if (e.kind === "token") {
          setDebateTurns((t) => {
            if (!t.length) return t;
            const n = [...t];
            n[n.length - 1] = { ...n[n.length - 1], text: n[n.length - 1].text + e.text };
            return n;
          });
        } else if (e.kind === "end_turn") {
          setDebateTurns((t) => {
            if (!t.length) return t;
            const n = [...t];
            n[n.length - 1] = { ...n[n.length - 1], citations: e.citations };
            return n;
          });
        }
      });
    } catch {
      /* stream ended/aborted */
    } finally {
      setDebating(false);
    }
  }

  const status = listening ? "Listening…" : busy ? "Consulting the team…" : speaking ? "Speaking…" : "Tap the mic and ask";

  return (
    <div>
      <PageHeader
        eyebrow="Your personalized care team"
        title="Coach"
        subtitle="A Care Coordinator routes your question to the right specialists — Nutrition, Movement, Sleep, Biosignals, Labs, Supplements, Experiments — gated by a Safety reviewer. Every answer is grounded in your profile and cites its evidence."
      >
        <div className="inline-flex rounded-lg border border-border bg-surface p-1 text-sm">
          <button
            onClick={() => setMode("chat")}
            className={cn("rounded-md px-3 py-1.5", mode === "chat" ? "bg-surface-2 font-medium" : "text-muted")}
          >
            Chat
          </button>
          <button
            onClick={() => setMode("debate")}
            className={cn(
              "inline-flex items-center gap-1.5 rounded-md px-3 py-1.5",
              mode === "debate" ? "bg-surface-2 font-medium" : "text-muted",
            )}
          >
            <Swords size={14} /> Debate
          </button>
          <button
            onClick={() => {
              setMode("call");
              if (last) speak(last.text);
            }}
            className={cn(
              "inline-flex items-center gap-1.5 rounded-md px-3 py-1.5",
              mode === "call" ? "bg-surface-2 font-medium" : "text-muted",
            )}
          >
            <Phone size={14} /> Voice call
          </button>
        </div>
      </PageHeader>

      {/* care team roster */}
      {roster.data && (
        <div className="mb-5 rounded-2xl border border-border bg-surface p-4 shadow-card">
          <button
            onClick={() => setTeamOpen((o) => !o)}
            className="flex w-full items-center justify-between gap-3"
          >
            <div className="flex items-center gap-2">
              <Users size={15} className="text-vital-soft" />
              <span className="text-sm font-medium">Your care team</span>
              <span className="text-xs text-faint">· {roster.data.agents.length} agents</span>
            </div>
            <div className="flex items-center gap-1.5">
              {!teamOpen && roster.data.agents.map((a) => <AgentAvatar key={a.key} glyph={a.glyph} size={22} />)}
              <ChevronDown size={16} className={cn("text-faint transition-transform", teamOpen && "rotate-180")} />
            </div>
          </button>
          {teamOpen && (
            <div className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {roster.data.agents.map((a) => (
                <div key={a.key} className="flex items-center gap-2.5 rounded-xl border border-border bg-surface-2/40 p-2.5">
                  <AgentAvatar glyph={a.glyph} size={32} />
                  <div className="min-w-0">
                    <div className="flex items-center gap-1.5">
                      <span className="truncate text-sm font-medium">{a.name}</span>
                      {a.role !== "specialist" && (
                        <span className="rounded-full bg-surface-2 px-1.5 py-px text-[10px] capitalize text-faint">
                          {a.role}
                        </span>
                      )}
                    </div>
                    <div className="truncate text-[11px] text-muted">{a.title}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {mode === "chat" ? (
        <div className="flex h-[60vh] flex-col overflow-hidden rounded-2xl border border-border bg-surface shadow-card">
          <div ref={scrollRef} className="flex-1 space-y-4 overflow-y-auto p-5">
            {messages.map((m, i) =>
              m.role === "user" ? (
                <div key={i} className="flex justify-end">
                  <div className="max-w-[80%] rounded-2xl rounded-br-sm bg-gradient-to-r from-vital to-ai px-4 py-2.5 text-sm text-white">
                    {m.text}
                  </div>
                </div>
              ) : (
                <div key={i} className="flex gap-2.5">
                  <AgentAvatar glyph="compass" size={28} />
                  <div className="min-w-0 max-w-[82%]">
                    {/* engaged team */}
                    {m.notes && m.notes.length > 0 && (
                      <div className="mb-1.5 flex flex-wrap items-center gap-1.5 text-[11px] text-faint">
                        <span>Coordinator routed to</span>
                        {m.notes.map((n) => (
                          <span key={n.key} className="inline-flex items-center gap-1" title={n.title}>
                            <AgentAvatar glyph={n.glyph} size={18} />
                            <span className="font-medium" style={{ color: gstyle(n.glyph).color }}>
                              {n.name}
                            </span>
                          </span>
                        ))}
                        {m.safety && !m.safety.passed && (
                          <span className="inline-flex items-center gap-1 rounded-full border border-watch/30 bg-watch/10 px-1.5 py-0.5 text-watch">
                            <ShieldAlert size={11} /> Safety flag
                          </span>
                        )}
                      </div>
                    )}
                    <div className="rounded-2xl rounded-tl-sm border border-border bg-surface-2/50 px-4 py-2.5 text-sm leading-relaxed">
                      {m.text}
                    </div>
                    {m.citations && m.citations.length > 0 && (
                      <div className="mt-1.5 flex flex-wrap gap-1.5">
                        {m.citations.map((c) => (
                          <EvidenceChip key={c} id={c} />
                        ))}
                      </div>
                    )}
                    {m.notes && m.notes.length > 0 && (
                      <>
                        <button
                          onClick={() =>
                            setOpenNotes((s) => {
                              const n = new Set(s);
                              if (n.has(i)) n.delete(i);
                              else n.add(i);
                              return n;
                            })
                          }
                          className="mt-2 inline-flex items-center gap-1 text-[11px] font-medium text-vital-soft hover:text-vital"
                        >
                          {openNotes.has(i) ? "Hide" : `How ${m.notes.length} specialist${m.notes.length > 1 ? "s" : ""} weighed in`}
                          <ChevronDown size={12} className={cn("transition-transform", openNotes.has(i) && "rotate-180")} />
                        </button>
                        {openNotes.has(i) && (
                          <div className="mt-2 space-y-2">
                            {m.notes.map((n) => (
                              <div key={n.key} className="rounded-xl border border-border bg-surface p-3">
                                <div className="flex items-center gap-2">
                                  <AgentAvatar glyph={n.glyph} size={22} />
                                  <span className="text-xs font-medium">{n.name}</span>
                                  <span className="text-[11px] text-faint">· {n.title}</span>
                                </div>
                                <p className="mt-1.5 text-xs leading-relaxed text-muted">{n.text}</p>
                              </div>
                            ))}
                          </div>
                        )}
                      </>
                    )}
                  </div>
                </div>
              ),
            )}
            {busy && (
              <div className="flex items-center gap-2.5 text-xs text-muted">
                <AgentAvatar glyph="compass" size={28} />
                <span className="inline-flex items-center gap-1">
                  Consulting the team
                  {[0, 1, 2].map((d) => (
                    <span key={d} className="h-1 w-1 animate-bounce rounded-full bg-muted" style={{ animationDelay: `${d * 0.15}s` }} />
                  ))}
                </span>
              </div>
            )}
          </div>

          <div className="border-t border-border p-3">
            <div className="mb-2 flex flex-wrap gap-1.5">
              {suggestions.map((s) => (
                <button
                  key={s}
                  onClick={() => send(s)}
                  disabled={busy}
                  className="rounded-full border border-border bg-surface px-3 py-1 text-xs text-muted transition-colors hover:border-vital/40 hover:text-fg disabled:opacity-50"
                >
                  {s}
                </button>
              ))}
            </div>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                send(input);
              }}
              className="flex items-center gap-2"
            >
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask your care team…  e.g. should I eat pasta tonight?"
                className="flex-1 rounded-xl border border-border bg-surface-2/40 px-4 py-2.5 text-sm outline-none focus:border-vital/50"
              />
              <button
                type="submit"
                disabled={busy || !input.trim()}
                className="grid h-10 w-10 place-items-center rounded-xl bg-gradient-to-r from-vital to-ai text-white transition-transform hover:-translate-y-px disabled:opacity-50"
              >
                <Send size={16} />
              </button>
            </form>
          </div>
        </div>
      ) : mode === "debate" ? (
        <DebateView
          turns={debateTurns}
          debating={debating}
          onStart={runDebate}
          suggestions={suggestions}
          live={live}
        />
      ) : (
        /* ── Voice call ── */
        <div className="flex min-h-[58vh] flex-col items-center justify-center gap-7 rounded-2xl border border-border bg-gradient-to-b from-surface to-ai/[0.04] p-8 text-center shadow-card">
          <div className="relative grid h-28 w-28 place-items-center">
            {(speaking || listening || busy) && (
              <>
                <span className="absolute inset-0 animate-ping rounded-full bg-ai/20" />
                <span className="absolute inset-2 animate-pulse rounded-full bg-vital/20" />
              </>
            )}
            <span
              className={cn(
                "relative grid h-20 w-20 place-items-center rounded-full bg-gradient-to-br from-vital to-ai text-white shadow-glow transition-transform",
                (speaking || listening) && "scale-110",
              )}
            >
              <Compass size={30} />
            </span>
          </div>
          <div>
            <div className="font-serif text-2xl font-medium">Care Coordinator</div>
            <div className="mt-1 text-sm text-muted">{status}</div>
          </div>
          {last && <p className="max-w-lg text-sm leading-relaxed text-muted">&ldquo;{last.text}&rdquo;</p>}
          <div className="flex flex-wrap items-center justify-center gap-2">
            {suggestions.slice(0, 3).map((s) => (
              <button
                key={s}
                onClick={() => send(s)}
                disabled={busy}
                className="rounded-full border border-border bg-surface px-3 py-1.5 text-xs text-muted hover:text-fg disabled:opacity-50"
              >
                {s}
              </button>
            ))}
          </div>
          <div className="flex items-center gap-4">
            <button
              onClick={listen}
              disabled={!sttSupported || busy}
              title={sttSupported ? "Speak" : "Voice input not supported in this browser"}
              className={cn(
                "grid h-16 w-16 place-items-center rounded-full text-white shadow-glow transition-transform hover:scale-105 disabled:opacity-40",
                listening ? "animate-pulse bg-risk" : "bg-gradient-to-br from-vital to-ai",
              )}
            >
              <Mic size={24} />
            </button>
            <button onClick={endCall} className="grid h-12 w-12 place-items-center rounded-full bg-surface-2 text-risk hover:bg-risk/10" title="End call">
              <PhoneOff size={18} />
            </button>
          </div>
          {!sttSupported && (
            <p className="text-[11px] text-faint">Mic needs a Chromium/Safari browser. The coach still speaks its replies — or use Chat.</p>
          )}
        </div>
      )}
    </div>
  );
}
