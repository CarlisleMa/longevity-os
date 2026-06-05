import React from "react";
import { useCurrentFrame, interpolate, spring, useVideoConfig } from "remotion";
import { colors } from "../theme";
import { Card, Eyebrow, Chip } from "../components/ui";
import { Rise } from "../lib/anim";

// Test JEPA loss (lower = more predictable). Aligned must beat the controls.
const HORIZONS = [
  { h: "0m", aligned: 3.196, wrong: 4.076, shuffle: 4.436 },
  { h: "30m", aligned: 3.458, wrong: 4.102, shuffle: 4.429 },
  { h: "60m", aligned: 3.639, wrong: 4.153, shuffle: 4.430 },
  { h: "120m", aligned: 3.840, wrong: 4.204, shuffle: 4.434 },
];
const LO = 2.9;
const HI = 4.6;
const CHART_H = 205;

const Bar: React.FC<{ value: number; color: string; delay: number; label: string }> = ({ value, color, delay, label }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const grow = spring({ frame: frame - delay, fps, config: { damping: 200, stiffness: 120 } });
  const full = ((value - LO) / (HI - LO)) * CHART_H;
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "flex-end", height: CHART_H + 30 }}>
      <div style={{ fontFamily: "var(--font-mono)", fontSize: 16, color, opacity: grow, marginBottom: 4 }}>{value.toFixed(2)}</div>
      <div style={{ width: 34, height: full * grow, background: color, borderRadius: "6px 6px 0 0" }} title={label} />
    </div>
  );
};

export const JEPA: React.FC = () => {
  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", gap: 22 }}>
      <Rise delay={2}>
        <div style={{ display: "flex", alignItems: "baseline", gap: 20, flexWrap: "wrap" }}>
          <h2 style={{ fontFamily: "var(--font-serif)", fontSize: 62, fontWeight: 600, margin: 0, letterSpacing: "-0.01em" }}>
            A foundation model I trained: <span style={{ color: colors.vital }}>multimodal JEPA</span>
          </h2>
        </div>
      </Rise>
      <Rise delay={5}>
        <div style={{ fontSize: 24, color: colors.muted, marginTop: -8 }}>
          Joint-Embedding Predictive Architecture — the body as one coupled dynamical system.
        </div>
      </Rise>

      <div style={{ display: "flex", gap: 26, flex: 1 }}>
        {/* Left: architecture sketch */}
        <Rise delay={10} style={{ flex: 0.92 }}>
          <Card pad={28} style={{ height: "100%", display: "flex", flexDirection: "column" }}>
            <Eyebrow>How it learns</Eyebrow>
            <div style={{ display: "flex", flexDirection: "column", gap: 14, marginTop: 18, flex: 1, justifyContent: "center" }}>
              <Box title="Context — past 2 hours" body="glucose · heart rate · activity · environment" tone={colors.ink} />
              <Arrow label="encode" />
              <Box title="Temporal encoders" body="PatchTST (CGM · wearable · env) + frozen RETFound + ECGFounder" tone={colors.ai} />
              <Arrow label="predict latent" />
              <Box title="Future window" body="held-out target · matched by an EMA teacher" tone={colors.vital} />
            </div>
            <div style={{ display: "flex", gap: 10, marginTop: 16, flexWrap: "wrap" }}>
              <Chip tone="neutral" mono>36 GPU runs</Chip>
              <Chip tone="neutral" mono>4 horizons</Chip>
              <Chip tone="neutral" mono>3 seeds</Chip>
            </div>
          </Card>
        </Rise>

        {/* Right: adversarial control chart */}
        <Rise delay={16} style={{ flex: 1.08 }}>
          <Card pad={28} style={{ height: "100%" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
              <Eyebrow>The adversarial test · prediction loss ↓ = more predictable</Eyebrow>
            </div>
            <div style={{ display: "flex", gap: 12, marginTop: 14 }}>
              <Legend color={colors.vital} label="aligned (real)" />
              <Legend color={colors.muted} label="wrong day" />
              <Legend color={colors.faint} label="wrong person" />
            </div>
            <div style={{ display: "flex", justifyContent: "space-around", marginTop: 14 }}>
              {HORIZONS.map((g, gi) => (
                <div key={g.h} style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
                  <div style={{ display: "flex", gap: 7, alignItems: "flex-end" }}>
                    <Bar value={g.aligned} color={colors.vital} delay={20 + gi * 6} label="aligned" />
                    <Bar value={g.wrong} color={colors.muted} delay={22 + gi * 6} label="wrong day" />
                    <Bar value={g.shuffle} color={colors.faint} delay={24 + gi * 6} label="wrong person" />
                  </div>
                  <div style={{ fontSize: 20, color: colors.muted, marginTop: 8, fontFamily: "var(--font-mono)" }}>{g.h}</div>
                </div>
              ))}
            </div>
            <div style={{ fontSize: 21, color: colors.ink, marginTop: 10, lineHeight: 1.35 }}>
              <strong style={{ color: colors.vitalSoft }}>aligned &lt; wrong-day &lt; wrong-person</strong> — every horizon, every seed. Real
              physiology is genuinely more predictable, and the edge decays with time.
            </div>
          </Card>
        </Rise>
      </div>

      {/* Nature Aging ribbon */}
      <Rise delay={34}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 18,
            border: `1.5px solid ${colors.ai}`,
            background: "rgba(87,94,207,0.07)",
            borderRadius: 18,
            padding: "16px 26px",
          }}
        >
          <span style={{ fontFamily: "var(--font-serif)", fontStyle: "italic", fontSize: 30, fontWeight: 600, color: colors.ai }}>
            Nature Aging
          </span>
          <span style={{ width: 1, height: 30, background: colors.border }} />
          <span style={{ fontSize: 25, color: colors.ink }}>
            This foundation-model work is <strong>currently under submission</strong>.
          </span>
        </div>
      </Rise>
    </div>
  );
};

const Box: React.FC<{ title: string; body: string; tone: string }> = ({ title, body, tone }) => (
  <div style={{ border: `1px solid ${colors.border}`, borderLeft: `4px solid ${tone}`, borderRadius: 14, padding: "14px 18px", background: colors.surface2 }}>
    <div style={{ fontWeight: 600, fontSize: 24 }}>{title}</div>
    <div style={{ fontSize: 19, color: colors.muted, marginTop: 3, fontFamily: "var(--font-mono)" }}>{body}</div>
  </div>
);

const Arrow: React.FC<{ label: string }> = ({ label }) => (
  <div style={{ display: "flex", alignItems: "center", gap: 10, paddingLeft: 8 }}>
    <span style={{ color: colors.faint, fontSize: 24 }}>↓</span>
    <span style={{ fontSize: 17, color: colors.faint, fontFamily: "var(--font-mono)" }}>{label}</span>
  </div>
);

const Legend: React.FC<{ color: string; label: string }> = ({ color, label }) => (
  <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 19, color: colors.muted }}>
    <span style={{ width: 14, height: 14, borderRadius: 4, background: color }} />
    {label}
  </div>
);
