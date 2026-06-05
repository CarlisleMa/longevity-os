"use client";

import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import type { Intervention } from "@/lib/types";
import { EvidenceChip } from "./evidence-chip";
import { Badge } from "./ui/badge";
import { Check, ChevronDown, Shield, Sparkles, X } from "lucide-react";

const GATE_LABEL: Record<string, string> = {
  evidence_grounding: "Evidence-grounded",
  personalization: "Personalized",
  safety: "Safety",
};

const STATUS_TONE: Record<string, "vital" | "good" | "neutral"> = {
  new: "vital",
  accepted: "good",
  tracking: "good",
  dismissed: "neutral",
};

export function InterventionCard({
  iv,
  onAccept,
  onDismiss,
}: {
  iv: Intervention;
  onAccept?: (id: string) => void;
  onDismiss?: (id: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const accepted = iv.status === "accepted" || iv.status === "tracking";

  return (
    <div className="flex flex-col rounded-2xl border border-border bg-surface p-5 shadow-card lift hover:border-border-strong hover:shadow-card-hover">
      <div className="flex items-start justify-between gap-3">
        <h3 className="font-serif text-lg font-medium leading-snug">{iv.title}</h3>
        <Badge tone={STATUS_TONE[iv.status] ?? "neutral"} className="shrink-0 capitalize">
          {iv.status}
        </Badge>
      </div>
      <p className="mt-2 text-sm leading-relaxed text-muted">{iv.rationale}</p>

      {iv.evidence_cards.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {iv.evidence_cards.map((c) => (
            <EvidenceChip key={c} id={c} />
          ))}
        </div>
      )}

      {/* The signature gate row */}
      <div className="mt-4 flex flex-wrap gap-1.5">
        {iv.gates.map((g) => (
          <span
            key={g.gate}
            title={g.note}
            className={`inline-flex items-center gap-1 rounded-md border px-2 py-1 text-xs font-medium animate-stamp-in ${
              g.passed
                ? "border-good/25 bg-good/10 text-good"
                : "border-risk/30 bg-risk/10 text-risk"
            }`}
          >
            {g.passed ? <Check size={12} /> : <Shield size={12} />}
            {GATE_LABEL[g.gate] ?? g.gate}
          </span>
        ))}
      </div>

      {(iv.expected_benefit || iv.effort) && (
        <div className="mt-4 grid grid-cols-2 gap-2 text-xs">
          {iv.expected_benefit && (
            <div className="rounded-lg border border-border bg-surface-2/60 px-3 py-2">
              <div className="text-faint">Expected</div>
              <div className="mt-0.5 text-fg">{iv.expected_benefit}</div>
            </div>
          )}
          {iv.effort && (
            <div className="rounded-lg border border-border bg-surface-2/60 px-3 py-2">
              <div className="text-faint">Effort</div>
              <div className="mt-0.5 capitalize text-fg">{iv.effort}</div>
            </div>
          )}
        </div>
      )}

      <div className="mt-4 flex flex-1 items-end gap-2">
        <button
          onClick={() => onAccept?.(iv.id)}
          disabled={accepted}
          className="inline-flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-vital to-ai px-3.5 py-2 text-sm font-medium text-white transition-all hover:-translate-y-px hover:brightness-105 disabled:opacity-60 disabled:hover:translate-y-0"
        >
          {accepted ? <Check size={15} /> : null}
          {accepted ? "Accepted" : "Accept"}
        </button>
        {onDismiss && !accepted && (
          <button
            onClick={() => onDismiss(iv.id)}
            className="inline-flex items-center gap-1 rounded-lg border border-border px-3 py-2 text-sm text-muted transition-colors hover:bg-surface-2 hover:text-fg"
          >
            <X size={14} /> Dismiss
          </button>
        )}
        <button
          onClick={() => setOpen((o) => !o)}
          className="ml-auto inline-flex items-center gap-1 rounded-lg border border-border px-3 py-2 text-sm transition-colors hover:bg-surface-2"
        >
          Why this?
          <ChevronDown
            size={14}
            className={open ? "rotate-180 transition-transform" : "transition-transform"}
          />
        </button>
      </div>

      <AnimatePresence initial={false}>
        {open && iv.reasoning_trace && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
            className="overflow-hidden"
          >
            <div className="mt-3 rounded-xl border border-ai/20 bg-ai/5 p-3 text-xs leading-relaxed text-muted">
              <div className="mb-1 flex items-center gap-1.5 font-medium text-ai">
                <Sparkles size={13} /> Agent reasoning
              </div>
              {iv.reasoning_trace}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
