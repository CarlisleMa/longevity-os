// Brand typography: Playfair Display (serif display), Inter (sans body),
// JetBrains Mono (metrics) — matching the LongevityOS app.
//
// Self-hosted via @fontsource (bundled by webpack) so NOTHING is fetched from
// the network at render time. The render container does TLS interception that
// the headless browser rejects, which broke @remotion/google-fonts — local
// fonts sidestep that entirely.
import "@fontsource/playfair-display/500.css";
import "@fontsource/playfair-display/600.css";
import "@fontsource/playfair-display/700.css";
import "@fontsource/playfair-display/600-italic.css";
import "@fontsource/inter/400.css";
import "@fontsource/inter/500.css";
import "@fontsource/inter/600.css";
import "@fontsource/inter/700.css";
import "@fontsource/jetbrains-mono/400.css";
import "@fontsource/jetbrains-mono/500.css";
import "@fontsource/jetbrains-mono/600.css";

const serif = "'Playfair Display', Georgia, serif";
const sans = "'Inter', system-ui, sans-serif";
const mono = "'JetBrains Mono', ui-monospace, monospace";

export const fontFamilies = { serif, sans, mono };

// CSS custom properties consumed throughout (theme.ts references these vars).
export const fontCssVars: React.CSSProperties = {
  // @ts-expect-error custom properties
  "--font-serif": serif,
  "--font-sans": sans,
  "--font-mono": mono,
};
