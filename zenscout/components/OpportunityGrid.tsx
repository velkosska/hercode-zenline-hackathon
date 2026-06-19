"use client";

import { useMemo, useState } from "react";
import type { DashboardOpportunity, DashboardResponse } from "@/lib/api";

const STATUS_STYLES = {
  buy_now: { dot: "bg-emerald-500", text: "text-emerald-700", bg: "bg-emerald-50" },
  worth_testing: { dot: "bg-sky-500", text: "text-sky-700", bg: "bg-sky-50" },
  keep_watching: { dot: "bg-orange-400", text: "text-orange-700", bg: "bg-orange-50" },
};

type Props = {
  opportunities: DashboardOpportunity[];
  filters: DashboardResponse["filters"];
  onOpenStory: (opp: DashboardOpportunity) => void;
};

export default function OpportunityGrid({ opportunities, filters, onOpenStory }: Props) {
  const [filter, setFilter] = useState("all");
  const [sort, setSort] = useState("recommendation");

  const visible = useMemo(() => {
    let rows = filter === "all" ? opportunities : opportunities.filter((o) => o.status === filter);
    if (sort === "market") {
      rows = [...rows].sort((a, b) => b.addressable_chf_m - a.addressable_chf_m);
    }
    return rows;
  }, [opportunities, filter, sort]);

  return (
    <section id="evidence" className="mt-12 pb-16">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-wrap gap-2">
          {filters.map((f) => (
            <button
              key={f.id}
              type="button"
              onClick={() => setFilter(f.id)}
              className={`rounded-full px-4 py-2 text-[13px] font-medium transition ${
                filter === f.id
                  ? "bg-stone-900 text-white"
                  : "border border-stone-200/80 bg-surface text-stone-600 hover:border-stone-300"
              }`}
            >
              {f.label} ({f.count})
            </button>
          ))}
        </div>
        <label className="flex items-center gap-2 text-[13px] text-stone-500">
          Sort by
          <select
            value={sort}
            onChange={(e) => setSort(e.target.value)}
            className="rounded-lg border border-stone-200 bg-surface px-2 py-1 text-stone-700"
          >
            <option value="recommendation">Recommendation</option>
            <option value="market">Market size</option>
          </select>
        </label>
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        {visible.map((opp) => {
          const style = STATUS_STYLES[opp.status];
          return (
            <article
              key={opp.id}
              className="rounded-2xl border border-stone-200/80 bg-surface p-5 shadow-sm transition hover:border-stone-300"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-2">
                  <span className="text-[13px] font-semibold text-stone-400">#{opp.rank}</span>
                  <span className="rounded-full bg-stone-100 px-2.5 py-0.5 text-[11px] font-medium uppercase tracking-wide text-stone-500">
                    {opp.category_tag}
                  </span>
                </div>
                <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-medium ${style.bg} ${style.text}`}>
                  <span className={`h-1.5 w-1.5 rounded-full ${style.dot}`} />
                  {opp.status_label}
                </span>
              </div>

              <h3 className="mt-4 text-lg font-semibold text-stone-900">{opp.title}</h3>
              <p className="mt-1 text-[13px] text-stone-500">{opp.subtitle}</p>

              <div className="mt-5 grid grid-cols-2 gap-4 border-t border-stone-100 pt-4">
                <div>
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-stone-400">Could be worth</p>
                  <p className="mt-1 text-xl font-semibold text-stone-900">CHF {opp.addressable_chf_m}M</p>
                  <p className="text-[12px] text-stone-500">{opp.market_label}</p>
                </div>
                <div>
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-stone-400">Start stocking</p>
                  <p className="mt-1 text-xl font-semibold text-stone-900">{opp.start_stocking}</p>
                  <p className="text-[12px] text-stone-500">{opp.peak_label}</p>
                </div>
              </div>

              <div className="mt-4 flex items-center justify-between">
                <p className="text-[12px] text-stone-400">Based on {opp.source_count} sources</p>
                <button
                  type="button"
                  onClick={() => onOpenStory(opp)}
                  className="text-[13px] font-medium text-accent hover:underline"
                >
                  See the full story →
                </button>
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
