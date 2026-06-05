"use client";

import {
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import type { SystemScore } from "@/lib/types";
import { signed } from "@/lib/utils";

const VITAL = "#ff5a1f";
const AI = "#575ecf";

// Map age acceleration → a 0–100 "vitality" radius: younger (negative) reads outward.
function vitality(accel: number) {
  return Math.max(8, Math.min(95, 50 - accel * 7));
}

const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

export function SystemRadar({ systems }: { systems: SystemScore[] }) {
  const data = systems.map((s) => ({
    system: cap(s.system),
    score: vitality(s.age_accel),
    accel: s.age_accel,
    status: s.status,
  }));

  return (
    <div className="h-[260px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart data={data} outerRadius="72%">
          <defs>
            <linearGradient id="radarFill" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor={VITAL} stopOpacity={0.5} />
              <stop offset="100%" stopColor={AI} stopOpacity={0.45} />
            </linearGradient>
          </defs>
          <PolarGrid stroke="var(--border-strong)" />
          <PolarAngleAxis
            dataKey="system"
            tick={{ fill: "var(--text-muted)", fontSize: 11 }}
          />
          <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
          <Radar
            dataKey="score"
            stroke={VITAL}
            strokeWidth={2}
            fill="url(#radarFill)"
            isAnimationActive
          />
          <Tooltip
            cursor={false}
            contentStyle={{
              background: "var(--surface)",
              border: "1px solid var(--border-strong)",
              borderRadius: 12,
              fontSize: 12,
              boxShadow: "0 10px 30px -16px rgba(27,27,27,0.4)",
            }}
            formatter={(_v, _n, p) => [
              `${signed(p.payload.accel)} yrs · ${p.payload.status}`,
              p.payload.system,
            ]}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
