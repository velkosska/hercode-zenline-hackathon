"use client";

import { useEffect, useState } from "react";
import { fetchCompetitorSnapshot, type CompetitorSnapshot } from "@/lib/api";

const STATUS_STYLE: Record<string, string> = {
  covered: "bg-emerald-100 text-emerald-800",
  partially_covered: "bg-amber-100 text-amber-900",
  absent: "bg-rose-100 text-rose-800",
};

function StatusDot({ status }: { status: string }) {
  return (
    <span
      className={`inline-block rounded-full px-2 py-0.5 text-[10px] font-medium capitalize ${STATUS_STYLE[status] || "bg-stone-100 text-stone-600"}`}
      title={status.replace("_", " ")}
    >
      {status === "partially_covered" ? "partial" : status}
    </span>
  );
}

export default function CompetitorSnapshotPanel({
  market,
  onAnalyze,
}: {
  market: string;
  onAnalyze?: () => void;
}) {
  const [data, setData] = useState<CompetitorSnapshot | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetchCompetitorSnapshot(market).then((d) => {
      setData(d);
      setLoading(false);
    });
  }, [market]);

  const domains = data?.retailer_domains ?? ["transa.ch", "ochsnersport.ch", "decathlon.ch"];

  return (
    <div className="rounded-2xl border border-stone-200 bg-white p-4 shadow-sm">
      <div className="mb-3 flex items-start justify-between gap-2">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-stone-400">Competitor analysis</p>
          <p className="mt-0.5 text-sm font-medium text-stone-800">CH assortment coverage gaps</p>
        </div>
        {data && !loading && (
          <span className="shrink-0 rounded-full bg-stone-100 px-2 py-0.5 text-[10px] font-medium text-stone-600">
            {data.gap_count} gaps
          </span>
        )}
      </div>

      {loading ? (
        <div className="py-10 text-center text-sm text-stone-400 animate-pulse">Scanning retailers…</div>
      ) : !data?.rows?.length ? (
        <p className="py-10 text-center text-sm text-stone-400">Competitor data unavailable</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[320px] text-left text-[11px]">
            <thead>
              <tr className="border-b border-stone-100 text-stone-400">
                <th className="pb-2 pr-2 font-medium">Keyword</th>
                {domains.map((d) => (
                  <th key={d} className="pb-2 px-1 font-medium text-center">
                    {d.replace(".ch", "")}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.rows.map((row) => (
                <tr key={row.keyword} className="border-b border-stone-50">
                  <td className="py-2 pr-2 font-medium text-stone-800">{row.keyword}</td>
                  {domains.map((d) => (
                    <td key={d} className="py-2 px-1 text-center">
                      <StatusDot status={row.retailers[d]?.status ?? row.retailers[`www.${d}`]?.status ?? "absent"} />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {onAnalyze && (
        <button
          type="button"
          onClick={onAnalyze}
          className="mt-3 w-full rounded-xl border border-stone-200 bg-stone-50 py-2 text-[12px] font-medium text-stone-700 transition hover:bg-stone-100"
        >
          Deep-dive competitor gaps in chat →
        </button>
      )}
    </div>
  );
}
