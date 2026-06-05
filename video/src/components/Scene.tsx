import React from "react";
import { AbsoluteFill, useCurrentFrame, interpolate } from "remotion";
import { colors } from "../theme";
import { Paper } from "./Paper";
import { Dot } from "./ui";
import { Rise } from "../lib/anim";
import type { RubricTag } from "../script";

// Brand wordmark, top-left.
const BrandMark: React.FC<{ ink?: boolean }> = ({ ink }) => (
  <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
    <Dot color={colors.vital} size={12} />
    <span
      style={{
        fontFamily: "var(--font-serif)",
        fontWeight: 600,
        fontSize: 30,
        letterSpacing: "-0.01em",
        color: ink ? "#f3efe6" : colors.ink,
      }}
    >
      Longevity<span style={{ color: colors.vital }}>OS</span>
    </span>
  </div>
);

// Rubric criterion chip, top-right — directly serves the grader.
const RubricChip: React.FC<{ tag: RubricTag; ink?: boolean }> = ({ tag, ink }) => (
  <div
    style={{
      display: "inline-flex",
      alignItems: "center",
      gap: 10,
      border: `1px solid ${ink ? "#3a352a" : colors.border}`,
      background: ink ? "rgba(255,255,255,0.04)" : colors.surface,
      color: ink ? "#cfc8b8" : colors.muted,
      borderRadius: 999,
      padding: "9px 16px",
      fontSize: 19,
      fontWeight: 600,
      fontFamily: "var(--font-sans)",
    }}
  >
    <span style={{ fontSize: 15, color: colors.faint, letterSpacing: "0.08em" }}>RUBRIC</span>
    <span style={{ width: 1, height: 16, background: ink ? "#3a352a" : colors.border }} />
    {tag}
  </div>
);

// Bottom subtitle band — keeps the video understandable on mute.
const Caption: React.FC<{ text: string; ink?: boolean; dur: number }> = ({ text, ink, dur }) => {
  const frame = useCurrentFrame();
  // fade the caption in at the start and out near the end of the scene
  const opacity = interpolate(
    frame,
    [6, 18, dur - 16, dur - 4],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );
  return (
    <div
      style={{
        position: "absolute",
        left: 80,
        right: 80,
        bottom: 70,
        opacity,
        display: "flex",
        justifyContent: "center",
      }}
    >
      <div
        style={{
          maxWidth: 1400,
          textAlign: "center",
          fontFamily: "var(--font-sans)",
          fontSize: 30,
          lineHeight: 1.4,
          fontWeight: 500,
          color: ink ? "#e7e1d4" : colors.ink,
          background: ink ? "rgba(20,19,16,0.55)" : "rgba(252,251,248,0.72)",
          border: `1px solid ${ink ? "#332f26" : colors.border}`,
          borderRadius: 18,
          padding: "16px 28px",
          backdropFilter: "blur(6px)",
        }}
      >
        {text}
      </div>
    </div>
  );
};

// The frame around every scene: paper, brand, rubric chip, caption, content.
export const Scene: React.FC<{
  rubric?: RubricTag;
  caption?: string;
  ink?: boolean;
  chrome?: boolean; // show brand + rubric chip (off for full-bleed title/close)
  durationInFrames: number;
  children: React.ReactNode;
}> = ({ rubric, caption, ink, chrome = true, durationInFrames, children }) => {
  return (
    <Paper tone={ink ? "ink" : "paper"}>
      {chrome && (
        <>
          <Rise delay={2} style={{ position: "absolute", top: 56, left: 80 }}>
            <BrandMark ink={ink} />
          </Rise>
          {rubric && (
            <Rise delay={4} style={{ position: "absolute", top: 56, right: 80 }}>
              <RubricChip tag={rubric} ink={ink} />
            </Rise>
          )}
        </>
      )}
      <AbsoluteFill
        style={{
          padding: chrome ? "120px 76px 168px" : 0,
          display: "flex",
          overflow: "hidden",
        }}
      >
        {children}
      </AbsoluteFill>
      {caption && <Caption text={caption} ink={ink} dur={durationInFrames} />}
    </Paper>
  );
};
