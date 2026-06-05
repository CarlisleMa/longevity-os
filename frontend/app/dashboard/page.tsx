"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, DEMO_USER } from "@/lib/api";
import { BiologicalAgeScorecard } from "@/components/biological-age-scorecard";
import { CouplingCard } from "@/components/coupling-card";
import { InterventionCard } from "@/components/intervention-card";
import { EvidenceChip } from "@/components/evidence-chip";
import { Card, CardLabel } from "@/components/ui/card";
import { statusColor } from "@/lib/utils";
import { Sparkles } from "lucide-react";

export default function DashboardPage() {
  const qc = useQueryClient();
  const dash = useQuery({ queryKey: ["dashboard"], queryFn: () => api.dashboard(DEMO_USER) });
  const interventions = useQuery({
    queryKey: ["interventions"],
    queryFn: () => api.interventions(DEMO_USER),
  });

  if (dash.isLoading) return <Skeleton />;
  if (dash.isError || !dash.data)
    return (
      <div className="mt-10 rounded-xl border border-risk/30 bg-risk/10 p-5 text-sm text-risk">
        Couldn’t reach the API. Is the backend running on <code>:8000</code>?
      </div>
    );

  const d = dash.data;

  async function accept(id: string) {
    await api.acceptIntervention(DEMO_USER, id);
    qc.invalidateQueries({ queryKey: ["interventions"] });
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{d.display_name}</h1>
          <p className="text-sm text-muted">Your longevity dashboard</p>
        </div>
      </div>

      <BiologicalAgeScorecard s={d.scorecard} />

      {/* Latest agent insight */}
      {d.latest_observation && (
        <Card className="border-ai/30">
          <div className="flex items-start gap-3">
            <span className="mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-ai/15 text-ai">
              <Sparkles size={16} />
            </span>
            <div>
              <CardLabel className="text-ai">Latest agent insight</CardLabel>
              <p className="mt-1 text-sm leading-relaxed">{d.latest_observation.text}</p>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {d.latest_observation.evidence_cards.map((c) => (
                  <EvidenceChip key={c} id={c} />
                ))}
              </div>
            </div>
          </div>
        </Card>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Systems */}
        <Card>
          <CardLabel>System aging</CardLabel>
          <ul className="mt-3 flex flex-col gap-3">
            {d.systems.map((sys) => (
              <li key={sys.system} className="flex items-center gap-3">
                <span className="w-24 shrink-0 text-sm capitalize">{sys.system}</span>
                <div className="relative h-2 flex-1 overflow-hidden rounded-full bg-surface-2">
                  <div
                    className="absolute inset-y-0 left-1/2 rounded-full bg-current opacity-70"
                    style={{
                      width: `${Math.min(Math.abs(sys.age_accel) * 6, 50)}%`,
                      transform: sys.age_accel < 0 ? "translateX(-100%)" : "none",
                    }}
                  />
                </div>
                <span className={`w-14 text-right font-mono text-xs ${statusColor(sys.status)}`}>
                  {sys.age_accel > 0 ? "+" : "−"}
                  {Math.abs(sys.age_accel).toFixed(1)}
                </span>
              </li>
            ))}
          </ul>
        </Card>

        <CouplingCard metrics={d.coupling} />
      </div>

      {/* Interventions */}
      <section>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-semibold">Recommended interventions</h2>
          <span className="text-xs text-muted">each passes 3 safety gates</span>
        </div>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {interventions.data?.map((iv) => (
            <InterventionCard key={iv.id} iv={iv} onAccept={accept} />
          ))}
        </div>
      </section>
    </div>
  );
}

function Skeleton() {
  return (
    <div className="mt-6 flex flex-col gap-6">
      <div className="h-44 animate-pulse rounded-2xl border border-border bg-surface" />
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="h-56 animate-pulse rounded-xl border border-border bg-surface" />
        <div className="h-56 animate-pulse rounded-xl border border-border bg-surface" />
      </div>
    </div>
  );
}
