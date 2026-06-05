import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "var(--bg)",
        surface: "var(--surface)",
        "surface-2": "var(--surface-2)",
        border: "var(--border)",
        "border-strong": "var(--border-strong)",
        fg: "var(--text)",
        muted: "var(--text-muted)",
        faint: "var(--text-faint)",
        vital: "var(--vital)",
        "vital-soft": "var(--vital-soft)",
        ai: "var(--ai)",
        "ai-soft": "var(--ai-soft)",
        good: "var(--good)",
        watch: "var(--watch)",
        risk: "var(--risk)",
        coral: "var(--coral)",
        magenta: "var(--magenta)",
        amber: "var(--amber)",
        indigo: "var(--indigo)",
        sage: "var(--sage)",
      },
      fontFamily: {
        sans: ["var(--font-sans)"],
        mono: ["var(--font-mono)"],
        serif: ["var(--font-serif)"],
      },
      borderRadius: {
        xl: "16px",
        "2xl": "20px",
        "3xl": "26px",
      },
      boxShadow: {
        // Soft, light-theme depth — paper with a faint cast shadow.
        card: "0 1px 2px rgba(27,27,27,0.04), 0 10px 30px -16px rgba(27,27,27,0.18)",
        "card-hover": "0 2px 4px rgba(27,27,27,0.05), 0 18px 44px -18px rgba(27,27,27,0.28)",
        glow: "0 8px 40px -12px color-mix(in srgb, var(--vital) 35%, transparent)",
      },
      keyframes: {
        "fade-rise": {
          "0%": { opacity: "0", transform: "translateY(10px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "scale-in": {
          "0%": { opacity: "0", transform: "scale(0.96)" },
          "100%": { opacity: "1", transform: "scale(1)" },
        },
        "stamp-in": {
          "0%": { opacity: "0", transform: "scale(0.8) rotate(-6deg)" },
          "60%": { opacity: "1", transform: "scale(1.06) rotate(1deg)" },
          "100%": { opacity: "1", transform: "scale(1) rotate(0)" },
        },
        float: {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-6px)" },
        },
      },
      animation: {
        "fade-rise": "fade-rise 0.5s cubic-bezier(0.22,1,0.36,1) both",
        "scale-in": "scale-in 0.4s cubic-bezier(0.22,1,0.36,1) both",
        "stamp-in": "stamp-in 0.45s cubic-bezier(0.22,1,0.36,1) both",
        float: "float 6s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;
