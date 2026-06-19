"use client";

type Step = { step: string; title: string; body: string };

export default function HowItWorks({ steps }: { steps: Step[] }) {
  return (
    <section id="how-it-works" className="rounded-3xl border border-stone-200/80 bg-surface p-6 shadow-sm sm:p-8">
      <div className="mb-8 text-center">
        <h2 className="text-xl font-semibold text-stone-900">How ZenScout works</h2>
        <p className="mt-2 text-[14px] text-stone-500">
          Four steps from raw market noise to a buyer-ready decision.
        </p>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {steps.map((s) => (
          <div key={s.step} className="rounded-2xl bg-stone-50/80 p-5">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-stone-400">{s.step}</p>
            <h3 className="mt-3 text-[15px] font-semibold text-stone-900">{s.title}</h3>
            <p className="mt-2 text-[13px] leading-relaxed text-stone-500">{s.body}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
