"use client";

import type { DashboardResponse } from "@/lib/api";
import type { ChatMode } from "@/lib/types";

type Props = {
  prompts: DashboardResponse["chat_prompts"];
  onSelect: (mode: ChatMode, prompt: string) => void;
};

function Icon({ id }: { id: string }) {
  const c = "h-5 w-5";
  if (id === "category") {
    return (
      <svg className={c} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
        <circle cx="12" cy="12" r="8" />
        <circle cx="12" cy="12" r="3" />
        <path d="M12 2v3M12 19v3M2 12h3M19 12h3" strokeLinecap="round" />
      </svg>
    );
  }
  if (id === "crosscheck") {
    return (
      <svg className={c} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
        <path d="M9 18h6M10 22h4M12 2a7 7 0 017 7c0 2.5-1.3 4.7-3.2 6L15 18H9l-.8-3C6.3 13.7 5 11.5 5 9a7 7 0 017-7z" strokeLinejoin="round" />
      </svg>
    );
  }
  return (
    <svg className={c} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
      <path d="M5 19V9M12 19V5M19 19v-7" strokeLinecap="round" />
    </svg>
  );
}

export default function ActionCards({ prompts, onSelect }: Props) {
  return (
    <section className="mt-8 grid gap-4 md:grid-cols-3">
      {prompts.map((p) => {
        const accent = p.accent === "orange" ? "text-orange-600" : "text-accent";
        const iconBg = p.accent === "orange" ? "bg-orange-50 text-orange-600" : "bg-accent/10 text-accent";
        return (
          <div key={p.id} className="rounded-2xl border border-stone-200/80 bg-surface p-5 shadow-sm">
            <div className={`mb-4 flex h-10 w-10 items-center justify-center rounded-xl ${iconBg}`}>
              <Icon id={p.id} />
            </div>
            <h3 className="text-[15px] font-semibold text-stone-900">{p.title}</h3>
            <p className="mt-2 text-[13px] leading-relaxed text-stone-500">{p.description}</p>
            <button
              type="button"
              onClick={() => onSelect(p.mode as ChatMode, p.prompt)}
              className={`mt-4 text-[13px] font-medium ${accent} hover:underline`}
            >
              Start chat →
            </button>
          </div>
        );
      })}
    </section>
  );
}
