import type { CouplingMetric } from "@/lib/types";
import { signed } from "@/lib/utils";
import { EvidenceChip } from "./evidence-chip";
import { Card, CardLabel } from "./ui/card";
import { ArrowDownRight, ArrowUpRight, Minus } from "lucide-react";

export function CouplingCard({ metrics }: { metrics: CouplingMetric[] }) {
  return (
    <Card>
      <CardLabel>Cross-modal coupling · vs your baseline</CardLabel>
      <ul className="mt-3 flex flex-col divide-y divide-border/70">
        {metrics.map((m) => {
          const delta = m.delta_vs_baseline ?? 0;
          const worse = delta < 0;
          const flat = Math.abs(delta) < 0.005;
          const Icon = flat ? Minus : worse ? ArrowDownRight : ArrowUpRight;
          const tone = flat ? "text-muted" : worse ? "text-watch" : "text-good";
          return (
            <li key={m.key} className="flex flex-col gap-1.5 py-3.5 first:pt-1 last:pb-0">
              <div className="flex items-center justify-between gap-3">
                <span className="text-sm font-medium">{m.label}</span>
                <span className="flex items-baseline gap-2">
                  <span className="font-mono text-sm tabular-nums">{m.value.toFixed(2)}</span>
                  <span
                    className={`inline-flex items-center gap-0.5 font-mono text-xs tabular-nums ${tone}`}
                    title="change vs your baseline"
                  >
                    <Icon size={12} />
                    {signed(delta, 2)}
                  </span>
                </span>
              </div>
              {m.read && <p className="text-xs leading-relaxed text-muted">{m.read}</p>}
              {m.evidence_card && (
                <div>
                  <EvidenceChip id={m.evidence_card} />
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </Card>
  );
}
