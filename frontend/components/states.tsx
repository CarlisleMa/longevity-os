export function LoadingState({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex flex-col gap-6">
      <div className="h-44 animate-pulse rounded-3xl border border-border bg-surface shimmer" />
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="h-56 animate-pulse rounded-2xl border border-border bg-surface shimmer" />
        <div className="h-56 animate-pulse rounded-2xl border border-border bg-surface shimmer" />
      </div>
      <span className="sr-only">{label}</span>
    </div>
  );
}

export function ErrorState() {
  return (
    <div className="mt-10 rounded-2xl border border-risk/30 bg-risk/8 p-6 text-sm text-risk">
      <p className="font-medium">Couldn&rsquo;t reach the API.</p>
      <p className="mt-1 text-risk/80">
        Start the backend, then refresh:{" "}
        <code className="rounded bg-risk/10 px-1.5 py-0.5 font-mono text-xs">
          uvicorn longevityos_api.main:app --reload --port 8000
        </code>
      </p>
    </div>
  );
}
