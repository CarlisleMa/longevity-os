import Link from "next/link";
import { BookOpen } from "lucide-react";

/** Links a UI claim to a research knowledge card — the trust primitive. */
export function EvidenceChip({ id }: { id: string }) {
  return (
    <Link
      href={`/knowledge-base#${id}`}
      title={`Evidence: ${id}`}
      className="inline-flex items-center gap-1 rounded-md border border-ai/25 bg-ai/8 px-2 py-0.5 font-mono text-[11px] text-ai transition-colors hover:border-ai/50 hover:bg-ai/15"
    >
      <BookOpen size={11} />
      {id}
    </Link>
  );
}
