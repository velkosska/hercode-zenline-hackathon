"use client";

import { SparkleIcon } from "./Sidebar";

export default function LandingHero() {
  return (
    <div className="text-center">
      <div className="mb-6 flex items-center justify-center gap-2 text-stone-500">
        <SparkleIcon className="h-4 w-4 text-accent" />
        <span className="text-sm">Zenline AI · trend intelligence</span>
      </div>
      <h1 className="font-serif text-[2rem] font-semibold tracking-tight text-stone-900 md:text-[2.25rem]">
        What do you want to do today?
      </h1>
    </div>
  );
}
