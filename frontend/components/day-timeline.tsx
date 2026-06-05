"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import type { DayResponse } from "@/lib/types";
import { cn } from "@/lib/utils";
import {
  Brain,
  Coffee,
  Droplet,
  Dumbbell,
  Footprints,
  HeartPulse,
  Moon,
  Pause,
  Pill,
  Play,
  Sun,
  Utensils,
  X,
  type LucideIcon,
} from "lucide-react";

type Cat = { color: string; Icon: LucideIcon; lane: number; label: string };

const CATS: Record<string, Cat> = {
  sleep: { color: "#575ecf", Icon: Moon, lane: 0, label: "Sleep" },
  behavior: { color: "#8b8577", Icon: Brain, lane: 0, label: "Wind-down" },
  meal: { color: "#ff5a1f", Icon: Utensils, lane: 1, label: "Meal" },
  caffeine: { color: "#c77d1a", Icon: Coffee, lane: 1, label: "Caffeine" },
  supplement: { color: "#4e8c6a", Icon: Pill, lane: 1, label: "Supplement" },
  exercise: { color: "#dc4a2b", Icon: Dumbbell, lane: 2, label: "Exercise" },
  activity: { color: "#2f9e8f", Icon: Footprints, lane: 2, label: "Activity" },
  light: { color: "#d99a2b", Icon: Sun, lane: 3, label: "Light" },
};
const LANES = ["Sleep & recovery", "Fuel", "Movement", "Light & context"];

