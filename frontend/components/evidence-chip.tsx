import { BookOpen } from "lucide-react";

/** Links a UI claim to a research knowledge card — the trust primitive. */
export function EvidenceChip({ id }: { id: string }) {
  return (
    <span
      title={`Evidence: ${id}`}
      className="inline-flex items-center gap-1 rounded-md border border-ai/30 bg-ai/10 px-2 py-0.5 font-mono text-[11px] text-ai"
    >
      <BookOpen size={11} />
      {id}
    </span>
  );
}
