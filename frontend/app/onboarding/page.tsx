"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import { PageHeader } from "@/components/page-header";
import { buttonClass } from "@/components/ui/button";
import { Check, Loader2, UploadCloud } from "lucide-react";

const sources = ["Apple Health", "Garmin Connect", "Fitbit", "Lab results (PDF/CSV)"];

const PROCESS = ["Parsing uploads", "Computing features", "Scoring biological age", "Ready"];

export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState(-1);

  useEffect(() => {
    if (step < 0) return;
    if (step >= PROCESS.length - 1) {
      const t = setTimeout(() => router.push("/dashboard"), 650);
      return () => clearTimeout(t);
    }
    const t = setTimeout(() => setStep((s) => s + 1), 600);
    return () => clearTimeout(t);
  }, [step, router]);

  const processing = step >= 0;

  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader
        eyebrow="Get started"
        title="Build your private model."
        subtitle="Connect your own exports, or explore the product on a demo profile. Your raw data stays local — only derived summaries are ever reasoned over."
      />

      {/* Dropzone */}
      <div className="grid place-items-center rounded-3xl border-2 border-dashed border-border-strong bg-surface p-12 text-center shadow-card">
        <span className="grid h-14 w-14 place-items-center rounded-2xl bg-gradient-to-br from-vital/15 to-ai/15 text-vital-soft">
          <UploadCloud size={26} />
        </span>
        <h3 className="mt-4 font-serif text-xl font-medium">Drop your health exports here</h3>
        <p className="mt-1 text-sm text-muted">
          Wearable archives, lab PDFs, OCT/ECG files — we normalize them into one record.
        </p>
        <span className="mt-3 text-xs text-faint">Or explore the demo profile below.</span>
      </div>

      {/* Source tiles */}
      <div className="mt-5 grid gap-3 sm:grid-cols-2">
        {sources.map((name) => (
          <div
            key={name}
            className="flex items-center justify-between rounded-xl border border-border bg-surface px-4 py-3 text-sm shadow-card transition-colors hover:border-border-strong"
          >
            <span>{name}</span>
            <span className="text-xs text-muted">Connect →</span>
          </div>
        ))}
      </div>

      {/* Demo path */}
      <div className="mt-8 flex flex-col items-center gap-4 rounded-3xl border border-vital/25 bg-gradient-to-br from-surface to-vital/[0.04] p-8 text-center shadow-card">
        <h3 className="font-serif text-2xl font-medium">Or explore with a demo profile</h3>
        <p className="max-w-md text-sm text-muted">
          Meet <span className="font-medium text-fg">Alex Rivera</span> — a sample profile with a
          full, real-shaped record.
        </p>
        <button
          onClick={() => setStep(0)}
          disabled={processing}
          className={buttonClass("primary", "lg", "disabled:opacity-70")}
        >
          {processing ? "Loading your dashboard…" : "Explore the demo profile"}
        </button>
      </div>

      {/* Processing overlay */}
      <AnimatePresence>
        {processing && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 grid place-items-center bg-bg/70 backdrop-blur-sm"
          >
            <motion.div
              initial={{ scale: 0.96, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              className="w-[320px] rounded-2xl border border-border bg-surface p-6 shadow-card-hover"
            >
              <ul className="flex flex-col gap-3">
                {PROCESS.map((label, i) => {
                  const done = i < step;
                  const active = i === step;
                  return (
                    <li key={label} className="flex items-center gap-3 text-sm">
                      <span
                        className={`grid h-6 w-6 place-items-center rounded-full ${
                          done
                            ? "bg-good/15 text-good"
                            : active
                              ? "bg-vital/15 text-vital-soft"
                              : "bg-surface-2 text-faint"
                        }`}
                      >
                        {done ? (
                          <Check size={13} />
                        ) : active ? (
                          <Loader2 size={13} className="animate-spin" />
                        ) : (
                          <span className="h-1.5 w-1.5 rounded-full bg-current" />
                        )}
                      </span>
                      <span className={done || active ? "text-fg" : "text-faint"}>{label}</span>
                    </li>
                  );
                })}
              </ul>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
