import React from "react";
import { AbsoluteFill } from "remotion";
import { colors } from "../theme";

// The warm ivory "paper" backdrop with a faint hairline grid + soft vignette,
// echoing the app's paper-grid texture.
export const Paper: React.FC<{
  tone?: "paper" | "ink";
  children?: React.ReactNode;
}> = ({ tone = "paper", children }) => {
  if (tone === "ink") {
    return (
      <AbsoluteFill
        style={{
          background: `radial-gradient(120% 120% at 50% 0%, ${colors.inkPanel2} 0%, ${colors.inkPanel} 60%)`,
          color: "#f3efe6",
        }}
      >
        <AbsoluteFill style={{ opacity: 0.5, ...grid("#2c281f") }} />
        {children}
      </AbsoluteFill>
    );
  }
  return (
    <AbsoluteFill style={{ background: colors.bg, color: colors.ink }}>
      <AbsoluteFill style={grid(colors.border)} />
      <AbsoluteFill
        style={{
          background:
            "radial-gradient(70% 55% at 50% 38%, rgba(255,90,31,0.05) 0%, transparent 70%)",
        }}
      />
      {children}
    </AbsoluteFill>
  );
};

const grid = (line: string): React.CSSProperties => ({
  backgroundImage: `linear-gradient(${line} 1px, transparent 1px), linear-gradient(90deg, ${line} 1px, transparent 1px)`,
  backgroundSize: "56px 56px",
  opacity: 0.4,
  maskImage:
    "radial-gradient(120% 100% at 50% 50%, black 55%, transparent 100%)",
  WebkitMaskImage:
    "radial-gradient(120% 100% at 50% 50%, black 55%, transparent 100%)",
});
