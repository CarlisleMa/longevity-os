import Link from "next/link";
import { ArrowRight, Upload, LineChart, Sparkles } from "lucide-react";

const steps = [
  { icon: Upload, title: "Upload", body: "Connect wearables, labs, imaging, and records — your data, kept private." },
  { icon: LineChart, title: "Understand", body: "A growing knowledge base scores your multimodal aging and cross-system coupling." },
  { icon: Sparkles, title: "Act", body: "Evidence-grounded interventions, each gated for safety and tied to a finding." },
];

export default function Landing() {
  return (
    <div className="flex flex-col gap-20">
      {/* Hero */}
      <section className="glow-vital relative pt-10">
        <div className="relative z-10 mx-auto max-w-3xl text-center">
          <span className="inline-flex items-center gap-2 rounded-full border border-border bg-surface px-3 py-1 text-xs text-muted">
            <span className="h-1.5 w-1.5 rounded-full bg-vital" />
            Backed by a multimodal foundation model validated on 2,280 participants
          </span>
          <h1 className="mt-6 text-balance text-5xl font-semibold leading-tight tracking-tight sm:text-6xl">
            Your biology, <span className="bg-gradient-to-r from-vital to-ai bg-clip-text text-transparent">understood</span>.
          </h1>
          <p className="mx-auto mt-5 max-w-xl text-pretty text-lg text-muted">
            LongevityOS turns validated longevity research into a private, growing model of you —
            and into evidence-grounded actions you can actually take.
          </p>
          <div className="mt-8 flex items-center justify-center gap-3">
            <Link
              href="/dashboard"
              className="inline-flex items-center gap-2 rounded-lg bg-gradient-to-r from-vital to-ai px-5 py-2.5 font-medium text-bg transition-transform hover:scale-[1.02]"
            >
              Explore the demo profile <ArrowRight size={16} />
            </Link>
            <Link
              href="/about"
              className="rounded-lg border border-border px-5 py-2.5 font-medium text-fg transition-colors hover:bg-surface-2"
            >
              How it works
            </Link>
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="grid gap-4 sm:grid-cols-3">
        {steps.map((s) => (
          <div key={s.title} className="rounded-xl border border-border bg-surface p-6 shadow-card">
            <div className="grid h-10 w-10 place-items-center rounded-lg bg-surface-2 text-vital">
              <s.icon size={20} />
            </div>
            <h3 className="mt-4 text-lg font-semibold">{s.title}</h3>
            <p className="mt-1.5 text-sm text-muted">{s.body}</p>
          </div>
        ))}
      </section>

      {/* Research strip */}
      <section className="rounded-2xl border border-border bg-surface p-8">
        <div className="grid gap-6 sm:grid-cols-3">
          <Stat n="27" label="Hypotheses tested (propose → critique → verify)" />
          <Stat n="6" label="Modalities: glucose, wearable, ECG, retina, environment, clinical" />
          <Stat n="3 gates" label="Every recommendation: evidence · personalized · safe" />
        </div>
      </section>
    </div>
  );
}

function Stat({ n, label }: { n: string; label: string }) {
  return (
    <div>
      <div className="font-mono text-3xl font-semibold text-fg">{n}</div>
      <div className="mt-1 text-sm text-muted">{label}</div>
    </div>
  );
}
