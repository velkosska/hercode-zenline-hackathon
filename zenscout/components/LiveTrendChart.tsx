"use client";

import { useEffect, useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { checkLiveSearch, fetchLiveTrends, type LiveTrendsResponse } from "@/lib/api";

export default function LiveTrendChart({ market }: { market: string }) {
  const [data, setData] = useState<LiveTrendsResponse | null>(null);
  const [apiUp, setApiUp] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    checkLiveSearch().then(setApiUp);
    fetchLiveTrends(market).then((d) => {
      setData(d);
      setLoading(false);
    });
  }, [market]);

  const series = data?.series ?? [];

  const badge =
    data?.data_source === "tavily"
      ? { text: `Live · ${data.source_count} sources`, className: "bg-emerald-50 text-emerald-700" }
      : data?.data_source === "pipeline"
        ? { text: "Pipeline signals", className: "bg-sky-50 text-sky-800" }
        : null;

  return (
    <div className="w-full rounded-2xl border border-stone-200/80 bg-surface p-5 shadow-sm">
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-wider text-stone-400">
            Live trend radar
          </p>
          <p className="mt-1 text-base font-medium text-stone-900">
            Momentum from today&apos;s web signals
          </p>
        </div>
        {badge && !loading && (
          <span className={`shrink-0 rounded-full px-2.5 py-1 text-[11px] font-medium ${badge.className}`}>
            {badge.text}
          </span>
        )}
      </div>

      {data?.notice && !loading && (
        <p className="mb-3 rounded-lg bg-amber-50 px-3 py-2 text-[12px] leading-relaxed text-amber-900">
          {data.notice}
        </p>
      )}

      {loading ? (
        <div className="flex h-[260px] items-center justify-center text-sm text-stone-400 animate-pulse">
          Loading trends…
        </div>
      ) : apiUp === false ? (
        <div className="flex h-[260px] flex-col items-center justify-center gap-2 text-center text-sm text-stone-500">
          <p>Cannot reach the API on port 8000.</p>
          <p className="text-[12px] text-stone-400">Run <code className="rounded bg-stone-100 px-1">make api</code> in hercode-zenline-hackathon</p>
        </div>
      ) : series.length === 0 ? (
        <div className="flex h-[260px] flex-col items-center justify-center gap-2 text-center text-sm text-stone-500 px-4">
          <p>No trend data available yet.</p>
          <p className="text-[12px] text-stone-400">Run <code className="rounded bg-stone-100 px-1">make all</code> to build signals.csv</p>
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={260}>
          <AreaChart data={series} margin={{ left: 4, right: 12, top: 8, bottom: 56 }}>
            <defs>
              <linearGradient id="momentumFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#ea580c" stopOpacity={0.4} />
                <stop offset="100%" stopColor="#ea580c" stopOpacity={0.03} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#e7e5e4" vertical={false} />
            <XAxis
              dataKey="name"
              tick={{ fontSize: 10, fill: "#78716c" }}
              angle={-28}
              textAnchor="end"
              height={56}
              interval={0}
            />
            <YAxis domain={[0, 1]} tick={{ fontSize: 11, fill: "#78716c" }} width={32} />
            <Tooltip />
            <Area
              type="monotone"
              dataKey="momentum"
              stroke="#ea580c"
              strokeWidth={2}
              fill="url(#momentumFill)"
              name="Momentum"
            />
          </AreaChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
