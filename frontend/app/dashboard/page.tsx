"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { api, DEMO_USER } from "@/lib/api";
import type { Observation } from "@/lib/types";
import { BiologicalAgeScorecard } from "@/components/biological-age-scorecard";
import { SystemRadar } from "@/components/system-radar";
import { CouplingCard } from "@/components/coupling-card";
import { InterventionCard } from "@/components/intervention-card";
import { EvidenceChip } from "@/components/evidence-chip";
import { Card, CardLabel } from "@/components/ui/card";
import { Reveal } from "@/components/motion";
import { statusTone } from "@/components/ui/badge";
import { LoadingState, ErrorState } from "@/components/states";
import { signed } from "@/lib/utils";
import { ArrowRight, RefreshCw, Sparkles } from "lucide-react";

export default function DashboardPage() {
  const dash = useQuery({ queryKey: ["dashboard"], queryFn: () => api.dashboard(DEMO_USER) });
  const interventions = useQuery({
    queryKey: ["interventions"],
    queryFn: () => api.interventions(DEMO_USER),
  });

  const [accepted, setAccepted] = useState<Set<string>>(new Set());
  const [dismissed, setDismissed] = useState<Set<string>>(new Set());
  const [freshObs, setFreshObs] = useState<Observation | null>(null);
  const [observing, setObserving] = useState(false);

  if (dash.isLoading) return <LoadingState />;
  if (dash.isError || !dash.data) return <ErrorState />;

  const d = dash.data;
  const observation = freshObs ?? d.latest_observation;

  function accept(id: string) {
    setAccepted((s) => new Set(s).add(id));
    api.acceptIntervention(DEMO_USER, id).catch(() => {});
  }
  function dismiss(id: string) {
    setDismissed((s) => new Set(s).add(id));
    api.dismissIntervention(DEMO_USER, id).catch(() => {});
  }
  async function regenerate() {
    setObserving(true);
    try {
      setFreshObs(await api.observe(DEMO_USER));
    } finally {
      setObserving(false);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <div className="text-[11px] font-semibold uppercase tracking-[0.12em] text-vital-soft">
          Your longevity dashboard
        </div>
        <h1 className="mt-1 font-serif text-3xl font-medium tracking-tight">{d.display_name}</h1>
      </div>

      <BiologicalAgeScorecard s={d.scorecard} />

      {/* Latest agent insight */}
      {observation && (
        <Reveal>
          <Card className="border-ai/25 bg-gradient-to-br from-surface to-ai/[0.03]">
            <div className="flex items-start gap-3">
              <span className="mt-0.5 grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-ai/12 text-ai">
                <Sparkles size={17} />
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between gap-3">
                  <CardLabel className="text-ai">Latest agent insight</CardLabel>
                  <button
                    onClick={regenerate}
                    disabled={observing}
                    className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs text-muted transition-colors hover:bg-surface-2 hover:text-fg disabled:opacity-50"
                  >
                    <RefreshCw size={12} className={observing ? "animate-spin" : ""} />
                    {observing ? "Thinking…" : "Re-observe"}
                  </button>
                </div>
                <p className="mt-1.5 text-sm leading-relaxed">{observation.text}</p>
                <div className="mt-2.5 flex flex-wrap gap-1.5">
                  {observation.evidence_cards.map((c) => (
                    <EvidenceChip key={c} id={c} />
                  ))}
                </div>
              </div>
            </div>
          </Card>
        </Reveal>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        {/* System aging — radar */}
        <Reveal>
          <Card>
            <div className="flex items-center justify-between">
              <CardLabel>System aging</CardLabel>
              <span className="text-[11px] text-faint">outer ring = younger</span>
            </div>
            <SystemRadar systems={d.systems} />
            <div className="mt-2 flex flex-wrap gap-1.5">
              {d.systems.map((s) => (
                <span
                  key={s.system}
                  className="inline-flex items-center gap-1.5 rounded-md border border-border bg-surface-2/50 px-2 py-1 text-[11px]"
                >
                  <span className="capitalize text-muted">{s.system}</span>
                  <span
                    className={`font-mono ${
                      statusTone(s.status) === "good"
                        ? "text-good"
                        : statusTone(s.status) === "watch"
                          ? "text-watch"
                          : "text-risk"
                    }`}
                  >
                    {signed(s.age_accel)}
                  </span>
                </span>
              ))}
            </div>
          </Card>
        </Reveal>

        <Reveal delay={0.06}>
          <CouplingCard metrics={d.coupling} />
        </Reveal>
      </div>

      {/* Interventions */}
      <section>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="font-serif text-xl font-medium">Recommended interventions</h2>
          <Link
            href="/interventions"
            className="inline-flex items-center gap-1 text-sm text-muted transition-colors hover:text-fg"
          >
            View all <ArrowRight size={14} />
          </Link>
        </div>
        {interventions.isLoading ? (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {[0, 1, 2].map((i) => (
              <div
                key={i}
                className="h-64 animate-pulse rounded-2xl border border-border bg-surface shimmer"
              />
            ))}
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {interventions.data
              ?.filter((iv) => !dismissed.has(iv.id))
              .map((iv) => (
                <Reveal key={iv.id}>
                  <InterventionCard
                    iv={accepted.has(iv.id) ? { ...iv, status: "accepted" } : iv}
                    onAccept={accept}
                    onDismiss={dismiss}
                  />
                </Reveal>
              ))}
          </div>
        )}
      </section>
    </div>
  );
}
