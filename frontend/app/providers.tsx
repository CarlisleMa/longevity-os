"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { api, DEMO_USER } from "@/lib/api";

export function Providers({ children }: { children: React.ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            // Keep fetched data fresh for the session so moving between pages
            // doesn't re-hit the API; survive a slow first request (cold start).
            staleTime: 5 * 60_000,
            gcTime: 30 * 60_000,
            refetchOnWindowFocus: false,
            retry: 2,
            retryDelay: (n) => Math.min(1000 * 2 ** n, 8000),
          },
        },
      }),
  );

  // Warm every page's data in parallel as soon as the app opens, so navigating
  // to any subpage is instant instead of showing a fresh loading skeleton.
  useEffect(() => {
    const u = DEMO_USER;
    const tasks: [readonly string[], () => Promise<unknown>][] = [
      [["dashboard"], () => api.dashboard(u)],
      [["interventions"], () => api.interventions(u)],
      [["day"], () => api.day(u)],
      [["timeline"], () => api.timeline(u)],
      [["knowledge-base"], () => api.knowledgeBase(u)],
      [["knowledge-cards"], () => api.knowledgeCards()],
      [["coach-roster"], () => api.coachRoster()],
      [["meta"], () => api.meta()],
    ];
    for (const [queryKey, queryFn] of tasks) {
      client.prefetchQuery({ queryKey, queryFn }).catch(() => {});
    }
  }, [client]);

  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}
