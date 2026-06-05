import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function statusColor(status?: string) {
  switch (status) {
    case "watch":
      return "text-watch";
    case "risk":
      return "text-risk";
    default:
      return "text-good";
  }
}

/** Format a signed delta with an explicit + / − and fixed precision. */
export function signed(n: number | null | undefined, digits = 1) {
  if (n === null || n === undefined) return "—";
  const s = n > 0 ? "+" : n < 0 ? "−" : "";
  return `${s}${Math.abs(n).toFixed(digits)}`;
}
