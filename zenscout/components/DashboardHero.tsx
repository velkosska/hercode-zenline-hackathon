"use client";

type Props = {
  updatedAt?: string;
  scanDate?: string;
};

function formatDate(iso?: string) {
  if (!iso) return null;
  try {
    const d = iso.includes("T") ? new Date(iso) : new Date(`${iso}T12:00:00`);
    return d.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
  } catch {
    return iso;
  }
}

export default function DashboardHero({ updatedAt, scanDate }: Props) {
  const label = formatDate(scanDate || updatedAt);

  return (
    <section className="py-10 text-center">
      {label && (
        <span className="inline-flex rounded-full bg-sky-50 px-3 py-1 text-[11px] font-medium text-sky-700">
          ↻ Updated {label}
        </span>
      )}
      <h1 className="mx-auto mt-5 max-w-3xl text-[2rem] font-semibold leading-tight tracking-tight text-stone-900 sm:text-[2.35rem]">
        Trend intelligence for Swiss outdoor retail.
      </h1>
      <p className="mx-auto mt-4 max-w-2xl text-[15px] leading-relaxed text-stone-500">
        Live signals, plain-English recommendations, and an AI co-pilot you can actually talk to.
      </p>
    </section>
  );
}
