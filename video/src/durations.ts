// Measured per-scene audio durations (seconds), keyed by scene id.
// Overwritten by scripts/generate-voiceover.mjs once real narration exists, so
// the visuals lock exactly to your voiceover. Empty = use script fallbacks.
export const DURATIONS: Record<string, number> = {};
