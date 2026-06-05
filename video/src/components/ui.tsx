import React from "react";
import { colors } from "../theme";

// ── Card: the app's warm paper card with soft cast shadow ──
export const Card: React.FC<{
  style?: React.CSSProperties;
  pad?: number;
  children: React.ReactNode;
}> = ({ style, pad = 28, children }) => (
  <div
    style={{
      background: colors.surface,
      border: `1px solid ${colors.border}`,
      borderRadius: 26,
      padding: pad,
      boxShadow:
        "0 1px 2px rgba(27,27,27,0.04), 0 18px 44px -18px rgba(27,27,27,0.22)",
      ...style,
    }}
  >
    {children}
  </div>
);

// ── Chip / pill ──
export const Chip: React.FC<{
  tone?: "neutral" | "good" | "watch" | "risk" | "ai" | "vital";
  style?: React.CSSProperties;
  mono?: boolean;
  children: React.ReactNode;
}> = ({ tone = "neutral", style, mono, children }) => {
  const map: Record<string, { bg: string; fg: string }> = {
    neutral: { bg: colors.surface2, fg: colors.muted },
    good: { bg: "rgba(78,140,106,0.13)", fg: colors.good },
    watch: { bg: "rgba(197,126,26,0.14)", fg: colors.watch },
    risk: { bg: "rgba(220,74,43,0.13)", fg: colors.risk },
    ai: { bg: "rgba(87,94,207,0.12)", fg: colors.ai },
    vital: { bg: "rgba(255,90,31,0.12)", fg: colors.vitalSoft },
  };
  const c = map[tone];
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 8,
        background: c.bg,
        color: c.fg,
        borderRadius: 999,
        padding: "7px 15px",
        fontSize: 21,
        fontWeight: 600,
        fontFamily: mono ? "var(--font-mono)" : "var(--font-sans)",
        whiteSpace: "nowrap",
        ...style,
      }}
    >
      {children}
    </span>
  );
};

// ── Small uppercase label (card eyebrows) ──
export const Eyebrow: React.FC<{ children: React.ReactNode; style?: React.CSSProperties }> = ({
  children,
  style,
}) => (
  <div
    style={{
      fontSize: 17,
      fontWeight: 700,
      letterSpacing: "0.1em",
      textTransform: "uppercase",
      color: colors.faint,
      fontFamily: "var(--font-sans)",
      ...style,
    }}
  >
    {children}
  </div>
);

// ── A status dot ──
export const Dot: React.FC<{ color: string; size?: number }> = ({ color, size = 10 }) => (
  <span
    style={{
      width: size,
      height: size,
      borderRadius: 999,
      background: color,
      display: "inline-block",
    }}
  />
);

// ── Gate badge with check (interventions) ──
export const Gate: React.FC<{ label: string; tone: "good" | "ai" | "vital" }> = ({
  label,
  tone,
}) => {
  const c =
    tone === "good" ? colors.good : tone === "ai" ? colors.ai : colors.vitalSoft;
  return (
    <div
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 10,
        border: `1.5px solid ${c}`,
        color: c,
        borderRadius: 14,
        padding: "12px 18px",
        fontWeight: 600,
        fontSize: 23,
        background: "rgba(255,255,255,0.6)",
      }}
    >
      <Check color={c} />
      {label}
    </div>
  );
};

export const Check: React.FC<{ color: string; size?: number }> = ({ color, size = 22 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
    <circle cx="12" cy="12" r="11" fill={color} opacity={0.14} />
    <path
      d="M7 12.5l3.2 3.2L17 8.8"
      stroke={color}
      strokeWidth={2.4}
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);
