"use client";

import type { CategoryOption } from "@/lib/types";

const ICONS: Record<string, string> = {
  shoes: "👟",
  coats: "🧥",
  gear: "🎒",
  accessories: "🧤",
};

type Props = {
  options: CategoryOption[];
  trendKeywords?: string[];
  onSelect: (categoryId: string, label: string) => void;
  disabled?: boolean;
};

export default function CategoryPicker({ options, trendKeywords, onSelect, disabled }: Props) {
  return (
    <div className="mt-4 rounded-xl border border-dashed border-stone-300 bg-white/80 p-4">
      <p className="text-[13px] font-semibold text-stone-800">Drill into a category</p>
      <p className="mt-1 text-[12px] leading-relaxed text-stone-500">
        Pick a shelf to see which styles and product features to stock up on
        {trendKeywords && trendKeywords.length > 0 && (
          <> — linked to: {trendKeywords.slice(0, 3).join(", ")}</>
        )}
        .
      </p>
      <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
        {options.map((cat) => (
          <button
            key={cat.id}
            type="button"
            disabled={disabled}
            onClick={() => onSelect(cat.id, cat.label)}
            className="flex flex-col items-center gap-1 rounded-xl border border-stone-200 bg-stone-50 px-3 py-3 text-center transition hover:border-stone-400 hover:bg-white disabled:opacity-50"
          >
            <span className="text-xl">{ICONS[cat.id] || "📦"}</span>
            <span className="text-[12px] font-medium text-stone-800">{cat.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
