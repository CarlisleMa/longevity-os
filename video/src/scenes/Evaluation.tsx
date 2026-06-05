import React from "react";
import { useCurrentFrame, interpolate } from "remotion";
import { colors } from "../theme";
import { Card, Eyebrow, Chip } from "../components/ui";
import { Rise } from "../lib/anim";

const pillars = [
  {
    tag: "Control-validated model",
    body: "Aligned physiology beats wrong-day and wrong-person controls — repeated across 36 runs, 4 horizons, 3 seeds.",
    accent: colors.vital,
  },
  {
    tag: "Honest hypothesis ledger",
    body: "27 hypotheses through propose → critique → verify. The refuted and open ones stay on the record.",
    accent: colors.ai,
  },
  {
    tag: "N-of-1 over cohort",
    body: "On one person, a cohort percentile is shaky — so we lead with within-person change against your own baseline.",
    accent: colors.good,
  },
];

export const Evaluation: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", gap: 24 }}>
      <Rise delay={2}>
        <h2 style={{ fontFamily: "var(--font-serif)", fontSize: 58, fontWeight: 600, margin: 0 }}>
          How do we know it's <span style={{ color: colors.vital }}>real</span>?
        </h2>
      </Rise>

      <div style={{ display: "flex", gap: 24, flex: 1 }}>
        {pillars.map((p, i) => (
          <Rise key={p.tag} delay={8 + i * 8} style={{ flex: 1 }}>
            <Card pad={30} style={{ height: "100%", borderTop: `4px solid ${p.accent}` }}>
              <div style={{ fontFamily: "var(--font-mono)", fontSize: 24, color: colors.faint }}>0{i + 1}</div>
              <div style={{ fontFamily: "var(--font-serif)", fontSize: 34, fontWeight: 600, marginTop: 10, color: p.accent }}>{p.tag}</div>
              <p style={{ fontSize: 24, color: colors.ink, lineHeight: 1.45, marginTop: 14 }}>{p.body}</p>
            </Card>
          </Rise>
        ))}
      </div>

      {/* hypothesis status breakdown */}
      <Rise delay={32}>
        <Card pad={26}>
          <div style={{ display: "flex", alignItems: "center", gap: 24, flexWrap: "wrap" }}>
            <Eyebrow>Hypothesis ledger (n = 27)</Eyebrow>
            <div style={{ display: "flex", gap: 12 }}>
              <Chip tone="good">supported</Chip>
              <Chip tone="risk">refuted — kept honest</Chip>
              <Chip tone="neutral">critiqued / open</Chip>
            </div>
            <div style={{ flex: 1, minWidth: 280, display: "flex", gap: 6, height: 20, borderRadius: 999, overflow: "hidden" }}>
              {[
                [18.5, colors.good],
                [3.7, colors.risk],
                [77.8, colors.surface2],
              ].map(([pct, c], i) => (
                <div
                  key={i}
                  style={{
                    width: `${interpolate(frame, [36 + i * 4, 48 + i * 4], [0, pct as number], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })}%`,
                    background: c as string,
                    border: i === 2 ? `1px solid ${colors.border}` : undefined,
                  }}
                />
              ))}
            </div>
          </div>
          <div style={{ fontSize: 20, color: colors.muted, marginTop: 16 }}>
            Limitations stated plainly: ~2,280 participants is small for from-scratch encoders; static phenotype
            shortcuts age/severity; results show predictability, not yet causal mechanism.
          </div>
        </Card>
      </Rise>
    </div>
  );
};
