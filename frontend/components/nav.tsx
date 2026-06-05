import Link from "next/link";
import { Activity } from "lucide-react";

const links = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/knowledge-base", label: "Knowledge Base" },
  { href: "/interventions", label: "Interventions" },
  { href: "/timeline", label: "Timeline" },
];

export function Nav() {
  return (
    <header className="sticky top-0 z-20 border-b border-border/60 bg-bg/80 backdrop-blur">
      <div className="mx-auto flex w-full max-w-6xl items-center justify-between px-5 py-3">
        <Link href="/" className="flex items-center gap-2 font-semibold tracking-tight">
          <span className="grid h-7 w-7 place-items-center rounded-lg bg-gradient-to-br from-vital to-ai text-bg">
            <Activity size={16} />
          </span>
          LongevityOS
        </Link>
        <nav className="flex items-center gap-1 text-sm text-muted">
          {links.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className="rounded-md px-3 py-1.5 transition-colors hover:bg-surface-2 hover:text-fg"
            >
              {l.label}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}
