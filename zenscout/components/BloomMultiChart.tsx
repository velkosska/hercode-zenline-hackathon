"use client";

import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { DashboardResponse } from "@/lib/api";
import { BloomScoreTooltip } from "./InfoTooltip";

function ScoreTooltip({ active, payload }: { active?: boolean; payload?: Array<{ payload: Record<string, unknown>; name: string; color: string }> }) {
  if (!active || !payload?.length) return null;
  const row = payload[0]?.payload;
  if (!row) return null;
  return (
    <div className="rounded-xl border border-stone-200 bg-white px-3 py-2 text-[12px] shadow-lg">
      <p className="font-medium text-stone-800">{String(row.label)}</p>
      {payload.map((p) => (
        <p key={p.name} style={{ color: p.color }} className="mt-1">
          {p.name}: {p.payload[p.name] as number}
        </p>
      ))}
    </div>
  );
}

type Props = {
  trendChart: DashboardResponse["trend_chart"];
  market: string;
  dataSource?: string;
};

export default function BloomMultiChart({ trendChart, market, dataSource }: Props) {
  const { series, chart_points, notice } = trendChart;
  const empty = !series.length || !chart_points.length;

  return (
    <section className="mt-8 rounded-3xl border border-stone-200/80 bg-surface p-6 shadow-sm">
      <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-wider text-stone-400">
            Live trends · {market === "CH" ? "Switzerland" : market}
          </p>
          <h2 className="mt-1 text-xl font-semibold text-stone-900">What&apos;s blooming right now</h2>
        </div>
        {dataSource && !empty && (
          <span
            className={`rounded-full px-2.5 py-1 text-[11px] font-medium ${
              dataSource === "tavily" ? "bg-emerald-50 text-emerald-700" : "bg-sky-50 text-sky-800"
            }`}
          >
            {dataSource === "tavily" ? "Live web signals" : "Pipeline signals"}
          </span>
        )}
      </div>

      {notice && (
        <p className="mb-4 rounded-xl bg-amber-50 px-3 py-2 text-[12px] leading-relaxed text-amber-900">{notice}</p>
      )}

      {empty ? (
        <div className="flex h-[320px] items-center justify-center text-sm text-stone-400">
          No trend series yet — run <code className="mx-1 rounded bg-stone-100 px-1">make all</code> to refresh pipeline data.
        </div>
      ) : (
        <>
          <div className="mb-4 flex flex-wrap gap-x-4 gap-y-2">
            {series.map((s) => (
              <div key={s.key} className="flex items-center gap-2 text-[12px] text-stone-600">
                <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ backgroundColor: s.color }} />
                <span>{s.label}</span>
                {s.score_math && <BloomScoreTooltip math={s.score_math} />}
              </div>
            ))}
          </div>

          <ResponsiveContainer width="100%" height={320}>
            <LineChart data={chart_points} margin={{ left: 0, right: 12, top: 8, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e7e5e4" vertical={false} />
              <XAxis dataKey="label" tick={{ fontSize: 11, fill: "#78716c" }} />
              <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: "#78716c" }} width={36} />
              <Tooltip content={<ScoreTooltip />} />
              <Legend wrapperStyle={{ display: "none" }} />
              {series.map((s) => (
                <Line
                  key={s.key}
                  type="monotone"
                  dataKey={s.key}
                  name={s.label}
                  stroke={s.color}
                  strokeWidth={2.5}
                  dot={false}
                  activeDot={{ r: 4 }}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </>
      )}
    </section>
  );
}
