import type { ScoreCard } from "@/lib/types";
import { signed } from "@/lib/utils";
import { TrendingDown, TrendingUp } from "lucide-react";

export function BiologicalAgeScorecard({ s }: { s: ScoreCard }) {
  const younger = s.age_accel < 0;
  const improving = (s.delta_vs_baseline ?? 0) < 0;
  return (
    <div className="glow-vital relative overflow-hidden rounded-2xl border border-border bg-surface p-7 shadow-card animate-fade-rise">
      <div className="relative z-10 flex flex-wrap items-end justify-between gap-6">
        <div>
          <div className="text-xs font-medium uppercase tracking-wide text-muted">
            Biological age
          </div>
          <div className="mt-1 flex items-baseline gap-3">
            <span className="font-mono text-6xl font-semibold leading-none">
              {s.biological_age.toFixed(1)}
            </span>
            <span className="text-sm text-muted">vs {s.chronological_age.toFixed(0)} chronological</span>
          </div>
          <div className="mt-3 flex items-center gap-2">
            <span
              className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-sm font-medium ${
                younger ? "bg-good/15 text-good" : "bg-watch/15 text-watch"
              }`}
            >
              {younger ? <TrendingDown size={14} /> : <TrendingUp size={14} />}
              {signed(s.age_accel)} yrs {younger ? "younger" : "older"}
            </span>
            {s.age_accel_percentile != null && (
              <span className="text-xs text-muted">{s.age_accel_percentile.toFixed(0)}th percentile</span>
            )}
          </div>
        </div>

        {/* N-of-1 delta — the headline */}
        <div className="rounded-xl border border-border bg-surface-2 px-4 py-3">
          <div className="text-xs text-muted">vs your own baseline</div>
          <div
            className={`mt-0.5 font-mono text-2xl font-semibold ${improving ? "text-good" : "text-watch"}`}
          >
            {signed(s.delta_vs_baseline)} yrs
          </div>
          <div className="text-[11px] text-muted">as of {s.as_of}</div>
        </div>
      </div>
    </div>
  );
}
