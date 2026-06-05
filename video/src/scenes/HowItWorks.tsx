import React from "react";
import { useCurrentFrame, interpolate } from "remotion";
import { colors } from "../theme";
import { Card } from "../components/ui";
import { Rise } from "../lib/anim";

const UploadIcon = () => (
  <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke={colors.vitalSoft} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
    <path d="M17 8l-5-5-5 5" />
    <path d="M12 3v12" />
  </svg>
);
const LineIcon = () => (
  <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke={colors.vitalSoft} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M3 3v18h18" />
    <path d="M19 9l-5 5-4-4-3 3" />
  </svg>
);
const SparkIcon = () => (
  <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke={colors.vitalSoft} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 3v4M12 17v4M3 12h4M17 12h4M5.6 5.6l2.8 2.8M15.6 15.6l2.8 2.8M18.4 5.6l-2.8 2.8M8.4 15.6l-2.8 2.8" />
  </svg>
);

const steps = [
  { icon: <UploadIcon />, title: "Upload", body: "Wearables, labs, imaging, and records — your data, private and local-first." },
  { icon: <LineIcon />, title: "Understand", body: "A growing knowledge base scores your multimodal aging and cross-system coupling — against your own baseline." },
  { icon: <SparkIcon />, title: "Act", body: "Evidence-grounded interventions, each gated for safety and tied to a validated finding." },
];

export const HowItWorks: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <div style={{ display: "flex", flexDirection: "column", justifyContent: "center", height: "100%", gap: 50 }}>
      <Rise delay={2}>
        <h2 style={{ fontFamily: "var(--font-serif)", fontSize: 60, fontWeight: 600, margin: 0, letterSpacing: "-0.01em" }}>
          From your data to your decisions.
        </h2>
      </Rise>
      <div style={{ display: "flex", gap: 28, alignItems: "stretch" }}>
        {steps.map((s, i) => (
          <React.Fragment key={s.title}>
            <Rise delay={8 + i * 10} style={{ flex: 1 }}>
              <Card pad={40} style={{ height: 380 }}>
                <div
                  style={{
                    width: 86,
                    height: 86,
                    borderRadius: 22,
                    background: "linear-gradient(135deg, rgba(255,90,31,0.14), rgba(87,94,207,0.14))",
                    display: "grid",
                    placeItems: "center",
                  }}
                >
                  {s.icon}
                </div>
                <div style={{ fontFamily: "var(--font-mono)", fontSize: 22, color: colors.faint, marginTop: 30 }}>
                  0{i + 1}
                </div>
                <div style={{ fontFamily: "var(--font-serif)", fontSize: 46, fontWeight: 600, marginTop: 6 }}>{s.title}</div>
                <p style={{ fontSize: 27, lineHeight: 1.45, color: colors.muted, marginTop: 14 }}>{s.body}</p>
              </Card>
            </Rise>
            {i < steps.length - 1 && (
              <div style={{ display: "flex", alignItems: "center" }}>
                <span
                  style={{
                    fontSize: 44,
                    color: colors.vital,
                    opacity: interpolate(frame, [16 + i * 10, 26 + i * 10], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
                  }}
                >
                  →
                </span>
              </div>
            )}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
};
