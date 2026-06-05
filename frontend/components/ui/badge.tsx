import { cn } from "@/lib/utils";

type Tone = "neutral" | "good" | "watch" | "risk" | "ai" | "vital";

const tones: Record<Tone, string> = {
  neutral: "border-border-strong bg-surface-2 text-muted",
  good: "border-good/25 bg-good/10 text-good",
  watch: "border-watch/30 bg-watch/10 text-watch",
  risk: "border-risk/30 bg-risk/10 text-risk",
  ai: "border-ai/30 bg-ai/10 text-ai",
  vital: "border-vital/30 bg-vital/10 text-vital-soft",
};

export function Badge({
  tone = "neutral",
  className,
  ...props
}: { tone?: Tone } & React.HTMLAttributes<HTMLSpanElement>) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium",
        tones[tone],
        className,
      )}
      {...props}
    />
  );
}

/** Map a backend status string ("good" | "watch" | "risk") to a Badge tone. */
export function statusTone(status?: string): Tone {
  if (status === "watch") return "watch";
  if (status === "risk") return "risk";
  return "good";
}

/** Map an evidence-strength to a tone for knowledge cards. */
export function strengthTone(strength?: string): Tone {
  switch (strength) {
    case "supported":
      return "good";
    case "completed":
      return "ai";
    case "exploratory":
      return "watch";
    case "refuted":
      return "risk";
    default:
      return "neutral";
  }
}
