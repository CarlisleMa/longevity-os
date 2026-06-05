import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "./providers";
import { Nav } from "@/components/nav";

export const metadata: Metadata = {
  title: "LongevityOS — your biology, understood",
  description:
    "Upload your data, grow a private knowledge base, and get evidence-grounded interventions. Powered by a multimodal foundation model and agentic discovery engine.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen antialiased">
        <Providers>
          <Nav />
          <main className="mx-auto w-full max-w-6xl px-5 pb-24 pt-6">{children}</main>
          <footer className="border-t border-border/60 py-6 text-center text-xs text-muted">
            LongevityOS is a wellness & informational prototype — <strong>not medical advice</strong>.
            Models validated on AI-READI; demo users are synthetic.
          </footer>
        </Providers>
      </body>
    </html>
  );
}
