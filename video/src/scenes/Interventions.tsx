import React from "react";
import { useCurrentFrame, interpolate } from "remotion";
import { colors } from "../theme";
import { Card, Eyebrow, Gate, Chip } from "../components/ui";
import { Rise } from "../lib/anim";

const team = [
  { who: "Metabolic agent", tone: colors.vital, msg: "Post-dinner glucose excursions are your largest; a timed walk blunts them." },
  { who: "Cardio agent", tone: colors.coral, msg: "Light zone-1 effort only — no contraindication in this profile." },
  { who: "Safety gate", tone: colors.good, msg: "Wellness-scoped. No clinician referral triggered. Cleared." },
];

export const Interventions: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", gap: 22 }}>
      <Rise delay={2}>
        <h2 style={{ fontFamily: "var(--font-serif)", fontSize: 56, fontWeight: 600, margin: 0 }}>
          Actions that pass <span style={{ color: colors.vital }}>three gates</span>.
        </h2>
      </Rise>

      <div style={{ display: "flex", gap: 26, flex: 1 }}>
        {/* intervention card */}
        <Rise delay={6} style={{ flex: 1 }}>
          <Card pad={32} style={{ height: "100%" }}>
            <Chip tone="vital" style={{ fontSize: 18 }}>Recommended for you</Chip>
            <div style={{ fontFamily: "var(--font-serif)", fontSize: 38, fontWeight: 600, lineHeight: 1.2, marginTop: 16 }}>
              Move 20 min of your evening walk to ~45 min after dinner.
            </div>
            <p style={{ fontSize: 23, color: colors.muted, lineHeight: 1.45, marginTop: 14 }}>
              Targets your blunted post-meal glucose–HR coupling — the largest excursion in your record.
            </p>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 12, marginTop: 26 }}>
              {([
                ["Evidence-grounded", "good"],
                ["Personalized", "ai"],
                ["Safety-checked", "vital"],
              ] as const).map(([label, tone], i) => (
                <div
                  key={label}
                  style={{ opacity: interpolate(frame, [14 + i * 6, 24 + i * 6], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) }}
                >
                  <Gate label={label} tone={tone} />
                </div>
              ))}
            </div>
            <div
              style={{
                marginTop: 26,
                display: "inline-flex",
                alignItems: "center",
                gap: 10,
                border: `1.5px solid ${colors.ink}`,
                borderRadius: 12,
                padding: "12px 20px",
                fontSize: 22,
                fontWeight: 600,
              }}
            >
              Why this? <span style={{ color: colors.vital }}>→</span>
            </div>
          </Card>
        </Rise>

        {/* care team trace */}
        <Rise delay={10} style={{ flex: 1 }}>
          <Card pad={28} style={{ height: "100%" }}>
            <Eyebrow>Multi-agent care team · reasoning trace</Eyebrow>
            <div style={{ display: "flex", flexDirection: "column", gap: 14, marginTop: 18 }}>
              {team.map((t, i) => {
                const appear = 24 + i * 14;
                return (
                  <div
                    key={t.who}
                    style={{
                      border: `1px solid ${colors.border}`,
                      borderLeft: `4px solid ${t.tone}`,
                      borderRadius: 14,
                      padding: "16px 20px",
                      background: colors.surface2,
                      opacity: interpolate(frame, [appear, appear + 10], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
                      transform: `translateY(${interpolate(frame, [appear, appear + 10], [10, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })}px)`,
                    }}
                  >
                    <div style={{ fontWeight: 600, fontSize: 22, color: t.tone, fontFamily: "var(--font-mono)" }}>{t.who}</div>
                    <div style={{ fontSize: 22, color: colors.ink, marginTop: 5, lineHeight: 1.35 }}>{t.msg}</div>
                  </div>
                );
              })}
            </div>
            <div
              style={{
                marginTop: 18,
                fontSize: 21,
                color: colors.muted,
                opacity: interpolate(frame, [70, 80], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
              }}
            >
              Same guarded reviewer pattern as the research engine — nothing reaches you ungated.
            </div>
          </Card>
        </Rise>
      </div>
    </div>
  );
};
