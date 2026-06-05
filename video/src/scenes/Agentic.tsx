import React from "react";
import { useCurrentFrame, interpolate } from "remotion";
import { colors } from "../theme";
import { Card, Eyebrow, Chip, Check } from "../components/ui";
import { Rise } from "../lib/anim";

const pipeline = ["Propose", "Critique", "Execute", "Verify"];
const agents = [
  "Literature",
  "Hypothesis",
  "Scientific Critic",
  "Feasibility / Leakage",
  "Method Planner",
  "Executor",
  "Mechanical Verifier",
  "Surprise Miner",
  "Synthesis",
];
const gates = [
  { name: "Scientific critic", sub: "is the claim sound + grounded?" },
  { name: "Feasibility & leakage", sub: "any train/test contamination?" },
  { name: "Mechanical verifier", sub: "do paths + artifacts check out?" },
];

export const Agentic: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", gap: 22 }}>
      <Rise delay={2}>
        <h2 style={{ fontFamily: "var(--font-serif)", fontSize: 60, fontWeight: 600, margin: 0, letterSpacing: "-0.01em" }}>
          An <span style={{ color: colors.ai }}>agentic discovery</span> system
        </h2>
      </Rise>
      <Rise delay={5}>
        <div style={{ fontSize: 24, color: colors.muted, marginTop: -8 }}>
          Built on the Claude Agent SDK — a team of specialists that hypothesizes, runs, and checks the science.
        </div>
      </Rise>

      {/* pipeline stepper */}
      <Rise delay={8}>
        <div style={{ display: "flex", alignItems: "center", gap: 0, marginTop: 4 }}>
          {pipeline.map((p, i) => (
            <React.Fragment key={p}>
              <div
                style={{
                  flex: 1,
                  textAlign: "center",
                  padding: "16px 0",
                  borderRadius: 14,
                  border: `1px solid ${colors.border}`,
                  background: colors.surface,
                  fontWeight: 600,
                  fontSize: 26,
                  opacity: interpolate(frame, [10 + i * 5, 18 + i * 5], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
                }}
              >
                <span style={{ fontFamily: "var(--font-mono)", color: colors.ai, marginRight: 8 }}>{i + 1}</span>
                {p}
              </div>
              {i < pipeline.length - 1 && <span style={{ padding: "0 14px", color: colors.faint, fontSize: 26 }}>→</span>}
            </React.Fragment>
          ))}
        </div>
      </Rise>

      <div style={{ display: "flex", gap: 26, flex: 1 }}>
        {/* agents */}
        <Rise delay={16} style={{ flex: 0.9 }}>
          <Card pad={26} style={{ height: "100%" }}>
            <Eyebrow>Specialist agents</Eyebrow>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 10, marginTop: 16 }}>
              {agents.map((a, i) => (
                <span
                  key={a}
                  style={{
                    border: `1px solid ${colors.border}`,
                    background: colors.surface2,
                    borderRadius: 999,
                    padding: "9px 16px",
                    fontSize: 21,
                    fontWeight: 500,
                    opacity: interpolate(frame, [18 + i * 2.5, 26 + i * 2.5], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
                  }}
                >
                  {a}
                </span>
              ))}
            </div>
            <div
              style={{
                marginTop: 22,
                display: "flex",
                alignItems: "center",
                gap: 12,
                border: `1px dashed ${colors.borderStrong}`,
                borderRadius: 14,
                padding: "14px 18px",
              }}
            >
              <span style={{ fontSize: 26 }}>🔒</span>
              <div style={{ fontSize: 21, color: colors.ink }}>
                Agents get <strong>guarded, vetted tools only</strong> — never raw shell access.
              </div>
            </div>
          </Card>
        </Rise>

        {/* gates */}
        <Rise delay={22} style={{ flex: 1.1 }}>
          <Card pad={26} style={{ height: "100%" }}>
            <Eyebrow>Promotion requires all three gates to PASS</Eyebrow>
            <div style={{ display: "flex", flexDirection: "column", gap: 12, marginTop: 16 }}>
              {gates.map((g, i) => {
                const on = frame > 30 + i * 7;
                return (
                  <div
                    key={g.name}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 16,
                      border: `1.5px solid ${on ? colors.good : colors.border}`,
                      borderRadius: 14,
                      padding: "16px 20px",
                      background: on ? "rgba(78,140,106,0.07)" : colors.surface,
                      transition: "all .3s",
                    }}
                  >
                    <Check color={on ? colors.good : colors.faint} size={30} />
                    <div>
                      <div style={{ fontWeight: 600, fontSize: 25 }}>{g.name}</div>
                      <div style={{ fontSize: 19, color: colors.muted, fontFamily: "var(--font-mono)" }}>{g.sub}</div>
                    </div>
                    <div style={{ marginLeft: "auto", fontFamily: "var(--font-mono)", fontWeight: 700, fontSize: 22, color: on ? colors.good : colors.faint }}>
                      {on ? "PASS" : "…"}
                    </div>
                  </div>
                );
              })}
            </div>
            <div
              style={{
                marginTop: 18,
                display: "flex",
                gap: 14,
                opacity: interpolate(frame, [56, 66], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
              }}
            >
              <Chip tone="ai" mono>→ 27 hypotheses</Chip>
              <Chip tone="vital" mono>coupling atlas · AUROC 0.80</Chip>
            </div>
          </Card>
        </Rise>
      </div>
    </div>
  );
};
