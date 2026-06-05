// Design tokens lifted from the LongevityOS app (frontend/app/globals.css)
// so the video is on-brand: warm ivory paper, near-black ink, vivid orange
// primary, indigo for agentic/AI, sage/amber/coral for status + data-viz.

export const colors = {
  bg: "#fcfbf8", // warm ivory paper
  surface: "#ffffff", // cards
  surface2: "#f4f1ea", // elevated / hover
  border: "#e7e2d7", // warm hairline
  borderStrong: "#d9d3c5",

  ink: "#1b1b1b",
  muted: "#6e695e",
  faint: "#9a9486",

  vital: "#ff5a1f", // primary — vivid orange
  vitalSoft: "#e84e12",
  ai: "#575ecf", // agentic / AI — indigo
  aiSoft: "#4248b8",

  good: "#4e8c6a", // sage green
  watch: "#c57e1a", // amber
  risk: "#dc4a2b", // terracotta / coral

  coral: "#fe3f21",
  magenta: "#f858bc",
  amber: "#fe7b02",
  indigo: "#575ecf",
  sage: "#5e8c77",

  // dark ink panels used for high-contrast hero / closing beats
  inkPanel: "#141310",
  inkPanel2: "#1f1d17",
} as const;

export const fonts = {
  serif: "var(--font-serif)",
  sans: "var(--font-sans)",
  mono: "var(--font-mono)",
} as const;

// 30fps everywhere.
export const FPS = 30;

// Convert seconds to whole frames.
export const sec = (s: number) => Math.round(s * FPS);
