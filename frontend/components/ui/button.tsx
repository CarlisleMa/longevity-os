import { cn } from "@/lib/utils";

type Variant = "primary" | "solid" | "outline" | "ghost";
type Size = "sm" | "md" | "lg";

const base =
  "inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-all focus-visible:outline-none disabled:opacity-50 disabled:pointer-events-none whitespace-nowrap";

const variants: Record<Variant, string> = {
  // headline action — warm orange→indigo wash
  primary:
    "bg-gradient-to-r from-vital to-ai text-white shadow-[0_6px_20px_-8px_color-mix(in_srgb,var(--vital)_60%,transparent)] hover:brightness-[1.05] hover:-translate-y-px active:translate-y-0",
  solid: "bg-vital text-white hover:bg-vital-soft hover:-translate-y-px active:translate-y-0",
  outline: "border border-border-strong bg-surface text-fg hover:bg-surface-2 hover:border-fg/20",
  ghost: "text-muted hover:bg-surface-2 hover:text-fg",
};

const sizes: Record<Size, string> = {
  sm: "h-8 px-3 text-sm",
  md: "h-10 px-4 text-sm",
  lg: "h-12 px-6 text-base",
};

/** Shared classes so <Link> can look identical to <Button>. */
export function buttonClass(variant: Variant = "primary", size: Size = "md", className?: string) {
  return cn(base, variants[variant], sizes[size], className);
}

export function Button({
  variant = "primary",
  size = "md",
  className,
  ...props
}: { variant?: Variant; size?: Size } & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return <button className={buttonClass(variant, size, className)} {...props} />;
}
