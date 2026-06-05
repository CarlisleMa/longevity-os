"use client";

import { useState } from "react";
import type { Intervention } from "@/lib/types";
import { EvidenceChip } from "./evidence-chip";
import { Check, ChevronDown, Shield } from "lucide-react";

const GATE_LABEL: Record<string, string> = {
  evidence_grounding: "Evidence-grounded",
  personalization: "Personalized",
  safety: "Safety",
};

export function InterventionCard({
  iv,
  onAccept,
}: {
  iv: Intervention;
  onAccept?: (id: string) => void;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className="rounded-xl border border-border bg-surface p-5 shadow-card animate-fade-rise">
      <div className="flex items-start justify-between gap-3">
        <h3 className="font-semibold">{iv.title}</h3>
        <span className="rounded-full bg-vital/15 px-2 py-0.5 text-[11px] font-medium text-vital">
          {iv.status}
        </span>
      </div>
      <p className="mt-1.5 text-sm leading-relaxed text-muted">{iv.rationale}</p>

      <div className="mt-3 flex flex-wrap gap-1.5">
        {iv.evidence_cards.map((c) => (
          <EvidenceChip key={c} id={c} />
        ))}
      </div>

      {/* The signature gate row */}
      <div className="mt-4 flex flex-wrap gap-2">
        {iv.gates.map((g) => (
          <span
            key={g.gate}
            title={g.note}
            className={`inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs ${
              g.passed ? "bg-good/12 text-good" : "bg-risk/12 text-risk"
            }`}
          >
            {g.passed ? <Check size={12} /> : <Shield size={12} />}
            {GATE_LABEL[g.gate] ?? g.gate}
          </span>
        ))}
      </div>

      <div className="mt-4 flex items-center justify-between text-xs text-muted">
        <span>
          {iv.expected_benefit && <>Expected: {iv.expected_benefit} · </>}
          {iv.effort && <>Effort: {iv.effort}</>}
        </span>
      </div>

      <div className="mt-4 flex items-center gap-2">
        <button
          onClick={() => onAccept?.(iv.id)}
          className="rounded-lg bg-gradient-to-r from-vital to-ai px-3 py-1.5 text-sm font-medium text-bg transition-transform hover:scale-[1.02]"
        >
          Accept
        </button>
        <button
          onClick={() => setOpen((o) => !o)}
          className="inline-flex items-center gap-1 rounded-lg border border-border px-3 py-1.5 text-sm transition-colors hover:bg-surface-2"
        >
          Why this? <ChevronDown size={14} className={open ? "rotate-180 transition-transform" : "transition-transform"} />
        </button>
      </div>

      {open && iv.reasoning_trace && (
        <div className="mt-3 rounded-lg border border-border bg-surface-2 p-3 text-xs leading-relaxed text-muted">
          <div className="mb-1 font-medium text-fg">Agent reasoning</div>
          {iv.reasoning_trace}
        </div>
      )}
    </div>
  );
}
