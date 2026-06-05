import { cn } from "@/lib/utils";

export function Card({
  className,
  hover = false,
  ...props
}: { hover?: boolean } & React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "rounded-2xl border border-border bg-surface p-5 shadow-card",
        hover && "lift hover:border-border-strong hover:shadow-card-hover",
        className,
      )}
      {...props}
    />
  );
}

export function CardLabel({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "text-[11px] font-semibold uppercase tracking-[0.08em] text-faint",
        className,
      )}
      {...props}
    />
  );
}
