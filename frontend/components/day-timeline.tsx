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

const H = 132; // signal height (px)
const AXIS_H = 18;
const ROW_H = 30; // height of one packed row inside a lane
const MARKER = 22; // icon-marker size
const MERGE = 38; // minutes — same-lane markers closer than this stack into another row

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
  const [scrub, setScrub] = useState(12 * 60 + 50);
  const [playing, setPlaying] = useState(false);
  const plotRef = useRef<HTMLDivElement>(null);
  const raf = useRef(0);
  const lastPlayed = useRef<Ev | null>(null);

  useEffect(() => () => cancelAnimationFrame(raf.current), []);

  // ── signal geometry ──────────────────────────────────────────────
  const { gArea, gLine, hLine } = useMemo(() => {
    const s = day.summary;
    const gMin = s.glucose_min - 6,
      gMax = s.glucose_max + 6;
    const hMin = s.hr_min - 6,
      hMax = s.hr_max + 6;
    const gy = (v: number) => H - 10 - ((v - gMin) / (gMax - gMin)) * (H - 26);
    const hy = (v: number) => H - 10 - ((v - hMin) / (hMax - hMin)) * (H - 40);
    const gl = day.signals.map((p, i) => `${i ? "L" : "M"} ${p.t} ${gy(p.glucose).toFixed(1)}`).join(" ");
    const hl = day.signals.map((p, i) => `${i ? "L" : "M"} ${p.t} ${hy(p.hr).toFixed(1)}`).join(" ");
    return { gArea: `${gl} L 1440 ${H} L 0 ${H} Z`, gLine: gl, hLine: hl };
  }, [day]);

  // ── pack markers into non-overlapping rows per lane ──────────────
  const lanes = useMemo(
    () =>
      LANES.map((_, li) => {
        const evs = events.filter((e) => cat(e.type).lane === li).sort((a, b) => a.startMin - b.startMin);
        const rowLast: number[] = [];
        const placed = evs.map((e) => {
          let r = rowLast.findIndex((last) => e.startMin - last >= MERGE);
          if (r === -1) {
            r = rowLast.length;
            rowLast.push(e.startMin);
          } else {
            rowLast[r] = e.startMin;
          }
          return { e, row: r };
        });
        return { placed, rows: Math.max(1, rowLast.length) };
      }),
    [events],
  );
  const laneHeights = lanes.map((l) => l.rows * ROW_H + 6);
  const laneTops = laneHeights.map((_, i) => laneHeights.slice(0, i).reduce((a, b) => a + b, 0));
  const CONTENT_H = H + laneHeights.reduce((a, b) => a + b, 0);

  const sampleAt = (min: number) => day.signals[clamp(Math.round(min / 10), 0, day.signals.length - 1)];
  const cur = sampleAt(scrub);
  // During replay the detail panel walks through the day with the playhead.
  const playingEvent = playing
    ? events.find((e) => scrub >= e.startMin && scrub < e.startMin + e.durMin)
    : undefined;
  if (playingEvent) lastPlayed.current = playingEvent;
  const sel =
    (playing ? playingEvent ?? lastPlayed.current : events.find((e) => e.id === selected)) ?? null;
  const sleeps = events.filter((e) => e.type === "sleep");

  // ── interaction ─────────────────────────────────────────────────
  function pxWidth() {
    return plotRef.current?.clientWidth ?? 0;
  }
  function dragPill(e: React.PointerEvent, ev: Ev) {
    e.preventDefault();
    e.stopPropagation();
    const startX = e.clientX,
      orig = ev.startMin,
      w = pxWidth();
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
    const el = plotRef.current;
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

  const pct = (min: number) => (min / 1440) * 100;

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
          <button
            onClick={togglePlay}
            className="inline-flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-vital to-ai px-3 py-1.5 font-medium text-white transition-transform hover:-translate-y-px"
          >
            {playing ? <Pause size={13} /> : <Play size={13} />}
            {playing ? "Playing…" : "Replay day"}
          </button>
        </div>
      </div>

      {/* legend (icon markers are decoded here) */}
      <div className="mt-4 flex flex-wrap gap-x-3 gap-y-1.5">
        {Object.entries(CATS).map(([k, c]) => (
          <span key={k} className="inline-flex items-center gap-1 text-[11px] text-muted">
            <span
              className="grid h-4 w-4 place-items-center rounded-full"
              style={{ background: hexA(c.color, 0.15), color: c.color }}
            >
              <c.Icon size={9} />
            </span>
            {c.label}
          </span>
        ))}
      </div>

      {/* track: gutter + plot */}
      <div className="mt-4 flex select-none">
        {/* gutter */}
        <div className="w-24 shrink-0 pr-3 text-right">
          <div style={{ height: H }} className="flex flex-col justify-center gap-2">
            <span className="flex items-center justify-end gap-1.5 text-[11px] font-medium" style={{ color: "#e2581a" }}>
              Glucose <span className="h-2 w-2 rounded-full" style={{ background: "#ff5a1f" }} />
            </span>
            <span className="flex items-center justify-end gap-1.5 text-[11px] font-medium text-ai">
              Heart rate <span className="h-2 w-2 rounded-full bg-ai" />
            </span>
          </div>
          {LANES.map((l, li) => (
            <div
              key={l}
              style={{ height: laneHeights[li] }}
              className="flex items-center justify-end text-[10px] font-medium uppercase leading-tight tracking-wide text-faint"
            >
              {l}
            </div>
          ))}
          <div style={{ height: AXIS_H }} />
        </div>

        {/* plot */}
        <div
          ref={plotRef}
          onPointerDown={dragScrub}
          style={{ touchAction: "none" }}
          className="relative flex-1 cursor-ew-resize"
        >
          {/* background: night + gridlines + lane separators */}
          <div className="pointer-events-none absolute inset-x-0 top-0 z-0" style={{ height: CONTENT_H }}>
            {sleeps.map((e) => (
              <div
                key={e.id}
                className="absolute inset-y-0 bg-ai/[0.05]"
                style={{ left: `${pct(e.startMin)}%`, width: `${pct(e.durMin)}%` }}
              />
            ))}
            {Array.from({ length: 9 }, (_, i) => i * 3).map((h) => (
              <div key={h} className="absolute inset-y-0 w-px bg-border/40" style={{ left: `${(h / 24) * 100}%` }} />
            ))}
            {LANES.map((_, li) => (
              <div
                key={li}
                className="absolute inset-x-0 border-t border-border/40"
                style={{ top: H + laneTops[li] }}
              />
            ))}
          </div>

          {/* signal — reveals left→right with the playhead during Replay */}
          <div
            className={cn("relative z-10", !playing && "day-wipe")}
            style={{ height: H, clipPath: playing ? `inset(0 ${100 - pct(scrub)}% 0 0)` : undefined }}
          >
            <svg viewBox={`0 0 1440 ${H}`} preserveAspectRatio="none" width="100%" height={H} className="block">
              <defs>
                <linearGradient id="gFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#ff5a1f" stopOpacity="0.22" />
                  <stop offset="100%" stopColor="#ff5a1f" stopOpacity="0" />
                </linearGradient>
              </defs>
              <path d={gArea} fill="url(#gFill)" />
              <path d={gLine} fill="none" stroke="#ff5a1f" strokeWidth="2" vectorEffect="non-scaling-stroke" />
              <path d={hLine} fill="none" stroke="#575ecf" strokeWidth="1.75" strokeOpacity="0.85" vectorEffect="non-scaling-stroke" />
            </svg>
          </div>

          {/* lanes + icon markers */}
          <div className="relative z-10">
            {LANES.map((_, li) => (
              <div key={li} className="relative" style={{ height: laneHeights[li] }}>
                {lanes[li].placed.map(({ e, row }) => {
                  const c = cat(e.type);
                  const active = sel?.id === e.id;
                  const future = playing && e.startMin > scrub;
                  return (
                    <button
                      key={e.id}
                      onPointerDown={(ev) => dragPill(ev, e)}
                      aria-label={e.title}
                      title={`${e.title} · ${toHHMM(e.startMin)}–${toHHMM(e.startMin + e.durMin)}`}
                      className={cn(
                        "absolute grid place-items-center rounded-full border transition-all",
                        active ? "z-20" : "z-10 cursor-grab active:cursor-grabbing hover:scale-110",
                      )}
                      style={{
                        left: `${pct(e.startMin)}%`,
                        top: row * ROW_H + (ROW_H - MARKER) / 2,
                        width: MARKER,
                        height: MARKER,
                        background: hexA(c.color, active ? 0.22 : 0.13),
                        borderColor: hexA(c.color, active ? 0.9 : 0.45),
                        color: c.color,
                        opacity: future ? 0.3 : 1,
                        boxShadow: active ? `0 0 0 2px var(--surface), 0 0 0 3px ${c.color}` : undefined,
                      }}
                    >
                      <c.Icon size={12} />
                    </button>
                  );
                })}
              </div>
            ))}
          </div>

          {/* hour axis */}
          <div className="relative" style={{ height: AXIS_H }}>
            {Array.from({ length: 9 }, (_, i) => i * 3).map((h) => (
              <span
                key={h}
                className="absolute top-1 -translate-x-1/2 text-[10px] tabular-nums text-faint"
                style={{ left: `${(h / 24) * 100}%` }}
              >
                {String(h).padStart(2, "0")}:00
              </span>
            ))}
          </div>

          {/* scrubber */}
          <div
            className="pointer-events-none absolute top-0 z-30 w-px bg-fg/40"
            style={{ left: `${pct(scrub)}%`, height: CONTENT_H }}
          >
            <button
              onPointerDown={(e) => {
                e.stopPropagation();
                dragScrub(e);
              }}
              className="pointer-events-auto absolute -left-2 -top-1.5 h-4 w-4 cursor-ew-resize rounded-full border-2 border-fg/50 bg-surface shadow-card"
            />
            <div className="pointer-events-none absolute -top-9 -translate-x-1/2 whitespace-nowrap rounded-lg border border-border bg-surface px-2.5 py-1 text-[10px] shadow-card">
              <span className="font-mono font-medium">{toHHMM(scrub)}</span>
              <span className="ml-2 font-mono" style={{ color: "#e2581a" }}>
                {cur.glucose}
                <span className="text-faint"> mg/dL</span>
              </span>
              <span className="ml-1.5 font-mono text-ai">
                {cur.hr}
                <span className="text-faint"> bpm</span>
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* detail panel */}
      <AnimatePresence mode="wait">
        {sel ? (
          <motion.div
            key={sel.id}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.22 }}
            className="mt-5 grid gap-4 rounded-xl border border-border bg-surface-2/40 p-4 md:grid-cols-[1fr_220px]"
          >
            <div>
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
                <button onClick={() => setSelected(null)} className="text-faint hover:text-fg" aria-label="Close">
                  <X size={16} />
                </button>
              </div>
              <p className="mt-3 text-sm leading-relaxed text-muted">{sel.detail}</p>
              <div className="mt-3 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-vital-soft">
                <HeartPulse size={12} /> Your body&rsquo;s response
              </div>
              <p className="mt-1 text-sm leading-relaxed">{sel.response}</p>
            </div>

            {/* mini response sparkline */}
            <ResponseSpark day={day} ev={sel} />
          </motion.div>
        ) : (
          <motion.div
            key="hint"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="mt-5 rounded-xl border border-dashed border-border-strong bg-surface p-4 text-center text-sm text-muted"
          >
            Click any activity icon to expand its explanation and your body&rsquo;s response.
          </motion.div>
        )}
      </AnimatePresence>

      <p className="mt-3 text-[11px] text-faint">
        Drag an activity icon to reschedule it · drag the scrubber or hit Replay to scan your day ·
        click an icon to expand it.
      </p>
    </div>
  );
}

