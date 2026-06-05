import React from "react";
import { useCurrentFrame, interpolate, random } from "remotion";
import { colors } from "../theme";
import { Card, Eyebrow, Chip } from "../components/ui";
import { Rise, useCountUp, useSweep } from "../lib/anim";

const modalities: { name: string; cov: number; tone: string }[] = [
  { name: "Clinical labs (OMOP)", cov: 100, tone: colors.ink },
  { name: "12-lead ECG", cov: 98.7, tone: colors.coral },
  { name: "Retinal OCT", cov: 99.4, tone: colors.ai },
  { name: "Retinal OCTA", cov: 99.3, tone: colors.ai },
  { name: "Retinal photo", cov: 99.8, tone: colors.ai },
  { name: "Retinal FLIO", cov: 81.0, tone: colors.ai },
  { name: "Wearable (Garmin)", cov: 95.8, tone: colors.good },
  { name: "CGM (Dexcom)", cov: 98.5, tone: colors.vital },
  { name: "Environment", cov: 97.9, tone: colors.sage },
];

const Stat: React.FC<{ value: string; label: string; delay: number }> = ({ value, label, delay }) => (
  <Rise delay={delay} style={{ flex: 1 }}>
    <div style={{ fontFamily: "var(--font-mono)", fontSize: 58, fontWeight: 600, lineHeight: 1 }}>{value}</div>
    <div style={{ fontSize: 22, color: colors.muted, marginTop: 8 }}>{label}</div>
  </Rise>
);

// A tiny synchronized multi-stream strip (CGM / HR / activity / light).
const SyncStreams: React.FC = () => {
  const sweep = useSweep(20, 50);
  const W = 600;
  const rows = [
    { label: "CGM", color: colors.vital, freq: 2.1, amp: 16 },
    { label: "Heart rate", color: colors.coral, freq: 3.4, amp: 12 },
    { label: "Activity", color: colors.good, freq: 5.0, amp: 14 },
    { label: "Light / env", color: colors.sage, freq: 1.6, amp: 18 },
  ];
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {rows.map((r, i) => {
        const pts: string[] = [];
        const n = 80;
        for (let k = 0; k <= n; k++) {
          const x = (k / n) * W;
          const seedy = random(`${r.label}-${k}`) * r.amp * 0.5;
          const y = 34 + Math.sin((k / n) * Math.PI * 2 * r.freq) * r.amp + seedy - r.amp * 0.25;
          pts.push(`${x},${y}`);
        }
        const visible = Math.floor(pts.length * sweep);
        return (
          <div key={r.label} style={{ display: "flex", alignItems: "center", gap: 16 }}>
            <div style={{ width: 120, fontSize: 19, color: colors.muted, textAlign: "right", fontFamily: "var(--font-mono)" }}>
              {r.label}
            </div>
            <svg width={W} height={68} style={{ overflow: "visible" }}>
              <line x1={0} y1={34} x2={W} y2={34} stroke={colors.border} strokeWidth={1} />
              <polyline
                points={pts.slice(0, visible).join(" ")}
                fill="none"
                stroke={r.color}
                strokeWidth={2.5}
                strokeLinejoin="round"
                opacity={0.9}
              />
            </svg>
          </div>
        );
      })}
      <div style={{ display: "flex", alignItems: "center", gap: 16, marginTop: 2 }}>
        <div style={{ width: 120 }} />
        <div style={{ width: W, display: "flex", justifyContent: "space-between", fontSize: 17, color: colors.faint, fontFamily: "var(--font-mono)" }}>
          <span>↑ clinical visit (day 1)</span>
          <span>~10-day synchronized window →</span>
        </div>
      </div>
    </div>
  );
};

export const Dataset: React.FC = () => {
  const frame = useCurrentFrame();
  const n = useCountUp(2280, { delay: 8, duration: 36 });
  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", gap: 26 }}>
      <Rise delay={2}>
        <div style={{ display: "flex", alignItems: "baseline", gap: 22, flexWrap: "wrap" }}>
          <h2 style={{ fontFamily: "var(--font-serif)", fontSize: 64, fontWeight: 600, margin: 0, letterSpacing: "-0.01em" }}>
            The data: <span style={{ color: colors.ai }}>AI-READI</span>
          </h2>
          <Chip tone="ai">NIH Bridge2AI flagship cohort</Chip>
        </div>
      </Rise>
      <Rise delay={5}>
        <div style={{ fontSize: 24, color: colors.muted, marginTop: -10 }}>
          Artificial Intelligence Ready and Exploratory Atlas for Diabetes Insights · v3.0.0
        </div>
      </Rise>

      {/* stat row */}
      <Card pad={30}>
        <div style={{ display: "flex", gap: 30 }}>
          <Stat value={Number(n).toLocaleString()} label="participants" delay={8} />
          <Stat value="3" label="clinical sites (UW · UAB · UCSD)" delay={12} />
          <Stat value="9" label="synchronized modalities" delay={16} />
          <Stat value="~4 TB" label="densely aligned physiology" delay={20} />
        </div>
        {/* diabetes spectrum bar */}
        <div style={{ marginTop: 26 }}>
          <Eyebrow>Spectrum: healthy → insulin-dependent</Eyebrow>
          <div style={{ display: "flex", gap: 6, marginTop: 10, height: 18, borderRadius: 999, overflow: "hidden" }}>
            {[
              [34, colors.good],
              [24.6, colors.sage],
              [30.1, colors.watch],
              [11.3, colors.risk],
            ].map(([pct, c], i) => (
              <div
                key={i}
                style={{
                  width: `${interpolate(frame, [24 + i * 4, 36 + i * 4], [0, pct as number], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })}%`,
                  background: c as string,
                }}
              />
            ))}
          </div>
        </div>
      </Card>

      {/* modality grid + sync streams */}
      <div style={{ display: "flex", gap: 26, flex: 1 }}>
        <Rise delay={24} style={{ flex: 0.95 }}>
          <Card pad={26} style={{ height: "100%" }}>
            <Eyebrow>Per person · 9 modalities</Eyebrow>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 14, marginTop: 16 }}>
              {modalities.map((m, i) => (
                <div
                  key={m.name}
                  style={{
                    opacity: interpolate(frame, [28 + i * 3, 38 + i * 3], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 19, fontWeight: 500 }}>
                    <span style={{ width: 9, height: 9, borderRadius: 999, background: m.tone }} />
                    {m.name}
                  </div>
                  <div style={{ height: 6, background: colors.surface2, borderRadius: 999, marginTop: 7, overflow: "hidden" }}>
                    <div style={{ width: `${m.cov}%`, height: "100%", background: m.tone, opacity: 0.6 }} />
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </Rise>
        <Rise delay={28} style={{ flex: 1.05 }}>
          <Card pad={26} style={{ height: "100%" }}>
            <Eyebrow>~10-day synchronized streams (every 5 min – 5 sec)</Eyebrow>
            <div style={{ marginTop: 18 }}>
              <SyncStreams />
            </div>
          </Card>
        </Rise>
      </div>
    </div>
  );
};
