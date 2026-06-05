import React from "react";
import { useCurrentFrame, interpolate, spring, useVideoConfig } from "remotion";
import { colors } from "../theme";
import { Card, Eyebrow, Chip, Check } from "../components/ui";
import { Rise } from "../lib/anim";

// Animated cursor that drifts to the evidence chip and clicks it.
const Cursor: React.FC<{ clickAt: number }> = ({ clickAt }) => {
  const frame = useCurrentFrame();
  const t = interpolate(frame, [10, clickAt], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const x = interpolate(t, [0, 1], [560, 300]);
  const y = interpolate(t, [0, 1], [520, 330]);
  const press = frame >= clickAt && frame < clickAt + 8 ? 0.85 : 1;
  return (
    <div style={{ position: "absolute", left: x, top: y, transform: `scale(${press})`, transition: "transform .1s", zIndex: 10 }}>
      <svg width="34" height="34" viewBox="0 0 24 24" fill={colors.ink} stroke="#fff" strokeWidth="1.5">
        <path d="M5 3l5 16 2.5-6.5L19 10z" />
      </svg>
    </div>
  );
};

export const Evidence: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const clickAt = 36;
  const open = spring({ frame: frame - clickAt, fps, config: { damping: 200, stiffness: 120 } });
  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", gap: 22 }}>
      <Rise delay={2}>
        <h2 style={{ fontFamily: "var(--font-serif)", fontSize: 56, fontWeight: 600, margin: 0 }}>
          Every interpretation is <span style={{ color: colors.vital }}>grounded</span>.
        </h2>
      </Rise>

      <div style={{ display: "flex", gap: 26, flex: 1, position: "relative" }}>
        <Cursor clickAt={clickAt} />
        {/* knowledge card */}
        <Rise delay={6} style={{ flex: 1 }}>
          <Card pad={32} style={{ height: "100%" }}>
            <Eyebrow>Knowledge card</Eyebrow>
            <div style={{ fontFamily: "var(--font-serif)", fontSize: 36, fontWeight: 600, lineHeight: 1.25, marginTop: 14 }}>
              Event windows concentrate glucose–HR coupling — and yours reads blunted after meals.
            </div>
            <p style={{ fontSize: 24, color: colors.muted, lineHeight: 1.45, marginTop: 16 }}>
              Your post-meal heart-rate response lags and flattens relative to your glucose excursion — a
              cross-system coordination signal, measured against your own baseline.
            </p>
            <div style={{ marginTop: 24, display: "flex", alignItems: "center", gap: 12 }}>
              <span style={{ fontSize: 21, color: colors.faint }}>Evidence:</span>
              <span
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 8,
                  border: `1.5px solid ${frame >= clickAt ? colors.ai : colors.border}`,
                  background: frame >= clickAt ? "rgba(87,94,207,0.1)" : colors.surface2,
                  color: colors.ai,
                  borderRadius: 999,
                  padding: "9px 16px",
                  fontFamily: "var(--font-mono)",
                  fontSize: 22,
                  fontWeight: 600,
                }}
              >
                🔗 H-NEW13
              </span>
            </div>
          </Card>
        </Rise>

        {/* evidence trace popover */}
        <div style={{ flex: 1, opacity: open, transform: `translateX(${(1 - open) * 40}px)` }}>
          <Card pad={30} style={{ height: "100%", borderTop: `4px solid ${colors.ai}` }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <Eyebrow>Traced to research engine</Eyebrow>
              <Chip tone="good" style={{ fontSize: 18 }}>
                <Check color={colors.good} size={18} /> verified
              </Chip>
            </div>
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 30, fontWeight: 600, color: colors.ai, marginTop: 14 }}>
              Hypothesis H-NEW13
            </div>
            <p style={{ fontSize: 22, color: colors.ink, lineHeight: 1.4, marginTop: 8 }}>
              “Event windows concentrate physiologically meaningful cross-modal coupling.”
            </p>
            <div style={{ display: "flex", gap: 10, marginTop: 18, flexWrap: "wrap" }}>
              {["Propose", "Critique", "Execute", "Verify"].map((s, i) => (
                <span
                  key={s}
                  style={{
                    fontSize: 19,
                    fontFamily: "var(--font-mono)",
                    color: colors.good,
                    border: `1px solid ${colors.border}`,
                    borderRadius: 10,
                    padding: "6px 12px",
                    opacity: interpolate(frame, [clickAt + 8 + i * 4, clickAt + 16 + i * 4], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
                  }}
                >
                  ✓ {s}
                </span>
              ))}
            </div>
            <div style={{ marginTop: 22, fontSize: 21, color: colors.muted, lineHeight: 1.4 }}>
              Backed by event-control suites: aligned event windows beat wrong-day and wrong-person across 36 runs.
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
};
