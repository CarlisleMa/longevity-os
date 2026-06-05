import type { Metadata } from "next";
import "./globals.css";
import { inter, jetbrainsMono, playfair } from "./fonts";
import { Providers } from "./providers";
import { Nav } from "@/components/nav";
import { Activity } from "lucide-react";

export const metadata: Metadata = {
  title: "LongevityOS — your biology, understood",
  description:
    "Upload your data, grow a private knowledge base, and get evidence-grounded interventions. Powered by a multimodal foundation model and agentic discovery engine.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      className={`${inter.variable} ${jetbrainsMono.variable} ${playfair.variable}`}
    >
      <body className="min-h-screen antialiased">
        <Providers>
          <Nav />
          <main className="mx-auto w-full max-w-6xl px-5 pb-24 pt-8">{children}</main>
          <footer className="border-t border-border/70">
            <div className="mx-auto flex w-full max-w-6xl flex-col gap-3 px-5 py-8 text-sm text-muted sm:flex-row sm:items-center sm:justify-between">
              <div className="flex items-center gap-2">
                <span className="grid h-6 w-6 place-items-center rounded-md bg-gradient-to-br from-vital to-ai text-white">
                  <Activity size={13} />
                </span>
                <span className="font-medium text-fg">LongevityOS</span>
              </div>
              <p className="text-xs leading-relaxed text-faint">
                <strong className="font-medium text-muted">Not medical advice.</strong> Models
                validated on AI-READI.
              </p>
            </div>
          </footer>
        </Providers>
      </body>
    </html>
  );
}
