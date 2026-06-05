import React from "react";
import { AbsoluteFill, useCurrentFrame, interpolate } from "remotion";
import { colors } from "../theme";
import { Card, Chip, Eyebrow, Dot } from "../components/ui";
import { Rise, useCountUp, useFloat, useStamp } from "../lib/anim";

const biomarkers = ["VO₂max", "HbA1c", "RHR 58", "HRV", "TIR 82%", "ApoB", "Sleep 88%"];

export const Title: React.FC = () => {
  const frame = useCurrentFrame();
  const float = useFloat(8, 6);
  const bio = useCountUp(44.7, { delay: 24, duration: 34, decimals: 1 });
  const stamp = useStamp(50);

  return (
    <AbsoluteFill style={{ padding: "0 110px", display: "flex", flexDirection: "row", alignItems: "center", gap: 70 }}>
      {/* Left: headline */}
      <div style={{ flex: 1.05 }}>
        <Rise delay={2}>
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 26 }}>
            <Dot color={colors.vital} size={14} />
            <span style={{ fontFamily: "var(--font-serif)", fontWeight: 600, fontSize: 38, letterSpacing: "-0.01em" }}>
              Longevity<span style={{ color: colors.vital }}>OS</span>
            </span>
          </div>
        </Rise>
        <Rise delay={6}>
          <Chip tone="neutral" style={{ fontSize: 19, marginBottom: 28 }}>
            <Dot color={colors.vital} size={9} /> Foundation model validated on 2,280 participants
          </Chip>
        </Rise>
        <Rise delay={10}>
          <h1
            style={{
              fontFamily: "var(--font-serif)",
              fontWeight: 600,
              fontSize: 104,
              lineHeight: 1.02,
              letterSpacing: "-0.02em",
              margin: 0,
            }}
          >
            Your biology,
            <br />
            <span
              style={{
                background: `linear-gradient(100deg, ${colors.vital}, ${colors.ai})`,
                WebkitBackgroundClip: "text",
                backgroundClip: "text",
                color: "transparent",
              }}
            >
              understood
            </span>
            .
          </h1>
        </Rise>
        <Rise delay={16}>
          <p style={{ fontFamily: "var(--font-sans)", fontSize: 32, lineHeight: 1.45, color: colors.muted, maxWidth: 760, marginTop: 28 }}>
            Validated longevity research, turned into a private, growing model of <em>you</em> — and
            into evidence-grounded actions you can take.
          </p>
        </Rise>
        <Rise delay={22} style={{ marginTop: 30, display: "flex", flexWrap: "wrap", gap: 12 }}>
          {biomarkers.map((b) => (
            <span
              key={b}
              style={{
                border: `1px solid ${colors.border}`,
                background: colors.surface,
                color: colors.muted,
                fontFamily: "var(--font-mono)",
                fontSize: 22,
                padding: "8px 14px",
                borderRadius: 10,
              }}
            >
              {b}
            </span>
          ))}
        </Rise>
      </div>

      {/* Right: floating scorecard (echo of the app hero) */}
      <div style={{ flex: 0.95, display: "flex", justifyContent: "center" }}>
        <Rise delay={14} style={{ transform: float, width: 560 }}>
          <div style={{ position: "relative" }}>
            <div
              style={{
                position: "absolute",
                inset: -40,
                background: "radial-gradient(60% 60% at 50% 40%, rgba(255,90,31,0.18), transparent 70%)",
                filter: "blur(10px)",
              }}
            />
            <Card pad={40} style={{ position: "relative" }}>
              <Eyebrow>Biological age</Eyebrow>
              <div style={{ display: "flex", alignItems: "baseline", gap: 18, marginTop: 12 }}>
                <span style={{ fontFamily: "var(--font-mono)", fontSize: 116, fontWeight: 600, lineHeight: 1 }}>{bio}</span>
                <span style={{ fontSize: 28, color: colors.muted }}>vs 47 chronological</span>
              </div>
              <div style={{ display: "flex", gap: 12, marginTop: 22, ...stamp }}>
                <Chip tone="good">−2.3 yrs younger</Chip>
                <Chip tone="neutral" style={{ fontSize: 19 }}>↓ 0.4 vs your baseline</Chip>
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 14, marginTop: 30 }}>
                {([
                  ["Cardiac", "−3.1", colors.good],
                  ["Metabolic", "+1.8", colors.watch],
                  ["Retinal", "−1.2", colors.good],
                ] as const).map(([sys, v, c], i) => (
                  <div
                    key={sys}
                    style={{
                      border: `1px solid ${colors.border}`,
                      background: colors.surface2,
                      borderRadius: 16,
                      padding: "16px 12px",
                      textAlign: "center",
                      opacity: interpolate(frame, [40 + i * 5, 52 + i * 5], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
                    }}
                  >
                    <div style={{ fontSize: 18, color: colors.faint }}>{sys}</div>
                    <div style={{ fontFamily: "var(--font-mono)", fontSize: 30, fontWeight: 600, color: c, marginTop: 4 }}>{v}</div>
                  </div>
                ))}
              </div>
            </Card>
          </div>
        </Rise>
      </div>
    </AbsoluteFill>
  );
};
