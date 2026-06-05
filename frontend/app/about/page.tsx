import Link from "next/link";
import { PageHeader } from "@/components/page-header";
import { Card, CardLabel } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Reveal } from "@/components/motion";
import { buttonClass } from "@/components/ui/button";
import { Brain, FlaskConical, GitBranch, Layers, ShieldCheck } from "lucide-react";

const pillars = [
  {
    icon: Layers,
    title: "Multimodal foundation model",
    body: "A JEPA encoder trained on AI-READI shows aligned person-time windows beat wrong-day and shuffled-participant controls across 36 runs — real cross-modal physiology, not an artifact.",
  },
  {
    icon: GitBranch,
    title: "Agentic discovery engine",
    body: "A guarded multi-agent system with scientific, feasibility, and mechanical reviewer gates. Repointed here, those gates become your intervention safety pipeline.",
  },
  {
    icon: FlaskConical,
    title: "27 hypotheses",
    body: "A propose → critique → execute → verify backbone. Findings — including refuted ones — are distilled into evidence cards the agent must cite.",
  },
  {
    icon: Brain,
    title: "N-of-1 reasoning",
    body: "Cohort clocks give orientation; the product leads with within-person change against your own growing baseline — a cleaner signal for one person.",
  },
];

const ledger: { cap: string; state: string; tone: "good" | "ai" | "watch" | "neutral" }[] = [
  { cap: "Foundation model, validated on 2,280 participants", state: "Real (research)", tone: "good" },
  { cap: "Agentic discovery framework with reviewer gates", state: "Real (research)", tone: "good" },
  { cap: "Backend API + synthetic demo user end-to-end", state: "Real", tone: "good" },
  { cap: "Aging-clock scoring on an individual", state: "Wrapped", tone: "ai" },
  { cap: "Per-user knowledge base (growing, versioned)", state: "Wrapped", tone: "ai" },
  { cap: "Live agent reasoning + intervention generation", state: "Representative", tone: "watch" },
  { cap: "Foundation-model embeddings on your uploads", state: "Representative", tone: "watch" },
  { cap: "Real upload parsers (Apple Health, Garmin, labs…)", state: "Roadmap", tone: "neutral" },
  { cap: "Accounts / multi-user · outcome tracking", state: "Roadmap", tone: "neutral" },
];

export default function AboutPage() {
  return (
    <div>
      <PageHeader
        eyebrow="How it works"
        title="Research engine, turned on you."
        subtitle="AI-READI turns a population into knowledge. LongevityOS is the inverse — it turns that knowledge back onto one person who uploads their own data."
      />

      <Reveal>
        <Card className="paper-grid">
          <div className="grid gap-6 sm:grid-cols-2">
            <div>
              <CardLabel>The research engine</CardLabel>
              <p className="mt-2 text-sm leading-relaxed text-muted">
                Many people → models &amp; findings. Foundation model, validated coupling findings,
                a corpus of critiqued hypotheses. <span className="text-fg">Discovery.</span>
              </p>
            </div>
            <div>
              <CardLabel className="text-vital-soft">LongevityOS</CardLabel>
              <p className="mt-2 text-sm leading-relaxed text-muted">
                Models &amp; findings → one person&rsquo;s insight. We consume the frozen outputs —
                coefficients, reference distributions, evidence cards. <span className="text-fg">Application.</span>
              </p>
            </div>
          </div>
        </Card>
      </Reveal>

      <div className="mt-6 grid gap-5 sm:grid-cols-2">
        {pillars.map((p, i) => (
          <Reveal key={p.title} delay={i * 0.05}>
            <Card hover className="h-full">
              <div className="grid h-10 w-10 place-items-center rounded-xl bg-gradient-to-br from-vital/15 to-ai/15 text-vital-soft">
                <p.icon size={20} />
              </div>
              <h3 className="mt-4 text-lg font-semibold">{p.title}</h3>
              <p className="mt-1.5 text-sm leading-relaxed text-muted">{p.body}</p>
            </Card>
          </Reveal>
        ))}
      </div>

      {/* Honest ledger */}
      <div className="mt-16">
        <PageHeader
          eyebrow="Say the vision, show the slice, label the rest"
          title="What's real vs roadmap"
          subtitle="An integrity ledger, so the demo never overclaims."
        />
        <Reveal>
          <Card className="p-0">
            <ul className="divide-y divide-border/70">
              {ledger.map((row) => (
                <li
                  key={row.cap}
                  className="flex items-center justify-between gap-4 px-5 py-3.5 text-sm"
                >
                  <span>{row.cap}</span>
                  <Badge tone={row.tone} className="shrink-0">
                    {row.state}
                  </Badge>
                </li>
              ))}
            </ul>
          </Card>
        </Reveal>
      </div>

      <Reveal>
        <div className="mt-12 flex flex-col items-start gap-4 rounded-3xl border border-border bg-surface p-8 shadow-card sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h3 className="font-serif text-2xl font-medium">See it on a synthetic profile.</h3>
            <p className="mt-1.5 flex items-center gap-1.5 text-sm text-muted">
              <ShieldCheck size={15} className="text-good" /> Nothing private — everything runs on
              a synthetic person.
            </p>
          </div>
          <Link href="/dashboard" className={buttonClass("primary", "lg")}>
            Open the dashboard
          </Link>
        </div>
      </Reveal>
    </div>
  );
}