const cat = (t: string): Cat => CATS[t] ?? { color: "#8b8577", Icon: Brain, lane: 3, label: t };
const toMin = (s: string) => {
  const [h, m] = s.split(":").map(Number);
  return h * 60 + m;
};
const toHHMM = (min: number) => {
  const m = ((min % 1440) + 1440) % 1440;
  return `${String(Math.floor(m / 60)).padStart(2, "0")}:${String(Math.round(m % 60)).padStart(2, "0")}`;
};
const clamp = (v: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, v));
const hexA = (hex: string, a: number) => {
  const n = parseInt(hex.slice(1), 16);
  return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${a})`;
};

type Ev = DayResponse["events"][number] & { startMin: number; durMin: number };

export function DayTimeline({ day }: { day: DayResponse }) {
  const [events, setEvents] = useState<Ev[]>(() =>
    day.events.map((e) => {
      const s = toMin(e.start);
      return { ...e, startMin: s, durMin: Math.max(15, toMin(e.end) - s) };
    }),
  );
  const [selected, setSelected] = useState<string | null>("EV-10");
  const [scrub, setScrub] = useState(13 * 60 + 30);
  const [playing, setPlaying] = useState(false);
  const [w, setW] = useState(0);
  const trackRef = useRef<HTMLDivElement>(null);
  const raf = useRef(0);

  useEffect(() => {
    const el = trackRef.current;
    if (!el) return;
    const ro = new ResizeObserver(() => setW(el.clientWidth));
    ro.observe(el);
    setW(el.clientWidth);
    return () => ro.disconnect();
  }, []);
  useEffect(() => () => cancelAnimationFrame(raf.current), []);

  // ── signal geometry ──────────────────────────────────────────────
  const H = 120;
  const { gArea, gLine, hLine, gy, hy } = useMemo(() => {
    const s = day.summary;
    const gMin = s.glucose_min - 6,
      gMax = s.glucose_max + 6;
    const hMin = s.hr_min - 6,
      hMax = s.hr_max + 6;
    const gy = (v: number) => H - 8 - ((v - gMin) / (gMax - gMin)) * (H - 30);
    const hy = (v: number) => H - 8 - ((v - hMin) / (hMax - hMin)) * (H - 44);
    const gl = day.signals.map((p, i) => `${i ? "L" : "M"} ${p.t} ${gy(p.glucose).toFixed(1)}`).join(" ");
    const hl = day.signals.map((p, i) => `${i ? "L" : "M"} ${p.t} ${hy(p.hr).toFixed(1)}`).join(" ");
    return { gArea: `${gl} L 1440 ${H} L 0 ${H} Z`, gLine: gl, hLine: hl, gy, hy };
  }, [day]);

  const sampleAt = (min: number) => day.signals[clamp(Math.round(min / 10), 0, day.signals.length - 1)];
  const cur = sampleAt(scrub);
  const sel = events.find((e) => e.id === selected) ?? null;

  // ── dragging ─────────────────────────────────────────────────────
  function dragPill(e: React.PointerEvent, ev: Ev) {
    e.preventDefault();
    const startX = e.clientX,
      orig = ev.startMin;
    let moved = false;
    const move = (me: PointerEvent) => {
      const dx = me.clientX - startX;
      if (Math.abs(dx) > 3) moved = true;
      if (!w) return;
      const ns = clamp(orig + Math.round((dx / w) * 1440), 0, 1440 - ev.durMin);
      setEvents((prev) => prev.map((p) => (p.id === ev.id ? { ...p, startMin: ns } : p)));
    };
    const up = () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
      if (!moved) setSelected(ev.id);
      else
        setEvents((prev) =>
          prev.map((p) => (p.id === ev.id ? { ...p, startMin: Math.round(p.startMin / 15) * 15 } : p)),
        );
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
  }

  function scrubFrom(clientX: number) {
    const el = trackRef.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    setScrub(clamp(Math.round(((clientX - r.left) / r.width) * 1440), 0, 1440));
  }
  function dragScrub(e: React.PointerEvent) {
    e.preventDefault();
    scrubFrom(e.clientX);
    const move = (me: PointerEvent) => scrubFrom(me.clientX);
    const up = () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
  }

  function togglePlay() {
    if (playing) {
      cancelAnimationFrame(raf.current);
      setPlaying(false);
      return;
    }
    setPlaying(true);
    setScrub(0);
    const start = performance.now();
    const tick = (now: number) => {
      const p = Math.min(1, (now - start) / 7000);
      setScrub(Math.round(p * 1440));
      if (p < 1) raf.current = requestAnimationFrame(tick);
      else setPlaying(false);
    };
    raf.current = requestAnimationFrame(tick);
  }

  const scrubPct = (scrub / 1440) * 100;

  return (
    <div className="rounded-2xl border border-border bg-surface p-5 shadow-card sm:p-6">
      {/* header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-faint">
            Your day · auto-synced
          </div>
          <h3 className="mt-0.5 font-serif text-xl font-medium">{day.date}</h3>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <Chip icon={Utensils} label={`${day.summary.meals} meals`} />
          <Chip icon={Dumbbell} label={`${day.summary.workouts} workout`} />
          <Chip icon={Droplet} label={`${day.summary.glucose_min}–${day.summary.glucose_max} mg/dL`} color="#ff5a1f" />
          <Chip icon={HeartPulse} label={`${day.summary.hr_min}–${day.summary.hr_max} bpm`} color="#575ecf" />
          <button
            onClick={togglePlay}
            className="inline-flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-vital to-ai px-3 py-1.5 font-medium text-white transition-all hover:-translate-y-px"
          >
            {playing ? <Pause size={13} /> : <Play size={13} />}
            {playing ? "Playing" : "Replay day"}
          </button>
        </div>
      </div>

      {/* legend */}
      <div className="mt-4 flex flex-wrap gap-x-3 gap-y-1.5">
        {Object.entries(CATS).map(([k, c]) => (
          <span key={k} className="inline-flex items-center gap-1 text-[11px] text-muted">
            <span className="h-2 w-2 rounded-full" style={{ background: c.color }} />
            {c.label}
          </span>
        ))}
      </div>

      {/* track */}
      <div className="mt-4 select-none">
        <div ref={trackRef} className="relative" onPointerDown={dragScrub} style={{ touchAction: "none" }}>
          {/* signal */}
          <div className="day-wipe">
            <svg viewBox={`0 0 1440 ${H}`} preserveAspectRatio="none" width="100%" height={H} className="block">
              <defs>
                <linearGradient id="gFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#ff5a1f" stopOpacity="0.20" />
                  <stop offset="100%" stopColor="#ff5a1f" stopOpacity="0" />
                </linearGradient>
              </defs>
              <path d={gArea} fill="url(#gFill)" />
              <path d={gLine} fill="none" stroke="#ff5a1f" strokeWidth="2" vectorEffect="non-scaling-stroke" />
              <path d={hLine} fill="none" stroke="#575ecf" strokeWidth="1.5" strokeOpacity="0.8" vectorEffect="non-scaling-stroke" />
            </svg>
          </div>

          {/* lanes */}
          <div className="relative mt-1">
            {LANES.map((laneLabel, li) => (
              <div key={laneLabel} className="relative h-11 border-t border-border/50 first:border-t-0">
                <span className="pointer-events-none absolute left-1 top-1 z-0 text-[10px] uppercase tracking-wide text-faint/70">
                  {laneLabel}
                </span>
                {events
                  .filter((e) => cat(e.type).lane === li)
                  .map((e) => {
                    const c = cat(e.type);
                    const left = (e.startMin / 1440) * 100;
                    const width = (e.durMin / 1440) * 100;
                    const active = selected === e.id;
                    return (
                      <button
                        key={e.id}
                        onPointerDown={(ev) => dragPill(ev, e)}
                        title={`${e.title} · drag to move`}
                        className={cn(
                          "group absolute top-1.5 flex h-8 cursor-grab items-center gap-1 overflow-hidden rounded-lg border px-1.5 text-left text-[11px] active:cursor-grabbing",
                          active ? "z-20" : "z-10",
                        )}
                        style={{
                          left: `${left}%`,
                          width: `${width}%`,
                          minWidth: "1.9rem",
                          background: hexA(c.color, active ? 0.2 : 0.12),
                          borderColor: hexA(c.color, active ? 0.9 : 0.4),
                          color: c.color,
                          boxShadow: active ? `0 0 0 2px var(--surface), 0 0 0 4px ${c.color}` : undefined,
                        }}
                      >
                        <c.Icon size={13} className="shrink-0" />
                        <span className="truncate font-medium">{e.title}</span>
                      </button>
                    );
                  })}
              </div>
            ))}
          </div>

          {/* hour axis */}
          <div className="relative mt-1 h-4">
            {Array.from({ length: 9 }, (_, i) => i * 3).map((h) => (
              <span
                key={h}
                className="absolute -translate-x-1/2 text-[10px] tabular-nums text-faint"
                style={{ left: `${(h / 24) * 100}%` }}
              >
                {String(h).padStart(2, "0")}:00
              </span>
            ))}
          </div>

          {/* scrubber */}
          <div
            className="pointer-events-none absolute inset-y-0 z-30 w-px bg-fg/40"
            style={{ left: `${scrubPct}%` }}
          >
            <div
              onPointerDown={(e) => {
                e.stopPropagation();
                dragScrub(e);
              }}
              className="pointer-events-auto absolute -left-2 -top-1 h-4 w-4 cursor-ew-resize rounded-full border-2 border-fg/60 bg-surface"
            />
            <div className="pointer-events-none absolute -top-7 -translate-x-1/2 whitespace-nowrap rounded-md border border-border bg-surface px-2 py-0.5 text-[10px] shadow-card">
              <span className="font-mono">{toHHMM(scrub)}</span>
              <span className="ml-1.5 font-mono text-vital-soft">{cur.glucose}</span>
              <span className="ml-1 font-mono text-ai">{cur.hr}♥</span>
            </div>
          </div>
        </div>
      </div>

      {/* detail panel */}
      <AnimatePresence mode="wait">
        {sel && (
          <motion.div
            key={sel.id}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.22 }}
            className="mt-5 rounded-xl border border-border bg-surface-2/40 p-4"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-center gap-2.5">
                <span
                  className="grid h-9 w-9 place-items-center rounded-lg"
                  style={{ background: hexA(cat(sel.type).color, 0.15), color: cat(sel.type).color }}
                >
                  {(() => {
                    const I = cat(sel.type).Icon;
                    return <I size={18} />;
                  })()}
                </span>
                <div>
                  <h4 className="font-medium leading-tight">{sel.title}</h4>
                  <div className="font-mono text-[11px] text-faint">
                    {toHHMM(sel.startMin)}–{toHHMM(sel.startMin + sel.durMin)} · {cat(sel.type).label}
                  </div>
                </div>
              </div>
              <button onClick={() => setSelected(null)} className="text-faint hover:text-fg">
                <X size={16} />
              </button>
            </div>
            <p className="mt-3 text-sm leading-relaxed text-muted">{sel.detail}</p>
            <div className="mt-3 rounded-lg border border-border bg-surface p-3">
              <div className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-vital-soft">
                <HeartPulse size={12} /> Your body&rsquo;s response
              </div>
              <p className="mt-1 text-sm leading-relaxed">{sel.response}</p>
              <div className="mt-2 flex gap-4 text-xs text-muted">
                <span className="font-mono">
                  <span className="text-vital-soft">glucose</span> {sampleAt(sel.startMin).glucose} mg/dL
                </span>
                <span className="font-mono">
                  <span className="text-ai">HR</span> {sampleAt(sel.startMin).hr} bpm
                </span>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <p className="mt-3 text-[11px] text-faint">
        Drag any activity to reschedule it · drag the scrubber or hit Replay to scan your day · click
        an activity for its body response.
      </p>
    </div>
  );
}

function Chip({ icon: Icon, label, color }: { icon: LucideIcon; label: string; color?: string }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-md border border-border bg-surface-2/50 px-2 py-1 text-muted">
      <Icon size={12} style={color ? { color } : undefined} />
      {label}
    </span>
  );
}
