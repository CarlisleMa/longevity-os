import React from "react";
import {
  useCurrentFrame,
  useVideoConfig,
  spring,
  interpolate,
  Easing,
} from "remotion";

// A spring-driven fade-rise, the app's signature entrance (see globals "fade-rise").
export const useRise = (delayFrames = 0, distance = 16) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({
    frame: frame - delayFrames,
    fps,
    config: { damping: 200, stiffness: 120, mass: 0.7 },
  });
  return {
    opacity: s,
    transform: `translateY(${(1 - s) * distance}px)`,
  } as React.CSSProperties;
};

// Wrap any block to make it fade-rise in, with an optional stagger delay.
export const Rise: React.FC<{
  delay?: number;
  distance?: number;
  style?: React.CSSProperties;
  children: React.ReactNode;
}> = ({ delay = 0, distance = 16, style, children }) => {
  const r = useRise(delay, distance);
  return <div style={{ ...r, ...style }}>{children}</div>;
};

// Scale-stamp entrance (used for the biological-age number, badges).
export const useStamp = (delayFrames = 0) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({
    frame: frame - delayFrames,
    fps,
    config: { damping: 12, stiffness: 140, mass: 0.8 },
  });
  return {
    opacity: interpolate(s, [0, 0.4], [0, 1], { extrapolateRight: "clamp" }),
    transform: `scale(${interpolate(s, [0, 1], [0.7, 1])})`,
  } as React.CSSProperties;
};

// Count a number up over a window of frames.
export const useCountUp = (
  to: number,
  { delay = 0, duration = 30, decimals = 0 }: { delay?: number; duration?: number; decimals?: number } = {}
) => {
  const frame = useCurrentFrame();
  const t = interpolate(frame, [delay, delay + duration], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  return (to * t).toFixed(decimals);
};

// A value that draws/sweeps from 0..1 over a window (for bars, rings, paths).
export const useSweep = (delay = 0, duration = 30, easing = Easing.inOut(Easing.cubic)) => {
  const frame = useCurrentFrame();
  return interpolate(frame, [delay, delay + duration], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing,
  });
};

// Gentle perpetual float for hero cards.
export const useFloat = (amplitude = 6, periodS = 6) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return `translateY(${Math.sin((frame / (periodS * fps)) * Math.PI * 2) * amplitude}px)`;
};
