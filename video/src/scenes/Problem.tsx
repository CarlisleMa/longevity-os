import React from "react";
import { useCurrentFrame, interpolate } from "remotion";
import { colors } from "../theme";
import { Card, Eyebrow } from "../components/ui";
import { Rise, useSweep } from "../lib/anim";

const Panel: React.FC<{
  eyebrow: string;
  title: string;
  accent: string;
  children: React.ReactNode;
  delay: number;
}> = ({ eyebrow, title, accent, children, delay }) => (
  <Rise delay={delay} style={{ flex: 1 }}>
    <Card pad={34} style={{ height: 330, borderTop: `4px solid ${accent}` }}>
      <Eyebrow>{eyebrow}</Eyebrow>
      <div style={{ fontFamily: "var(--font-serif)", fontSize: 40, fontWeight: 600, marginTop: 10, marginBottom: 22 }}>
        {title}
      </div>
      {children}
    </Card>
  </Rise>
);

// Many small dots = a population.
const Cohort: React.FC = () => {
  const frame = useCurrentFrame();
  const dots = Array.from({ length: 56 });
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(14, 1fr)", gap: 12, marginTop: 8 }}>
      {dots.map((_, i) => (
        <div
          key={i}
          style={{
            width: 16,
            height: 16,
            borderRadius: 999,
            background: colors.muted,
            opacity: interpolate(frame, [10 + i * 0.6, 18 + i * 0.6], [0, 0.55], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
          }}
        />
      ))}
    </div>
  );
};

// One highlighted person = the individual.
const OnePerson: React.FC = () => (
  <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: 200 }}>
    <div style={{ position: "relative" }}>
      <div style={{ position: "absolute", inset: -22, borderRadius: 999, background: "radial-gradient(circle, rgba(255,90,31,0.22), transparent 70%)" }} />
      <div style={{ width: 70, height: 70, borderRadius: 999, background: colors.vital, position: "relative" }} />
    </div>
    <div style={{ marginTop: 18, fontFamily: "var(--font-mono)", fontSize: 24, color: colors.vitalSoft }}>you · N-of-1</div>
  </div>
);

export const Problem: React.FC = () => {
  const arrow = useSweep(28, 26);
  return (
    <div style={{ display: "flex", flexDirection: "column", justifyContent: "center", height: "100%", gap: 40 }}>
      <Rise delay={2}>
        <h2 style={{ fontFamily: "var(--font-serif)", fontSize: 58, fontWeight: 600, margin: 0, letterSpacing: "-0.01em" }}>
          Research turns a population into knowledge — then{" "}
          <span style={{ color: colors.vital }}>stops at the journal</span>.
        </h2>
      </Rise>

      <div style={{ display: "flex", alignItems: "center", gap: 30 }}>
        <Panel eyebrow="The research engine" title="Population → Knowledge" accent={colors.ai} delay={8}>
          <Cohort />
          <div style={{ marginTop: 18, color: colors.muted, fontSize: 24 }}>aging clocks · biomarkers · coupling findings</div>
        </Panel>

        {/* reversed arrow */}
        <div style={{ width: 130, display: "flex", flexDirection: "column", alignItems: "center", gap: 8 }}>
          <svg width={130} height={56} viewBox="0 0 130 56">
            <defs>
              <linearGradient id="ar" x1="0" x2="1">
                <stop offset="0" stopColor={colors.ai} />
                <stop offset="1" stopColor={colors.vital} />
              </linearGradient>
            </defs>
            <line x1="6" y1="28" x2={6 + 100 * arrow} y2="28" stroke="url(#ar)" strokeWidth={5} strokeLinecap="round" />
            <path
              d={`M${6 + 100 * arrow - 16} 18 L${6 + 100 * arrow} 28 L${6 + 100 * arrow - 16} 38`}
              fill="none"
              stroke={colors.vital}
              strokeWidth={5}
              strokeLinecap="round"
              strokeLinejoin="round"
              opacity={arrow > 0.5 ? 1 : 0}
            />
          </svg>
          <div style={{ fontFamily: "var(--font-mono)", fontSize: 18, color: colors.faint }}>run in reverse</div>
        </div>

        <Panel eyebrow="LongevityOS" title="Knowledge → You" accent={colors.vital} delay={14}>
          <OnePerson />
        </Panel>
      </div>

      {/* N-of-1 insight */}
      <Rise delay={40}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 22,
            border: `1px solid ${colors.border}`,
            background: "rgba(87,94,207,0.06)",
            borderRadius: 20,
            padding: "22px 30px",
          }}
        >
          <div style={{ fontFamily: "var(--font-mono)", fontSize: 26, fontWeight: 600, color: colors.ai, whiteSpace: "nowrap" }}>
            The insight
          </div>
          <div style={{ width: 1, height: 40, background: colors.border }} />
          <div style={{ fontSize: 28, color: colors.ink, lineHeight: 1.35 }}>
            A cohort clock on one person has wide error bars — so we lead with{" "}
            <strong>within-person change against your own baseline</strong>. A clean N-of-1 control.
          </div>
        </div>
      </Rise>
    </div>
  );
};
