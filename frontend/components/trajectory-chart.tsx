"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { TimelineEvent } from "@/lib/types";

const VITAL = "#ff5a1f";

export function TrajectoryChart({ events }: { events: TimelineEvent[] }) {
  const points = events
    .filter((e) => e.biological_age != null)
    .map((e) => ({
      label: e.label,
      date: e.timestamp,
      bioAge: e.biological_age as number,
    }));

  if (points.length === 0) {
    return (
      <div className="grid h-[280px] place-items-center text-sm text-muted">
        No scored timepoints yet.
      </div>
    );
  }

  const baseline = points[0].bioAge;
  const values = points.map((p) => p.bioAge);
  const min = Math.min(...values, baseline) - 0.6;
  const max = Math.max(...values, baseline) + 0.6;

  return (
    <div className="h-[280px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={points} margin={{ top: 10, right: 12, left: -8, bottom: 0 }}>
          <defs>
            <linearGradient id="trajFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={VITAL} stopOpacity={0.22} />
              <stop offset="100%" stopColor={VITAL} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="var(--border)" vertical={false} />
          <XAxis
            dataKey="label"
            tick={{ fill: "var(--text-muted)", fontSize: 11 }}
            tickLine={false}
            axisLine={{ stroke: "var(--border-strong)" }}
          />
          <YAxis
            domain={[min, max]}
            tick={{ fill: "var(--text-muted)", fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            width={42}
            tickFormatter={(v) => (v as number).toFixed(1)}
          />
          <ReferenceLine
            y={baseline}
            stroke="var(--text-faint)"
            strokeDasharray="4 4"
            label={{
              value: "baseline",
              position: "insideTopLeft",
              fill: "var(--text-faint)",
              fontSize: 10,
            }}
          />
          <Tooltip
            cursor={{ stroke: "var(--border-strong)" }}
            contentStyle={{
              background: "var(--surface)",
              border: "1px solid var(--border-strong)",
              borderRadius: 12,
              fontSize: 12,
              boxShadow: "0 10px 30px -16px rgba(27,27,27,0.4)",
            }}
            formatter={(v: number) => [`${v.toFixed(1)} yrs`, "Biological age"]}
            labelFormatter={(l, p) => `${l}${p?.[0]?.payload?.date ? ` · ${p[0].payload.date}` : ""}`}
          />
          <Area
            type="monotone"
            dataKey="bioAge"
            stroke={VITAL}
            strokeWidth={2.5}
            fill="url(#trajFill)"
            dot={{ r: 4, fill: VITAL, strokeWidth: 0 }}
            activeDot={{ r: 6 }}
            isAnimationActive
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
