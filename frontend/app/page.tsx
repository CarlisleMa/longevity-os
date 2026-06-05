import Link from "next/link";
import { ArrowRight, Upload, LineChart, Sparkles, ShieldCheck } from "lucide-react";
import { buttonClass } from "@/components/ui/button";
import { Reveal, CountUp } from "@/components/motion";

const steps = [
  {
    icon: Upload,
    title: "Upload",
    body: "Connect wearables, labs, imaging, and records — your data, kept private and local-first.",
  },
  {
    icon: LineChart,
    title: "Understand",
    body: "A growing knowledge base scores your multimodal aging and cross-system coupling against your own baseline.",
  },
  {
    icon: Sparkles,
    title: "Act",
    body: "Evidence-grounded interventions, each gated for safety and tied to a validated finding.",
  },
];

const biomarkers = ["VO₂max", "HbA1c", "RHR 58", "HRV", "TIR 82%", "ApoB", "Sleep 88%"];

export default function Landing() {
  return (
    <div className="flex flex-col gap-24 pt-6">
      {/* Hero */}
      <section className="grid items-center gap-12 lg:grid-cols-[1.1fr_0.9fr]">
        <div>
          <span className="inline-flex items-center gap-2 rounded-full border border-border bg-surface px-3 py-1 text-xs text-muted">
            <span className="h-1.5 w-1.5 rounded-full bg-vital" />
            Backed by a multimodal foundation model validated on 2,280 participants
          </span>
          <h1 className="mt-6 font-serif text-5xl font-medium leading-[1.05] tracking-tight sm:text-6xl">
            Your biology, <span className="text-gradient">understood</span>.
          </h1>
          <p className="mt-5 max-w-xl text-pretty text-lg leading-relaxed text-muted">
            LongevityOS turns validated longevity research into a private, growing model of you —
            and into evidence-grounded actions you can actually take.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-3">
            <Link href="/dashboard" className={buttonClass("primary", "lg")}>
              Explore the demo profile <ArrowRight size={17} />
            </Link>
            <Link href="/about" className={buttonClass("outline", "lg")}>
              How it works
            </Link>
          </div>
          <div className="mt-8 flex flex-wrap gap-2">
            {biomarkers.map((b) => (
              <span
                key={b}
                className="rounded-md border border-border bg-surface px-2.5 py-1 font-mono text-xs text-muted"
              >
                {b}
              </span>
            ))}
          </div>
        </div>

        {/* Faux scorecard preview */}
        <Reveal delay={0.1}>
          <div className="glow-vital relative">
            <div className="relative animate-float rounded-3xl border border-border bg-surface p-7 shadow-card">
              <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-faint">
                Biological age
              </div>
              <div className="mt-2 flex items-baseline gap-3">
                <CountUp
                  value={44.7}
                  decimals={1}
                  className="font-mono text-6xl font-semibold leading-none"
                />
                <span className="text-sm text-muted">vs 47 chronological</span>
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                <span className="inline-flex items-center gap-1 rounded-full bg-good/12 px-3 py-1 text-sm font-medium text-good">
                  −2.3 yrs younger
                </span>
                <span className="inline-flex items-center gap-1 rounded-full bg-surface-2 px-3 py-1 text-xs text-muted">
                  ↓ 0.4 vs your baseline
                </span>
              </div>
              <div className="mt-6 grid grid-cols-3 gap-2 text-center">
                {[
                  ["Cardiac", "−3.1", "good"],
                  ["Metabolic", "+1.8", "watch"],
                  ["Retinal", "−1.2", "good"],
                ].map(([sys, v, tone]) => (
                  <div key={sys} className="rounded-xl border border-border bg-surface-2/50 p-2.5">
                    <div className="text-[10px] text-faint">{sys}</div>
                    <div
                      className={`mt-0.5 font-mono text-sm font-medium ${
                        tone === "good" ? "text-good" : "text-watch"
                      }`}
                    >
                      {v}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </Reveal>
      </section>

      {/* How it works */}
      <section>
        <Reveal>
          <h2 className="font-serif text-2xl font-medium tracking-tight">
            From your data to your decisions.
          </h2>
        </Reveal>
        <div className="mt-6 grid gap-4 sm:grid-cols-3">
          {steps.map((s, i) => (
            <Reveal key={s.title} delay={i * 0.08}>
              <div className="h-full rounded-2xl border border-border bg-surface p-6 shadow-card lift hover:border-border-strong hover:shadow-card-hover">
                <div className="grid h-10 w-10 place-items-center rounded-xl bg-gradient-to-br from-vital/15 to-ai/15 text-vital-soft">
                  <s.icon size={20} />
                </div>
                <h3 className="mt-4 text-lg font-semibold">{s.title}</h3>
                <p className="mt-1.5 text-sm leading-relaxed text-muted">{s.body}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      {/* Research strip */}
      <Reveal>
        <section className="overflow-hidden rounded-3xl border border-border bg-surface p-8 paper-grid">
          <div className="grid gap-8 sm:grid-cols-3">
            <Stat n={27} label="Hypotheses tested — propose → critique → verify" />
            <Stat n={6} label="Modalities: glucose · wearable · ECG · retina · environment · clinical" />
            <Stat
              n={3}
              suffix=" gates"
              label="Every recommendation: evidence · personalized · safe"
            />
          </div>
          <div className="mt-6 flex items-center gap-2 border-t border-border pt-5 text-xs text-muted">
            <ShieldCheck size={14} className="text-good" />
            Wellness &amp; informational — not medical advice. Models validated on AI-READI; demo
            users are synthetic.
          </div>
        </section>
      </Reveal>
    </div>
  );
}

function Stat({ n, label, suffix }: { n: number; label: string; suffix?: string }) {
  return (
    <div>
      <div className="font-mono text-4xl font-semibold tracking-tight">
        <CountUp value={n} suffix={suffix} />
      </div>
      <div className="mt-2 text-sm text-muted">{label}</div>
    </div>
  );
}
