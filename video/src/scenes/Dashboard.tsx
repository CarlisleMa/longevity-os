import React from "react";
import { useCurrentFrame, interpolate } from "remotion";
import { colors } from "../theme";
import { Card, Eyebrow, Chip } from "../components/ui";
import { Rise, useCountUp, useSweep, useStamp } from "../lib/anim";

// ── System radar ──
const AXES = [
  { label: "Cardiac", v: 0.82 },
  { label: "Metabolic", v: 0.58 },
  { label: "Retinal", v: 0.78 },
  { label: "Autonomic", v: 0.66 },
  { label: "Inflammatory", v: 0.72 },
  { label: "Renal", v: 0.8 },
];
const Radar: React.FC = () => {
  const sweep = useSweep(14, 30);
  const cx = 200;
  const cy = 185;
  const R = 140;
  const pt = (i: number, r: number) => {
    const a = (Math.PI * 2 * i) / AXES.length - Math.PI / 2;
    return [cx + Math.cos(a) * r, cy + Math.sin(a) * r];
  };
  const poly = AXES.map((ax, i) => pt(i, R * ax.v * sweep).join(",")).join(" ");
  return (
    <svg width={400} height={380}>
      {[0.25, 0.5, 0.75, 1].map((g) => (
        <polygon
          key={g}
          points={AXES.map((_, i) => pt(i, R * g).join(",")).join(" ")}
          fill="none"
          stroke={colors.border}
          strokeWidth={1}
        />
      ))}
      {AXES.map((_, i) => {
        const [x, y] = pt(i, R);
        return <line key={i} x1={cx} y1={cy} x2={x} y2={y} stroke={colors.border} strokeWidth={1} />;
      })}
      <polygon points={poly} fill="rgba(255,90,31,0.16)" stroke={colors.vital} strokeWidth={2.5} />
      {AXES.map((ax, i) => {
        const [x, y] = pt(i, R + 30);
        return (
          <text key={ax.label} x={x} y={y} fontSize={19} fill={colors.muted} textAnchor="middle" dominantBaseline="middle" fontFamily="var(--font-sans)">
            {ax.label}
          </text>
        );
      })}
    </svg>
  );
};

// ── Coupling dual-line (glucose vs HR, blunted post-meal) ──
const Coupling: React.FC = () => {
  const sweep = useSweep(20, 36);
  const W = 380;
  const H = 120;
  const mk = (fn: (t: number) => number) => {
    const pts: string[] = [];
    const n = 60;
    for (let k = 0; k <= n; k++) pts.push(`${(k / n) * W},${fn(k / n)}`);
    const vis = Math.floor(pts.length * sweep);
    return pts.slice(0, vis).join(" ");
  };
  const glucose = (t: number) => H - 18 - 70 * Math.exp(-Math.pow((t - 0.42) / 0.16, 2));
  const hr = (t: number) => H - 14 - 28 * Math.exp(-Math.pow((t - 0.5) / 0.2, 2)); // blunted/lagged
  return (
    <svg width={W} height={H} style={{ overflow: "visible" }}>
      <line x1={0} y1={H - 14} x2={W} y2={H - 14} stroke={colors.border} />
      <polyline points={mk(glucose)} fill="none" stroke={colors.vital} strokeWidth={2.6} />
      <polyline points={mk(hr)} fill="none" stroke={colors.coral} strokeWidth={2.6} strokeDasharray="2 4" />
      <text x={W * 0.42} y={18} fontSize={16} fill={colors.vitalSoft} textAnchor="middle">meal ↑ glucose</text>
    </svg>
  );
};

export const Dashboard: React.FC = () => {
  const frame = useCurrentFrame();
  const bio = useCountUp(44.7, { delay: 8, duration: 30, decimals: 1 });
  const stamp = useStamp(34);
  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", gap: 18 }}>
      <Rise delay={2}>
        <h2 style={{ fontFamily: "var(--font-serif)", fontSize: 54, fontWeight: 600, margin: 0 }}>Your dashboard</h2>
      </Rise>
      <div style={{ display: "flex", gap: 24, flex: 1 }}>
        {/* scorecard */}
        <Rise delay={6} style={{ flex: 1 }}>
          <Card pad={32} style={{ height: "100%" }}>
            <Eyebrow>Biological age</Eyebrow>
            <div style={{ display: "flex", alignItems: "baseline", gap: 16, marginTop: 10 }}>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: 104, fontWeight: 600, lineHeight: 1 }}>{bio}</span>
              <span style={{ fontSize: 26, color: colors.muted }}>vs 47 chronological</span>
            </div>
            <div style={{ display: "flex", gap: 12, marginTop: 20, ...stamp }}>
              <Chip tone="good">−2.3 yrs younger</Chip>
              <Chip tone="neutral" style={{ fontSize: 19 }}>↓ 0.4 vs your baseline</Chip>
            </div>
            <div style={{ marginTop: 30 }}>
              <Eyebrow>Your trajectory (N-of-1)</Eyebrow>
              <Trajectory />
            </div>
          </Card>
        </Rise>

        {/* radar + coupling */}
        <div style={{ flex: 1.25, display: "flex", flexDirection: "column", gap: 18 }}>
          <Rise delay={12} style={{ flex: 1 }}>
            <Card pad={20} style={{ height: "100%", display: "flex", alignItems: "center", justifyContent: "center", position: "relative" }}>
              <div style={{ position: "absolute", top: 22, left: 26 }}>
                <Eyebrow>System radar</Eyebrow>
              </div>
              <Radar />
            </Card>
          </Rise>
          <Rise delay={20} style={{ flex: 0.85 }}>
            <Card pad={24} style={{ height: "100%" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                <Eyebrow>Glucose–HR coupling</Eyebrow>
                <Chip tone="watch" style={{ fontSize: 18 }}>blunted post-meal · −15% vs baseline</Chip>
              </div>
              <div style={{ marginTop: 12, display: "flex", justifyContent: "center" }}>
                <Coupling />
              </div>
            </Card>
          </Rise>
        </div>
      </div>
    </div>
  );
};

const Trajectory: React.FC = () => {
  const sweep = useSweep(18, 36);
  const W = 460;
  const H = 90;
  const vals = [46.2, 45.8, 45.5, 45.1, 44.9, 44.7];
  const min = 44.4;
  const max = 46.5;
  const pts = vals.map((v, i) => {
    const x = (i / (vals.length - 1)) * W;
    const y = H - ((v - min) / (max - min)) * (H - 16) - 8;
    return [x, y];
  });
  const vis = Math.max(2, Math.floor(pts.length * sweep));
  return (
    <svg width={W} height={H} style={{ marginTop: 8, overflow: "visible" }}>
      <polyline points={pts.slice(0, vis).map((p) => p.join(",")).join(" ")} fill="none" stroke={colors.good} strokeWidth={3} strokeLinejoin="round" />
      {pts.slice(0, vis).map(([x, y], i) => (
        <circle key={i} cx={x} cy={y} r={4} fill={colors.good} />
      ))}
      <text x={0} y={H + 2} fontSize={15} fill={colors.faint} fontFamily="var(--font-mono)">3 mo ago</text>
      <text x={W} y={H + 2} fontSize={15} fill={colors.faint} textAnchor="end" fontFamily="var(--font-mono)">now</text>
    </svg>
  );
};
