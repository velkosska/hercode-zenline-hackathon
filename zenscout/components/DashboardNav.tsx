"use client";

type Props = {
  market: string;
  sectorLabel: string;
  regionLabel: string;
  active?: "dashboard" | "evidence" | "how";
};

export default function DashboardNav({ market, sectorLabel, regionLabel, active = "dashboard" }: Props) {
  const linkClass = (id: Props["active"]) =>
    `rounded-full px-4 py-1.5 text-[13px] font-medium transition ${
      active === id ? "bg-white text-stone-900 shadow-sm" : "text-stone-500 hover:text-stone-800"
    }`;

  return (
    <header className="sticky top-0 z-30 border-b border-stone-200/60 bg-canvas/90 backdrop-blur-md">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-6 py-4">
        <div className="flex items-center gap-2">
          <span className="text-accent">✦</span>
          <span className="text-[15px] font-semibold text-stone-900">ZenScout</span>
        </div>

        <nav className="hidden items-center gap-1 rounded-full border border-stone-200/80 bg-stone-100/60 p-1 md:flex">
          <a href="#" className={linkClass("dashboard")}>
            Dashboard
          </a>
          <a href="#evidence" className={linkClass("evidence")}>
            Evidence
          </a>
          <a href="#how-it-works" className={linkClass("how")}>
            How it works
          </a>
        </nav>

        <p className="hidden text-right text-[12px] text-stone-500 sm:block">
          {sectorLabel} · {market === "CH" ? "Switzerland" : market} / {regionLabel}
        </p>
      </div>
    </header>
  );
}
