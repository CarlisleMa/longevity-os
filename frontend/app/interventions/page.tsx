"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, DEMO_USER } from "@/lib/api";
import type { Intervention } from "@/lib/types";
import { PageHeader } from "@/components/page-header";
import { InterventionCard } from "@/components/intervention-card";
import { Reveal } from "@/components/motion";
import { LoadingState, ErrorState } from "@/components/states";
import { cn } from "@/lib/utils";
import { ShieldCheck } from "lucide-react";

type Tab = "recommended" | "tracking";

export default function InterventionsPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["interventions"],
    queryFn: () => api.interventions(DEMO_USER),
  });

  const [accepted, setAccepted] = useState<Set<string>>(new Set());
  const [dismissed, setDismissed] = useState<Set<string>>(new Set());
  const [tab, setTab] = useState<Tab>("recommended");

  async function accept(id: string) {
    setAccepted((s) => new Set(s).add(id));
    setTab("tracking");
    try {
      await api.acceptIntervention(DEMO_USER, id);
    } catch {
      /* optimistic */
    }
  }
  async function dismiss(id: string) {
    setDismissed((s) => new Set(s).add(id));
    try {
      await api.dismissIntervention(DEMO_USER, id);
    } catch {
      /* optimistic */
    }
  }

  const { recommended, tracking } = useMemo(() => {
    const items = data ?? [];
    const rec: Intervention[] = [];
    const trk: Intervention[] = [];
    for (const iv of items) {
      if (dismissed.has(iv.id)) continue;
      if (accepted.has(iv.id)) trk.push({ ...iv, status: "tracking" });
      else rec.push(iv);
    }
    return { recommended: rec, tracking: trk };
  }, [data, accepted, dismissed]);

  if (isLoading) return <LoadingState />;
  if (isError || !data) return <ErrorState />;

  const list = tab === "recommended" ? recommended : tracking;

  return (
    <div>
      <PageHeader
        eyebrow="Evidence-grounded · gated"
        title="Interventions"
        subtitle="Each recommendation clears three gates — evidence-grounding, personalization, and safety — before it ever reaches you."
      >
        <span className="inline-flex items-center gap-1.5 rounded-full border border-good/25 bg-good/8 px-3 py-1.5 text-xs font-medium text-good">
          <ShieldCheck size={14} /> 3-gate safety pipeline
        </span>
      </PageHeader>

      <div className="mb-6 inline-flex rounded-lg border border-border bg-surface p-1 text-sm">
        {(["recommended", "tracking"] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={cn(
              "rounded-md px-4 py-1.5 capitalize transition-colors",
              tab === t ? "bg-surface-2 font-medium text-fg" : "text-muted hover:text-fg",
            )}
          >
            {t}
            {t === "tracking" && tracking.length > 0 && (
              <span className="ml-1.5 rounded-full bg-good/15 px-1.5 text-[11px] text-good">
                {tracking.length}
              </span>
            )}
          </button>
        ))}
      </div>

      {list.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-border-strong bg-surface p-10 text-center text-sm text-muted">
          {tab === "recommended"
            ? "No open recommendations — you've actioned them all."
            : "Nothing tracked yet. Accept a recommendation to start tracking it."}
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {list.map((iv) => (
            <Reveal key={iv.id}>
              <InterventionCard
                iv={iv}
                onAccept={accept}
                onDismiss={tab === "recommended" ? dismiss : undefined}
              />
            </Reveal>
          ))}
        </div>
      )}

      {tab === "tracking" && (
        <p className="mt-6 text-xs text-faint">
          Outcome logging (did the intervention work?) is on the roadmap — adherence and re-measure
          come next.
        </p>
      )}
    </div>
  );
}
