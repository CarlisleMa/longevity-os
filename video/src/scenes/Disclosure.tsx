import React from "react";
import { useCurrentFrame, interpolate } from "remotion";
import { colors } from "../theme";
import { Card, Eyebrow, Check } from "../components/ui";
import { Rise } from "../lib/anim";

const items: { k: string; v: string; tone?: string }[] = [
  { k: "AI usage", v: "App, frontend, and this video built with Claude Code. The JEPA foundation-model paper is my own work." },
  { k: "Sources cited", v: "Research engine curated from my AI-READI workspace — pinned to a commit hash and DOI 10.60775/fairhub.3." },
  { k: "Borrowed models", v: "Retinal & cardiac encoders are the published RETFound and ECGFounder foundation models." },
  { k: "Data ethics", v: "No real participant data ships. The demo user is synthetic, per the AI-READI data-use agreement." },
  { k: "Scope", v: "Wellness & informational — explicitly not medical advice, enforced by a safety gate." },
  { k: "Reproducibility", v: "Public repo with full commit history, docs, provenance, and a claims map." },
];

export const Disclosure: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", gap: 22 }}>
      <Rise delay={2}>
        <h2 style={{ fontFamily: "var(--font-serif)", fontSize: 58, fontWeight: 600, margin: 0 }}>
          Integrity &amp; <span style={{ color: colors.ai }}>disclosure</span>.
        </h2>
      </Rise>
      <Rise delay={5}>
        <div style={{ fontSize: 24, color: colors.muted, marginTop: -8 }}>
          What's mine, what's borrowed, and the honest limits — stated up front.
        </div>
      </Rise>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, flex: 1 }}>
        {items.map((it, i) => (
          <div
            key={it.k}
            style={{
              opacity: interpolate(frame, [8 + i * 5, 18 + i * 5], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
              transform: `translateY(${interpolate(frame, [8 + i * 5, 18 + i * 5], [12, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })}px)`,
            }}
          >
            <Card pad={24} style={{ height: "100%", display: "flex", gap: 16, alignItems: "flex-start" }}>
              <Check color={colors.good} size={30} />
              <div>
                <div style={{ fontWeight: 700, fontSize: 24 }}>{it.k}</div>
                <div style={{ fontSize: 21, color: colors.muted, lineHeight: 1.4, marginTop: 5 }}>{it.v}</div>
              </div>
            </Card>
          </div>
        ))}
      </div>
    </div>
  );
};
