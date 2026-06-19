"use client";

import type { DashboardResponse } from "@/lib/api";

export default function DashboardMetrics({ metrics }: { metrics: DashboardResponse["metrics"] }) {
  const cards = [
    { label: "Opportunities found", value: String(metrics.opportunities_found), sub: "this scan" },
    { label: "Ready to buy", value: String(metrics.ready_to_buy), sub: "strong evidence" },
    { label: "Worth testing", value: String(metrics.worth_testing), sub: "pilot first" },
    { label: "Total market in Switzerland", value: `CHF ${metrics.total_market_chf_m}M`, sub: "combined yearly potential" },
  ];

  return (
    <section className="mt-8 grid grid-cols-2 gap-4 lg:grid-cols-4">
      {cards.map((c) => (
        <div key={c.label} className="rounded-2xl border border-stone-200/80 bg-surface px-5 py-4 shadow-sm">
          <p className="text-[11px] font-medium uppercase tracking-wide text-stone-400">{c.label}</p>
          <p className="mt-2 text-2xl font-semibold text-stone-900">{c.value}</p>
          <p className="mt-1 text-[12px] text-stone-500">{c.sub}</p>
        </div>
      ))}
    </section>
  );
}
