import { Inter, JetBrains_Mono, Playfair_Display } from "next/font/google";

// Body / UI — clean grotesque (the showcase site's base face).
export const inter = Inter({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-inter",
});

// Metrics / numerals — monospaced so figures align and read as data.
export const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-mono-jb",
});

// Display headlines — editorial serif for the science-journal voice.
export const playfair = Playfair_Display({
  subsets: ["latin"],
  display: "swap",
  weight: ["400", "500", "600", "700"],
  variable: "--font-playfair",
});
