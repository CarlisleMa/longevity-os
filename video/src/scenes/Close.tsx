import React from "react";
import { AbsoluteFill, useCurrentFrame, interpolate } from "remotion";
import { colors } from "../theme";
import { Rise, useFloat } from "../lib/anim";

export const Close: React.FC = () => {
  const frame = useCurrentFrame();
  const float = useFloat(6, 7);
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", textAlign: "center" }}>
      <Rise delay={2} style={{ transform: float }}>
        <div style={{ display: "flex", alignItems: "center", gap: 16, justifyContent: "center" }}>
          <span style={{ width: 16, height: 16, borderRadius: 999, background: colors.vital }} />
          <span style={{ fontFamily: "var(--font-serif)", fontWeight: 600, fontSize: 88, letterSpacing: "-0.02em", color: "#f3efe6" }}>
            Longevity<span style={{ color: colors.vital }}>OS</span>
          </span>
        </div>
      </Rise>
      <Rise delay={8}>
        <p style={{ fontFamily: "var(--font-sans)", fontSize: 32, color: "#cfc8b8", maxWidth: 1000, lineHeight: 1.45, marginTop: 28 }}>
          The longer you use it, the better it knows you — turning validated science into a private,
          evidence-grounded feedback loop for your own healthspan.
        </p>
      </Rise>
      <Rise delay={16}>
        <div style={{ display: "flex", gap: 14, marginTop: 40, justifyContent: "center", flexWrap: "wrap" }}>
          {["Validated on AI-READI (2,280)", "JEPA · under submission to Nature Aging", "Built with Claude Code"].map((t) => (
            <span
              key={t}
              style={{
                border: "1px solid #3a352a",
                background: "rgba(255,255,255,0.04)",
                color: "#cfc8b8",
                borderRadius: 999,
                padding: "11px 20px",
                fontSize: 21,
                fontFamily: "var(--font-mono)",
              }}
            >
              {t}
            </span>
          ))}
        </div>
      </Rise>
      <Rise delay={22}>
        <div
          style={{
            marginTop: 44,
            fontSize: 24,
            color: "#8f897b",
            fontFamily: "var(--font-mono)",
            opacity: interpolate(frame, [22, 34], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
          }}
        >
          github.com/CarlisleMa/longevity-os · wellness &amp; informational, not medical advice
        </div>
      </Rise>
    </AbsoluteFill>
  );
};
