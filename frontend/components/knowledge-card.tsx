"use client";

import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import type { KnowledgeCard as KC } from "@/lib/types";
import { Badge, strengthTone } from "./ui/badge";
import { ChevronDown, FlaskConical } from "lucide-react";

export function KnowledgeCard({ card }: { card: KC }) {
  const [open, setOpen] = useState(false);
  return (
    <div
      id={card.id}
      className="scroll-mt-28 rounded-2xl border border-border bg-surface p-5 shadow-card lift hover:border-border-strong"
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="font-mono text-[11px] text-faint">{card.id}</div>
          <h3 className="mt-1 font-serif text-lg font-medium leading-snug">{card.title}</h3>
        </div>
        <Badge tone={strengthTone(card.evidence_strength)} className="shrink-0 capitalize">
          {card.evidence_strength}
        </Badge>
      </div>

      <p className="mt-3 text-sm leading-relaxed text-muted">{card.finding}</p>

      {card.modalities?.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {card.modalities.map((m) => (
            <span
              key={m}
              className="rounded-md border border-border bg-surface-2/60 px-2 py-0.5 text-[11px] capitalize text-muted"
            >
              {m}
            </span>
          ))}
        </div>
      )}

      <button
        onClick={() => setOpen((o) => !o)}
        className="mt-4 inline-flex items-center gap-1 text-xs font-medium text-vital-soft transition-colors hover:text-vital"
      >
        {open ? "Less" : "How this applies to you"}
        <ChevronDown
          size={13}
          className={open ? "rotate-180 transition-transform" : "transition-transform"}
        />
      </button>

      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
            className="overflow-hidden"
          >
            <div className="mt-3 space-y-3 border-t border-border pt-3 text-sm leading-relaxed">
              <Field label="What it means">{card.interpretation}</Field>
              <Field label="For you">{card.individual_application}</Field>
              {card.caveats && (
                <div className="rounded-lg border border-watch/25 bg-watch/8 p-3 text-xs text-muted">
                  <span className="font-medium text-watch">Caveat · </span>
                  {card.caveats}
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="mt-4 flex items-center gap-1.5 border-t border-border/70 pt-3 text-[11px] text-faint">
        <FlaskConical size={12} />
        Source: {card.source?.system}
        {card.source?.ref ? ` · ${card.source.ref}` : ""}
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-faint">
        {label}
      </div>
      <p className="mt-1 text-muted">{children}</p>
    </div>
  );
}
