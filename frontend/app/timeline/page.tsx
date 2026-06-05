"use client";

import { useQuery } from "@tanstack/react-query";
import { api, DEMO_USER } from "@/lib/api";
import { PageHeader } from "@/components/page-header";
import { Card, CardLabel } from "@/components/ui/card";
import { DayTimeline } from "@/components/day-timeline";
import { TrajectoryChart } from "@/components/trajectory-chart";
import { Reveal } from "@/components/motion";
import { LoadingState, ErrorState } from "@/components/states";
import { signed } from "@/lib/utils";

export default function TimelinePage() {
  const day = useQuery({ queryKey: ["day"], queryFn: () => api.day(DEMO_USER) });
  const traj = useQuery({ queryKey: ["timeline"], queryFn: () => api.timeline(DEMO_USER) });

  if (day.isLoading || traj.isLoading) return <LoadingState />;
  if (day.isError || traj.isError || !traj.data) return <ErrorState />;

  const scored = (traj.data ?? []).filter((e) => e.biological_age != null);
  const baseline = scored[0]?.biological_age ?? null;

  return (
    <div>
      <PageHeader
        eyebrow="Your day, auto-synced"
        title="Timeline"
        subtitle="Every health activity on one animated 24-hour window — exercise, meals, supplements, light, behavior — with the glucose and heart-rate response underneath. Drag to reschedule, hit Replay to scan the day, click anything to see how your body responded."
      />

      {day.data && (
        <Reveal>
          <DayTimeline day={day.data} />
        </Reveal>
      )}

      {/* Long-term N-of-1 trajectory */}
      <div className="mt-12">
        <h2 className="font-serif text-xl font-medium">Long-term trajectory</h2>
        <p className="mt-1 max-w-2xl text-sm text-muted">
          Each ingest event is a snapshot. We lead with change against your own baseline — a cleaner
          signal than a single cohort-relative score.
        </p>

        <Reveal>
          <Card className="mt-4">
            <div className="flex items-center justify-between">
              <CardLabel>Biological age over time</CardLabel>
              {baseline != null && (
                <span className="text-[11px] text-faint">baseline {baseline.toFixed(1)} yrs</span>
              )}
            </div>
            <div className="mt-3">
              <TrajectoryChart events={traj.data} />
            </div>
          </Card>
        </Reveal>

        <div className="mt-6 flex flex-col gap-3">
          {traj.data.map((e, i) => {
            const delta =
              e.biological_age != null && baseline != null ? e.biological_age - baseline : null;
            const isLatest = i === traj.data.length - 1;
            return (
              <div
                key={e.timestamp}
                className="flex items-center gap-4 rounded-2xl border border-border bg-surface p-4 shadow-card lift hover:border-border-strong"
              >
                <span
                  className={`grid h-3 w-3 shrink-0 place-items-center rounded-full ${
                    isLatest ? "bg-vital ring-4 ring-vital/15" : "bg-border-strong"
                  }`}
                />
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
                    <div className="font-mono text-lg font-semibold">{e.biological_age.toFixed(1)}</div>
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
            );
          })}
        </div>
      </div>
    </div>
  );
}
