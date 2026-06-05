"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity } from "lucide-react";
import { cn } from "@/lib/utils";
import { buttonClass } from "@/components/ui/button";

const links = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/timeline", label: "Timeline" },
  { href: "/coach", label: "Coach" },
  { href: "/knowledge-base", label: "Knowledge Base" },
  { href: "/interventions", label: "Interventions" },
  { href: "/about", label: "About" },
];

export function Nav() {
  const pathname = usePathname();
  return (
    <header className="sticky top-0 z-30 border-b border-border/70 bg-bg/80 backdrop-blur-md">
      <div className="mx-auto flex w-full max-w-6xl items-center justify-between gap-4 px-5 py-3">
        <Link href="/" className="flex shrink-0 items-center gap-2 font-semibold tracking-tight">
          <span className="grid h-7 w-7 place-items-center rounded-lg bg-gradient-to-br from-vital to-ai text-white shadow-glow">
            <Activity size={15} />
          </span>
          <span className="text-[15px]">LongevityOS</span>
        </Link>

        <nav className="hidden items-center gap-0.5 text-sm md:flex">
          {links.map((l) => {
            const active = pathname === l.href || pathname.startsWith(l.href + "/");
            return (
              <Link
                key={l.href}
                href={l.href}
                className={cn(
                  "rounded-md px-3 py-1.5 transition-colors",
                  active ? "bg-surface-2 font-medium text-fg" : "text-muted hover:text-fg",
                )}
              >
                {l.label}
              </Link>
            );
          })}
        </nav>

        <Link href="/onboarding" className={buttonClass("primary", "sm", "shrink-0")}>
          Try the demo
        </Link>
      </div>

      {/* Mobile row */}
      <nav className="flex items-center gap-1 overflow-x-auto border-t border-border/60 px-4 py-2 text-sm md:hidden">
        {links.map((l) => {
          const active = pathname === l.href || pathname.startsWith(l.href + "/");
          return (
            <Link
              key={l.href}
              href={l.href}
              className={cn(
                "whitespace-nowrap rounded-md px-3 py-1 transition-colors",
                active ? "bg-surface-2 font-medium text-fg" : "text-muted",
              )}
            >
              {l.label}
            </Link>
          );
        })}
      </nav>
    </header>
  );
}
