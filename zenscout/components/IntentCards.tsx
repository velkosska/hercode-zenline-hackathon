"use client";

import type { ChatMode } from "@/lib/types";

export const LANDING_INTENTS: Array<{
  id: string;
  mode: ChatMode;
  title: string;
  description: string;
  prompt: string;
  icon: "category" | "crosscheck" | "roi";
}> = [
  {
    id: "category",
    mode: "category",
    title: "Stock up by category",
    description: "Choose shoes, coats, gear or accessories — get styles and features to buy.",
    prompt: "Category drill-down: Shoes — what styles and product features should we stock for Swiss outdoor retail?",
    icon: "category",
  },
  {
    id: "crosscheck",
    mode: "crosscheck",
    title: "Crosscheck an idea",
    description: "Pressure-test a product bet against live market signals.",
    prompt: "Crosscheck my product idea: ",
    icon: "crosscheck",
  },
  {
    id: "roi",
    mode: "roi",
    title: "Pricing & ROI",
    description: "Predict margin, ROI and the right price to launch at.",
    prompt: "Estimate TAM and addressable revenue for ",
    icon: "roi",
  },
];

export const CATEGORY_QUICK = [
  { id: "shoes", label: "Shoes" },
  { id: "coats", label: "Coats" },
  { id: "gear", label: "Gear" },
  { id: "accessories", label: "Accessories" },
];

function Icon({ type }: { type: "category" | "crosscheck" | "roi" }) {
  const c = "h-5 w-5 text-accent";
  if (type === "category") {
    return (
      <svg className={c} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
        <path d="M4 7h16M4 12h10M4 17h14" strokeLinecap="round" />
      </svg>
    );
  }
  if (type === "crosscheck") {
    return (
      <svg className={c} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
        <path d="M9 12l2 2 4-4" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M12 3l7 4v6c0 4-3 7-7 8-4-1-7-4-7-8V7l7-4z" strokeLinejoin="round" />
      </svg>
    );
  }
  return (
    <svg className={c} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
      <path d="M5 19V9M12 19V5M19 19v-7" strokeLinecap="round" />
    </svg>
  );
}

type Props = {
  onSelect: (mode: ChatMode, prompt: string) => void;
  onCategoryQuick?: (categoryId: string, label: string) => void;
  activeMode?: ChatMode;
};

export default function IntentCards({ onSelect, onCategoryQuick, activeMode }: Props) {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {LANDING_INTENTS.map((intent) => (
          <button
            key={intent.id}
            type="button"
            onClick={() => onSelect(intent.mode, intent.prompt)}
            className={`rounded-2xl border bg-surface p-5 text-left shadow-sm transition hover:border-stone-300 ${
              activeMode === intent.mode ? "border-stone-300 ring-1 ring-stone-200" : "border-stone-200/80"
            }`}
          >
            <div className="mb-4 flex h-9 w-9 items-center justify-center rounded-lg bg-accent/10">
              <Icon type={intent.icon} />
            </div>
            <h3 className="text-[15px] font-semibold text-stone-900">{intent.title}</h3>
            <p className="mt-2 text-[13px] leading-relaxed text-stone-500">{intent.description}</p>
          </button>
        ))}
      </div>

      {onCategoryQuick && (
        <div className="flex flex-wrap items-center justify-center gap-2">
          {CATEGORY_QUICK.map((cat) => (
            <button
              key={cat.id}
              type="button"
              onClick={() => onCategoryQuick(cat.id, cat.label)}
              className="rounded-full border border-stone-200/80 bg-surface px-3 py-1 text-[12px] font-medium text-stone-600 transition hover:border-stone-300"
            >
              {cat.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
