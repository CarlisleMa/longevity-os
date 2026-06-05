"use client";

import { useQuery } from "@tanstack/react-query";
import { api, DEMO_USER } from "@/lib/api";
import { PageHeader } from "@/components/page-header";
import { Card, CardLabel } from "@/components/ui/card";
import { TrajectoryChart } from "@/components/trajectory-chart";
import { Reveal } from "@/components/motion";
import { LoadingState, ErrorState } from "@/components/states";
import { signed } from "@/lib/utils";

export default function TimelinePage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["timeline"],
    queryFn: () => api.timeline(DEMO_USER),
  });

  if (isLoading) return <LoadingState />;
  if (isError || !data) return <ErrorState />;

  const scored = data.filter((e) => e.biological_age != null);
  const baseline = scored[0]?.biological_age ?? null;

  return (
    <div>
      <PageHeader
        eyebrow="Your N-of-1 trajectory"
        title="Timeline"
        subtitle="Every ingest event is a snapshot. We lead with change against your own baseline — a cleaner, more honest signal than a single cohort-relative score."
      />

      <Reveal>
        <Card>
          <div className="flex items-center justify-between">
            <CardLabel>Biological age over time</CardLabel>
            {baseline != null && (
              <span className="text-[11px] text-faint">
                baseline {baseline.toFixed(1)} yrs
              </span>
            )}
          </div>
          <div className="mt-3">
            <TrajectoryChart events={data} />
          </div>
        </Card>
      </Reveal>

      <div className="mt-6 flex flex-col gap-3">
        {data.map((e, i) => {
          const delta =
            e.biological_age != null && baseline != null ? e.biological_age - baseline : null;
          const isLatest = i === data.length - 1;
          return (
            <Reveal key={e.timestamp} delay={i * 0.05}>
              <div className="flex items-center gap-4 rounded-2xl border border-border bg-surface p-4 shadow-card lift hover:border-border-strong">
                <div className="flex flex-col items-center">
                  <span
                    className={`grid h-3 w-3 place-items-center rounded-full ${
                      isLatest ? "bg-vital ring-4 ring-vital/15" : "bg-border-strong"
                    }`}
                  />
                </div>
                <div className="w-28 shrink-0">
                  <div className="font-mono text-xs text-faint">{e.timestamp}</div>
                  <div className="text-sm font-medium">{e.label}</div>
                </div>
                <div className="flex flex-1 flex-wrap gap-1.5">
                  {e.modalities_present.map((m) => (
                    <span
                      key={m}
                      className="rounded-md border border-border bg-surface-2/60 px-2 py-0.5 text-[11px] capitalize text-muted"
                    >
                      {m}
                    </span>
                  ))}
                </div>
                {e.biological_age != null && (
                  <div className="shrink-0 text-right">
                    <div className="font-mono text-lg font-semibold">
                      {e.biological_age.toFixed(1)}
                    </div>
                    {delta != null && (
                      <div
                        className={`font-mono text-[11px] ${
                          delta < 0 ? "text-good" : delta > 0 ? "text-watch" : "text-faint"
                        }`}
                      >
                        {signed(delta)} vs base
                      </div>
                    )}
                  </div>
                )}
              </div>
            </Reveal>
          );
        })}
      </div>
    </div>
  );
}
