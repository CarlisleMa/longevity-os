"use client";

import { useQuery } from "@tanstack/react-query";
import { api, DEMO_USER } from "@/lib/api";
import type { KnowledgeBaseItem } from "@/lib/types";
import { PageHeader } from "@/components/page-header";
import { Card, CardLabel } from "@/components/ui/card";
import { KnowledgeCard } from "@/components/knowledge-card";
import { EvidenceChip } from "@/components/evidence-chip";
import { Reveal } from "@/components/motion";
import { LoadingState, ErrorState } from "@/components/states";
import {
  Activity,
  Droplet,
  Eye,
  HeartPulse,
  Minus,
  Stethoscope,
  TrendingDown,
  TrendingUp,
  Wind,
  type LucideIcon,
} from "lucide-react";

const MODALITY: Record<string, { icon: LucideIcon; label: string }> = {
  glucose: { icon: Droplet, label: "Glucose" },
  wearable: { icon: Activity, label: "Wearable" },
  cardiac: { icon: HeartPulse, label: "Cardiac" },
  retinal: { icon: Eye, label: "Retinal" },
  clinical: { icon: Stethoscope, label: "Clinical" },
  environment: { icon: Wind, label: "Environment" },
};

function Trend({ trend }: { trend?: string | null }) {
  if (trend === "up") return <TrendingUp size={13} className="text-muted" />;
  if (trend === "down") return <TrendingDown size={13} className="text-muted" />;
  return <Minus size={13} className="text-faint" />;
}

export default function KnowledgeBasePage() {
  const kb = useQuery({
    queryKey: ["knowledge-base"],
    queryFn: () => api.knowledgeBase(DEMO_USER),
  });
  const cards = useQuery({ queryKey: ["knowledge-cards"], queryFn: () => api.knowledgeCards() });

  if (kb.isLoading) return <LoadingState />;
  if (kb.isError || !kb.data) return <ErrorState />;

  const groups = Object.entries(kb.data.groups);

  return (
    <div>
      <PageHeader
        eyebrow="Everything we know about you"
        title="Knowledge base"
        subtitle="Your record, grouped by modality and growing by ingest date. Each interpretation is tied to a research evidence card you can open below."
      />

      <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
        {groups.map(([modality, items], gi) => {
          const meta = MODALITY[modality] ?? { icon: Activity, label: modality };
          const Icon = meta.icon;
          return (
            <Reveal key={modality} delay={gi * 0.05}>
              <Card hover className="h-full">
                <div className="flex items-center gap-2">
                  <span className="grid h-8 w-8 place-items-center rounded-lg bg-surface-2 text-vital-soft">
                    <Icon size={16} />
                  </span>
                  <CardLabel className="text-faint">{meta.label}</CardLabel>
                </div>
                <ul className="mt-3 flex flex-col divide-y divide-border/70">
                  {(items as KnowledgeBaseItem[]).map((item, i) => (
                    <li key={i} className="flex flex-col gap-1 py-2.5 first:pt-1 last:pb-0">
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-sm">{item.label}</span>
                        <span className="flex items-center gap-1.5">
                          <Trend trend={item.trend} />
                          <span className="font-mono text-sm tabular-nums">{item.value}</span>
                        </span>
                      </div>
                      <div className="flex items-center justify-between gap-2">
                        {item.evidence_card ? (
                          <EvidenceChip id={item.evidence_card} />
                        ) : (
                          <span />
                        )}
                        {item.as_of && (
                          <span className="text-[11px] text-faint">as of {item.as_of}</span>
                        )}
                      </div>
                    </li>
                  ))}
                </ul>
              </Card>
            </Reveal>
          );
        })}
      </div>

      {/* Evidence library */}
      <div className="mt-16">
        <PageHeader
          eyebrow="The research behind the reads"
          title="Evidence library"
          subtitle="Validated (and refuted) findings from the AI-READI research engine, distilled into priors the agent cites. The system records negative evidence too."
        />
        {cards.isLoading ? (
          <div className="grid gap-5 md:grid-cols-2">
            {[0, 1, 2, 3].map((i) => (
              <div
                key={i}
                className="h-44 animate-pulse rounded-2xl border border-border bg-surface shimmer"
              />
            ))}
          </div>
        ) : (
          <div className="grid items-start gap-5 md:grid-cols-2">
            {cards.data?.map((card, i) => (
              <Reveal key={card.id} delay={(i % 2) * 0.05}>
                <KnowledgeCard card={card} />
              </Reveal>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