function ResponseSpark({ day, ev }: { day: DayResponse; ev: Ev }) {
  const a = Math.max(0, ev.startMin - 45);
  const b = Math.min(1440, ev.startMin + ev.durMin + 90);
  const pts = day.signals.filter((s) => s.t >= a && s.t <= b);
  if (pts.length < 2) return <div />;
  const W = 220,
    Hs = 92;
  const xs = (t: number) => ((t - a) / (b - a)) * W;
  const gMin = Math.min(...pts.map((p) => p.glucose)) - 4;
  const gMax = Math.max(...pts.map((p) => p.glucose)) + 4;
  const yy = (v: number) => Hs - 16 - ((v - gMin) / (gMax - gMin)) * (Hs - 28);
  const line = pts.map((p, i) => `${i ? "L" : "M"} ${xs(p.t).toFixed(1)} ${yy(p.glucose).toFixed(1)}`).join(" ");
  const c = cat(ev.type).color;
  return (
    <div className="rounded-lg border border-border bg-surface p-3">
      <div className="text-[10px] font-semibold uppercase tracking-wide text-faint">Glucose around it</div>
      <svg viewBox={`0 0 ${W} ${Hs}`} width="100%" height={Hs} className="mt-1 block">
        <rect
          x={xs(ev.startMin)}
          y={4}
          width={Math.max(2, xs(ev.startMin + ev.durMin) - xs(ev.startMin))}
          height={Hs - 8}
          fill={hexA(c, 0.12)}
          rx={3}
        />
        <path d={`${line} L ${W} ${Hs} L 0 ${Hs} Z`} fill={hexA("#ff5a1f", 0.1)} />
        <path d={line} fill="none" stroke="#ff5a1f" strokeWidth="2" />
      </svg>
      <div className="flex justify-between font-mono text-[10px] text-faint">
        <span>{toHHMM(a)}</span>
        <span className="text-vital-soft">{day.signals[Math.round(ev.startMin / 10)]?.glucose} mg/dL</span>
        <span>{toHHMM(b)}</span>
      </div>
    </div>
  );
}

function Chip({ icon: Icon, label }: { icon: LucideIcon; label: string }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-md border border-border bg-surface-2/50 px-2 py-1 text-muted">
      <Icon size={12} />
      {label}
    </span>
  );
}
