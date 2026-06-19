"use client";

import { useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type {
  BloomPrediction,
  ChatResponse,
  DemandDriver,
  EvidenceItem,
  ProductStocking,
  SourceType,
} from "@/lib/types";
import { BloomScoreTooltip } from "./InfoTooltip";
import CategoryPicker from "./CategoryPicker";

const SOURCE_COLORS: Record<string, string> = {
  marketplace: "#059669",
  news: "#2563eb",
  social: "#db2777",
  trade: "#d97706",
  discovery: "#7c3aed",
  web: "#78716c",
};

const TRAJECTORY_COLORS = ["#ea580c", "#2563eb", "#059669"];

type Tab = "predictions" | "stocking" | "charts" | "evidence" | "playbook";

function DriverBadge({ driver }: { driver?: DemandDriver | null }) {
  if (!driver) return null;
  const styles = {
    consumer_pull: "bg-emerald-50 text-emerald-800 border-emerald-200",
    trade_push: "bg-amber-50 text-amber-900 border-amber-200",
    mixed: "bg-sky-50 text-sky-900 border-sky-200",
  };
  const labels = {
    consumer_pull: "Consumer-pull",
    trade_push: "Trade-push",
    mixed: "Mixed signals",
  };
  return (
    <span className={`inline-block rounded-full border px-2.5 py-0.5 text-[11px] font-medium ${styles[driver]}`}>
      {labels[driver]}
    </span>
  );
}

function SourcePill({ type }: { type: SourceType | string }) {
  return (
    <span
      className="rounded-full px-2 py-0.5 text-[10px] font-medium text-white"
      style={{ backgroundColor: SOURCE_COLORS[type] || SOURCE_COLORS.web }}
    >
      {type}
    </span>
  );
}

function BloomCard({
  prediction,
  evidence,
  selected,
  onSelect,
}: {
  prediction: BloomPrediction;
  evidence: EvidenceItem[];
  selected: boolean;
  onSelect: () => void;
}) {
  const linked = (prediction.evidence_ids || [])
    .map((id) => evidence.find((e) => e.id === id))
    .filter(Boolean) as EvidenceItem[];

  return (
    <button
      type="button"
      onClick={onSelect}
      className={`w-full overflow-visible rounded-xl border p-4 text-left transition ${
        selected
          ? "border-orange-300 bg-orange-50/60 ring-1 ring-orange-200"
          : "border-stone-200 bg-white hover:border-stone-300"
      }`}
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="font-semibold text-stone-900">{prediction.keyword}</p>
          <p className="mt-1 text-[13px] text-stone-600">{prediction.opportunity}</p>
        </div>
        <div className="text-right">
          <div className="flex items-center justify-end gap-1">
            <p className="text-lg font-bold text-orange-600">{(prediction.bloom_score * 100).toFixed(0)}</p>
            <BloomScoreTooltip math={prediction.score_math} />
          </div>
          <p className="text-[10px] uppercase tracking-wide text-stone-400">bloom score</p>
        </div>
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        {prediction.bloom_badge && (
          <span className="rounded-full bg-orange-100 px-2 py-0.5 text-[10px] font-medium text-orange-800">
            {prediction.bloom_badge}
          </span>
        )}
        {prediction.timing_window && (
          <span className="rounded-full bg-stone-100 px-2 py-0.5 text-[10px] text-stone-600">
            {prediction.timing_window}
          </span>
        )}
        {prediction.coverage_status && (
          <span className="rounded-full bg-stone-100 px-2 py-0.5 text-[10px] text-stone-600">
            {prediction.coverage_status.replace("_", " ")}
          </span>
        )}
      </div>
      {prediction.weak_signal_note && (
        <p className="mt-3 rounded-lg bg-stone-50 px-3 py-2 text-[12px] leading-relaxed text-stone-600">
          <span className="font-medium text-stone-700">Weak signal → </span>
          {prediction.weak_signal_note}
        </p>
      )}
      <p className="mt-2 text-[12px] leading-relaxed text-stone-600">{prediction.bloom_rationale}</p>
      <p className="mt-2 text-[13px] font-medium text-stone-800">→ {prediction.recommended_action}</p>
      {linked.length > 0 && (
        <p className="mt-2 text-[11px] text-stone-400">{linked.length} linked sources · click to highlight</p>
      )}
    </button>
  );
}

function EvidenceRow({
  item,
  highlighted,
}: {
  item: EvidenceItem;
  highlighted: boolean;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div
      id={`evidence-${item.id}`}
      className={`rounded-lg border transition ${
        highlighted ? "border-orange-300 bg-orange-50/50" : "border-stone-200 bg-white"
      }`}
    >
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex w-full items-start gap-3 p-3 text-left"
      >
        <span className="mt-0.5 shrink-0 font-mono text-[11px] text-stone-400">[{item.id}]</span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <SourcePill type={item.source_type} />
            <span className="truncate text-[13px] font-medium text-stone-900">{item.title}</span>
          </div>
          <p className="mt-1 truncate text-[11px] text-stone-400">{item.domain}</p>
        </div>
        <span className="text-stone-400">{open ? "−" : "+"}</span>
      </button>
      {open && (
        <div className="border-t border-stone-100 px-3 pb-3 pt-2">
          <p className="text-[12px] leading-relaxed text-stone-600">{item.snippet}</p>
          <a
            href={item.url}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-2 inline-block text-[12px] text-accent underline hover:text-accent/80"
          >
            Open source ↗
          </a>
        </div>
      )}
    </div>
  );
}

function CategoryPickerBlock({
  options,
  trendKeywords,
  onSelect,
  disabled,
}: {
  options: ChatResponse["category_options"];
  trendKeywords: string[];
  onSelect: (categoryId: string, label: string, trendKeywords: string[]) => void;
  disabled?: boolean;
}) {
  if (!options?.length) return null;
  return (
    <CategoryPicker
      options={options}
      trendKeywords={trendKeywords}
      disabled={disabled}
      onSelect={(id, label) => onSelect(id, label, trendKeywords)}
    />
  );
}

function StockingPanel({
  items,
  category,
}: {
  items: ProductStocking[];
  evidence: EvidenceItem[];
  category?: string | null;
}) {
  return (
    <div className="space-y-3">
      {category && (
        <p className="text-[12px] text-stone-500">
          Stocking guide for <span className="font-medium text-stone-800">{category}</span>
        </p>
      )}
      {items.map((item, i) => (
        <div key={i} className="rounded-xl border border-stone-200 bg-white p-4">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <p className="font-semibold text-stone-900">{item.style}</p>
            <div className="flex gap-2">
              {item.priority && (
                <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-medium text-emerald-800">
                  {item.priority} priority
                </span>
              )}
              {item.timing && (
                <span className="rounded-full bg-stone-100 px-2 py-0.5 text-[10px] text-stone-600">
                  {item.timing}
                </span>
              )}
            </div>
          </div>
          {item.features && item.features.length > 0 && (
            <ul className="mt-3 flex flex-wrap gap-1.5">
              {item.features.map((f) => (
                <li
                  key={f}
                  className="rounded-full border border-stone-200 bg-stone-50 px-2.5 py-1 text-[11px] text-stone-700"
                >
                  {f}
                </li>
              ))}
            </ul>
          )}
          {item.example_products && (
            <p className="mt-2 text-[12px] text-stone-600">
              <span className="font-medium">Examples: </span>
              {item.example_products}
            </p>
          )}
          {item.rationale && <p className="mt-2 text-[12px] leading-relaxed text-stone-600">{item.rationale}</p>}
          {item.evidence_urls && item.evidence_urls.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-2">
              {item.evidence_urls.slice(0, 3).map((url) => (
                <a
                  key={url}
                  href={url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-[11px] text-accent underline"
                >
                  Source ↗
                </a>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

export default function ScoutResults({
  data,
  onCategorySelect,
  categoryLoading,
}: {
  data: ChatResponse;
  onCategorySelect?: (categoryId: string, label: string, trendKeywords: string[]) => void;
  categoryLoading?: boolean;
}) {
  const [tab, setTab] = useState<Tab>(data.product_stocking?.length ? "stocking" : "predictions");
  const [selectedBloom, setSelectedBloom] = useState<number>(0);

  const predictions: BloomPrediction[] = useMemo(() => {
    if (data.bloom_predictions?.length) return data.bloom_predictions;
    return (data.emerging_trends || []).map((t) => ({
      keyword: t.keyword || "Trend",
      bloom_score: t.bloom_score || 0.5,
      opportunity: t.opportunity,
      timing_window: t.timing_window,
      recommended_action: t.recommended_action,
      bloom_badge: t.bloom_badge,
      evidence_ids: [] as number[],
    }));
  }, [data.bloom_predictions, data.emerging_trends]);

  const evidence = data.evidence || [];
  const charts = data.charts || {};
  const playbook = data.retailer_playbook || [];
  const cap = data.market_capture;

  const highlightIds = useMemo(() => {
    const pred = predictions[selectedBloom];
    return new Set(pred?.evidence_ids || []);
  }, [predictions, selectedBloom]);

  const stocking = data.product_stocking || [];
  const trendKeywords = predictions.map((p) => p.keyword);

  const tabs: { id: Tab; label: string; count?: number }[] = [
    { id: "predictions", label: "Bloom predictions", count: predictions.length },
    ...(stocking.length > 0 ? [{ id: "stocking" as Tab, label: "Stock up", count: stocking.length }] : []),
    { id: "charts", label: "Charts" },
    { id: "evidence", label: "Sources", count: evidence.length },
    { id: "playbook", label: "Retailer playbook", count: playbook.length },
  ];

  const handleSelectBloom = (index: number) => {
    setSelectedBloom(index);
    setTab("evidence");
    setTimeout(() => {
      const firstId = predictions[index]?.evidence_ids?.[0];
      if (firstId != null) {
        document.getElementById(`evidence-${firstId}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    }, 100);
  };

  return (
    <div className="mt-4 w-full space-y-4 overflow-visible rounded-xl border border-stone-200 bg-stone-50/80 p-4 text-sm">
      <div className="flex flex-wrap items-center gap-2">
        <DriverBadge driver={data.demand_driver} />
        <span className="text-[11px] text-emerald-600">Live search · predictive bloom</span>
        {typeof data.score_explanation?.prediction_count === "number" && (
          <span className="text-[11px] text-stone-400">
            {String(data.score_explanation.prediction_count)} predictions from{" "}
            {String(data.score_explanation.source_count)} sources
          </span>
        )}
      </div>

      {data.score_explanation?.recommended_action ? (
        <div className="rounded-xl border border-orange-200 bg-orange-50/80 p-3">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-orange-700">Lead action this week</p>
          <p className="mt-1 text-[14px] font-medium text-stone-900">
            {String(data.score_explanation.recommended_action)}
          </p>
        </div>
      ) : null}

      {cap && (
        <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
          {[
            ["Market TAM", `CHF ${cap.tam_total_chf_m}M`],
            ["Category TAM", `CHF ${cap.category_tam_chf_m}M`],
            ["Capture", `${cap.estimated_capture_rate_pct}%`],
            ["Addressable", `CHF ${cap.addressable_revenue_chf_m}M`],
          ].map(([label, val]) => (
            <div key={label} className="rounded-lg border border-stone-200 bg-white p-2.5">
              <p className="text-[10px] text-stone-400">{label}</p>
              <p className="text-sm font-semibold text-stone-800">{val}</p>
            </div>
          ))}
        </div>
      )}

      <div className="flex flex-wrap gap-1 rounded-xl border border-stone-200 bg-white p-1">
        {tabs.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            className={`rounded-lg px-3 py-1.5 text-[12px] font-medium transition ${
              tab === t.id ? "bg-stone-900 text-white" : "text-stone-600 hover:bg-stone-100"
            }`}
          >
            {t.label}
            {t.count != null && t.count > 0 ? ` (${t.count})` : ""}
          </button>
        ))}
      </div>

      {tab === "predictions" && (
        <div className="space-y-3">
          {predictions.map((p, i) => (
            <BloomCard
              key={i}
              prediction={p}
              evidence={evidence}
              selected={selectedBloom === i}
              onSelect={() => handleSelectBloom(i)}
            />
          ))}
          {data.score_explanation?.risks ? (
            <p className="rounded-lg border border-amber-200 bg-amber-50/80 p-3 text-[12px] text-amber-900">
              <span className="font-medium">Risks: </span>
              {String(data.score_explanation.risks)}
            </p>
          ) : null}
          {data.show_category_prompt && data.category_options && onCategorySelect && (
            <CategoryPickerBlock
              options={data.category_options}
              trendKeywords={trendKeywords}
              onSelect={onCategorySelect}
              disabled={categoryLoading}
            />
          )}
        </div>
      )}

      {tab === "stocking" && stocking.length > 0 && (
        <StockingPanel items={stocking} evidence={evidence} category={data.selected_category} />
      )}

      {tab === "charts" && (
        <div className="grid gap-4 lg:grid-cols-2">
          {charts.bloom_ranking && charts.bloom_ranking.length > 0 && (
            <div className="rounded-xl border border-stone-200 bg-white p-3">
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-stone-500">Bloom ranking</p>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={charts.bloom_ranking} margin={{ left: 0, right: 8, top: 8, bottom: 40 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e7e5e4" />
                  <XAxis dataKey="name" tick={{ fontSize: 10 }} angle={-20} textAnchor="end" height={50} />
                  <YAxis domain={[0, 1]} tick={{ fontSize: 10 }} />
                  <Tooltip />
                  <Bar dataKey="score" fill="#ea580c" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {charts.trajectories && charts.trajectories.length > 0 && (
            <div className="rounded-xl border border-stone-200 bg-white p-3">
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-stone-500">
                Predicted demand trajectory
              </p>
              <ResponsiveContainer width="100%" height={220}>
                <LineChart margin={{ left: 0, right: 8, top: 8, bottom: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e7e5e4" />
                  <XAxis
                    dataKey="label"
                    type="category"
                    allowDuplicatedCategory={false}
                    tick={{ fontSize: 10 }}
                  />
                  <YAxis domain={[0, 1]} tick={{ fontSize: 10 }} />
                  <Tooltip />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  {charts.trajectories.map((series, i) => (
                    <Line
                      key={series.keyword}
                      data={series.points}
                      type="monotone"
                      dataKey="demand_index"
                      name={series.keyword}
                      stroke={TRAJECTORY_COLORS[i % TRAJECTORY_COLORS.length]}
                      strokeWidth={2}
                      dot={{ r: 3 }}
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
              <p className="mt-1 text-[10px] text-stone-400">
                Projected from weak signals today → predicted mainstream demand (heuristic model)
              </p>
            </div>
          )}

          {charts.source_mix && charts.source_mix.length > 0 && (
            <div className="rounded-xl border border-stone-200 bg-white p-3">
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-stone-500">Evidence mix</p>
              <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                  <Pie
                    data={charts.source_mix}
                    dataKey="count"
                    nameKey="type"
                    cx="50%"
                    cy="50%"
                    outerRadius={70}
                    label={(props) => {
                      const name = String(props.name ?? props.payload?.type ?? "");
                      const value = props.value ?? props.payload?.count ?? "";
                      return `${name} (${value})`;
                    }}
                  >
                    {charts.source_mix.map((entry) => (
                      <Cell key={entry.type} fill={SOURCE_COLORS[entry.type] || SOURCE_COLORS.web} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>
          )}

          {charts.capture_funnel && charts.capture_funnel.length > 0 && (
            <div className="rounded-xl border border-stone-200 bg-white p-3">
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-stone-500">Revenue funnel (CHF M)</p>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={charts.capture_funnel} layout="vertical" margin={{ left: 20, right: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e7e5e4" />
                  <XAxis type="number" tick={{ fontSize: 10 }} />
                  <YAxis dataKey="label" type="category" width={90} tick={{ fontSize: 10 }} />
                  <Tooltip />
                  <Bar dataKey="value" fill="#2563eb" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      )}

      {tab === "evidence" && (
        <div className="space-y-2">
          {evidence.length === 0 &&
            data.evidence_urls.map((url) => (
              <a
                key={url}
                href={url}
                target="_blank"
                rel="noopener noreferrer"
                className="block truncate text-[12px] text-accent underline"
              >
                {url}
              </a>
            ))}
          {evidence.map((item) => (
            <EvidenceRow key={item.id} item={item} highlighted={highlightIds.has(item.id)} />
          ))}
        </div>
      )}

      {tab === "playbook" && (
        <ol className="space-y-3">
          {playbook.map((item, i) => (
            <li key={i} className="flex gap-3 rounded-xl border border-stone-200 bg-white p-3">
              <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-stone-900 text-xs font-bold text-white">
                {item.priority ?? i + 1}
              </span>
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <p className="font-medium text-stone-900">{item.action}</p>
                  {item.horizon && (
                    <span className="rounded-full bg-stone-100 px-2 py-0.5 text-[10px] text-stone-600">
                      {item.horizon}
                    </span>
                  )}
                </div>
                {item.rationale && <p className="mt-1 text-[12px] text-stone-600">{item.rationale}</p>}
              </div>
            </li>
          ))}
          {data.recommendations.length > 0 && playbook.length === 0 && (
            <>
              {data.recommendations.slice(0, 4).map((rec, i) => (
                <li key={i} className="rounded-lg border border-stone-200 bg-white p-3">
                  <p className="font-medium">{rec.opportunity || rec.keyword}</p>
                  <p className="mt-1 text-[13px] text-stone-600">{rec.recommended_action}</p>
                </li>
              ))}
            </>
          )}
        </ol>
      )}
    </div>
  );
}
