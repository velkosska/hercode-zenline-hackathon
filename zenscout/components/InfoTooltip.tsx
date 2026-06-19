"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

function InfoIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="currentColor" aria-hidden>
      <path
        fillRule="evenodd"
        d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
        clipRule="evenodd"
      />
    </svg>
  );
}

type BloomScoreMath = {
  formula?: string;
  computed_formula?: string;
  components?: Record<string, number>;
  weights?: Record<string, number>;
  computed_score?: number;
  llm_score?: number;
  blend_weights?: { computed?: number; llm?: number };
  final_score?: number;
  plain_english?: string;
};

const POPUP_WIDTH = 320;
const VIEWPORT_PAD = 16;

function clampPopupPosition(rect: DOMRect) {
  const maxLeft = window.innerWidth - POPUP_WIDTH - VIEWPORT_PAD;
  const centeredLeft = rect.left + rect.width / 2 - POPUP_WIDTH / 2;
  const left = Math.max(VIEWPORT_PAD, Math.min(centeredLeft, maxLeft));
  const top = rect.bottom + 8;
  return { top, left };
}

function PopupContent({ math }: { math?: BloomScoreMath | null }) {
  if (!math) {
    return <p>Bloom score blends live evidence rules with AI synthesis.</p>;
  }

  const comp = math.components || {};
  const w = math.weights || { early_stage: 0.35, source_diversity: 0.25, coverage_gap: 0.25, recency: 0.15 };

  return (
    <>
      <p className="font-semibold text-stone-800">How bloom score is calculated</p>
      <p className="mt-2 break-words font-mono text-[10px] leading-snug text-stone-500">{math.computed_formula}</p>
      <ul className="mt-2 space-y-1">
        <li>early_stage ({w.early_stage}×): {comp.early_stage ?? "—"}</li>
        <li>source_diversity ({w.source_diversity}×): {comp.source_diversity ?? "—"}</li>
        <li>coverage_gap ({w.coverage_gap}×): {comp.coverage_gap ?? "—"}</li>
        <li>recency ({w.recency}×): {comp.recency ?? "—"}</li>
      </ul>
      <p className="mt-2 break-words font-mono text-[10px] leading-snug">
        computed = {math.computed_score?.toFixed(2) ?? "—"} · AI = {math.llm_score?.toFixed(2) ?? "—"}
      </p>
      <p className="mt-1 break-words font-mono text-[10px] leading-snug text-orange-700">{math.formula}</p>
      <p className="mt-2 break-words text-stone-500">{math.plain_english}</p>
    </>
  );
}

export function BloomScoreTooltip({ math }: { math?: BloomScoreMath | null }) {
  const triggerRef = useRef<HTMLButtonElement>(null);
  const [open, setOpen] = useState(false);
  const [position, setPosition] = useState({ top: 0, left: 0 });

  const updatePosition = useCallback(() => {
    if (!triggerRef.current) return;
    setPosition(clampPopupPosition(triggerRef.current.getBoundingClientRect()));
  }, []);

  useEffect(() => {
    if (!open) return;
    updatePosition();
    window.addEventListener("scroll", updatePosition, true);
    window.addEventListener("resize", updatePosition);
    return () => {
      window.removeEventListener("scroll", updatePosition, true);
      window.removeEventListener("resize", updatePosition);
    };
  }, [open, updatePosition]);

  const popup =
    open &&
    typeof document !== "undefined" &&
    createPortal(
      <div
        role="tooltip"
        className="fixed z-[9999] rounded-xl border border-stone-200 bg-white p-4 text-left text-[11px] leading-relaxed text-stone-600 shadow-xl"
        style={{ top: position.top, left: position.left, width: POPUP_WIDTH, maxWidth: `calc(100vw - ${VIEWPORT_PAD * 2}px)` }}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
      >
        <PopupContent math={math} />
      </div>,
      document.body
    );

  return (
    <>
      <button
        ref={triggerRef}
        type="button"
        aria-label="How bloom score is calculated"
        aria-expanded={open}
        className="inline-flex shrink-0 cursor-help rounded-full p-0.5 text-stone-400 transition hover:text-stone-600 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/40"
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
          updatePosition();
          setOpen((v) => !v);
        }}
        onMouseEnter={() => {
          updatePosition();
          setOpen(true);
        }}
        onMouseLeave={() => setOpen(false)}
      >
        <InfoIcon className="h-3.5 w-3.5" />
      </button>
      {popup}
    </>
  );
}

export default BloomScoreTooltip;
