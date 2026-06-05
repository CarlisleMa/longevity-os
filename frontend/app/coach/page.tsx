"use client";

import { useEffect, useRef, useState } from "react";
import { api, DEMO_USER } from "@/lib/api";
import type { CoachTurn } from "@/lib/types";
import { PageHeader } from "@/components/page-header";
import { EvidenceChip } from "@/components/evidence-chip";
import { cn } from "@/lib/utils";
import { Mic, Phone, PhoneOff, Search, Send, Sparkles } from "lucide-react";

type Msg = { role: "user" | "assistant"; text: string; citations?: string[]; checked?: string[] };

const GREETING =
  "Hi Alex — I'm your LongevityOS coach. I can see your full health profile and everything you've logged today. Ask me about food, exercise, sleep, or your numbers.";
const START = ["What should I eat tonight?", "Best exercise for me?", "How's my sleep?", "How am I doing overall?"];

export default function CoachPage() {
  const [messages, setMessages] = useState<Msg[]>([{ role: "assistant", text: GREETING }]);
  const [suggestions, setSuggestions] = useState<string[]>(START);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [mode, setMode] = useState<"chat" | "call">("chat");
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
        { role: "assistant", text: r.reply, citations: r.citations, checked: r.checked },
      ]);
      setSuggestions(r.suggestions);
      if (mode === "call") speak(r.reply);
    } catch {
      setMessages((m) => [
        ...m,
        { role: "assistant", text: "I couldn't reach the backend just now — is it running on :8000?" },
      ]);
    } finally {
      setBusy(false);
    }
  }

  function listen() {
    const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SR) return;
    if (listening) {
      recog.current?.stop?.();
      return;
    }
    const r = new SR();
    r.lang = "en-US";
    r.interimResults = false;
    r.onstart = () => setListening(true);
    r.onend = () => setListening(false);
    r.onresult = (e: any) => send(e.results[0][0].transcript);
    recog.current = r;
    r.start();
  }

  function enterCall() {
    setMode("call");
    if (last) speak(last.text);
  }
  function endCall() {
    setMode("chat");
    window.speechSynthesis?.cancel();
    recog.current?.stop?.();
  }

  const status = listening ? "Listening…" : busy ? "Thinking…" : speaking ? "Speaking…" : "Tap the mic and ask";

  return (
    <div>
      <PageHeader
        eyebrow="Grounded in your data"
        title="Coach"
        subtitle="Ask about food, exercise, sleep, or supplements — the coach reads your profile and today's activities before answering, and cites the research behind each read."
      >
        <div className="inline-flex rounded-lg border border-border bg-surface p-1 text-sm">
          <button
            onClick={() => setMode("chat")}
            className={cn("rounded-md px-3 py-1.5", mode === "chat" ? "bg-surface-2 font-medium" : "text-muted")}
          >
            Chat
          </button>
          <button
            onClick={enterCall}
            className={cn(
              "inline-flex items-center gap-1.5 rounded-md px-3 py-1.5",
              mode === "call" ? "bg-surface-2 font-medium" : "text-muted",
            )}
          >
            <Phone size={14} /> Voice call
          </button>
        </div>
      </PageHeader>

      {mode === "chat" ? (
        <div className="flex h-[62vh] flex-col overflow-hidden rounded-2xl border border-border bg-surface shadow-card">
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
                  <span className="mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-lg bg-gradient-to-br from-vital to-ai text-white">
                    <Sparkles size={14} />
                  </span>
                  <div className="max-w-[80%]">
                    {m.checked && (
                      <div className="mb-1 inline-flex items-center gap-1 text-[11px] text-faint">
                        <Search size={10} /> Checked: {m.checked.join(" · ")}
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
                  </div>
                </div>
              ),
            )}
            {busy && (
              <div className="flex gap-2.5">
                <span className="mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-lg bg-gradient-to-br from-vital to-ai text-white">
                  <Sparkles size={14} />
                </span>
                <div className="flex items-center gap-1 rounded-2xl rounded-tl-sm border border-border bg-surface-2/50 px-4 py-3">
                  {[0, 1, 2].map((d) => (
                    <span
                      key={d}
                      className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted"
                      style={{ animationDelay: `${d * 0.15}s` }}
                    />
                  ))}
                </div>
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
                placeholder="Ask your coach…  e.g. should I eat pasta tonight?"
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
      ) : (
        /* ── Voice call ── */
        <div className="flex min-h-[62vh] flex-col items-center justify-center gap-7 rounded-2xl border border-border bg-gradient-to-b from-surface to-ai/[0.04] p-8 text-center shadow-card">
          <Orb active={speaking || listening} busy={busy} />
          <div>
            <div className="font-serif text-2xl font-medium">LongevityOS Coach</div>
            <div className="mt-1 text-sm text-muted">{status}</div>
          </div>
          {last && (
            <p className="max-w-lg text-sm leading-relaxed text-muted">&ldquo;{last.text}&rdquo;</p>
          )}

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
              title={sttSupported ? "Hold a thought and speak" : "Voice input not supported in this browser"}
              className={cn(
                "grid h-16 w-16 place-items-center rounded-full text-white shadow-glow transition-transform hover:scale-105 disabled:opacity-40",
                listening ? "bg-risk animate-pulse" : "bg-gradient-to-br from-vital to-ai",
              )}
            >
              <Mic size={24} />
            </button>
            <button
              onClick={endCall}
              className="grid h-12 w-12 place-items-center rounded-full bg-surface-2 text-risk hover:bg-risk/10"
              title="End call"
            >
              <PhoneOff size={18} />
            </button>
          </div>
          {!sttSupported && (
            <p className="text-[11px] text-faint">
              Mic input needs a Chromium/Safari browser. The coach still speaks its replies — or use
              Chat to type.
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function Orb({ active, busy }: { active: boolean; busy: boolean }) {
  return (
    <div className="relative grid h-28 w-28 place-items-center">
      {(active || busy) && (
        <>
          <span className="absolute inset-0 animate-ping rounded-full bg-ai/20" />
          <span className="absolute inset-2 animate-pulse rounded-full bg-vital/20" />
        </>
      )}
      <span
        className={cn(
          "relative grid h-20 w-20 place-items-center rounded-full bg-gradient-to-br from-vital to-ai text-white shadow-glow transition-transform",
          active && "scale-110",
        )}
      >
        <Sparkles size={30} />
      </span>
    </div>
  );
}
