"use client";

export default function Navbar() {
  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <div className="flex items-center gap-2">
          <svg
            className="h-8 w-8 text-navy"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
          >
            <path d="M12 2L4 20h16L12 2z" />
            <circle cx="12" cy="14" r="2" fill="currentColor" />
          </svg>
          <span className="text-xl font-semibold text-navy">
            Zen<span className="font-normal text-slate-500">Scout</span>
          </span>
        </div>
        <nav className="hidden items-center gap-8 text-sm text-slate-600 md:flex">
          <a href="#" className="hover:text-navy">
            Home
          </a>
          <a href="#how-it-works" className="hover:text-navy">
            How it Works
          </a>
          <a href="#chat" className="hover:text-navy">
            Scout Chat
          </a>
        </nav>
        <div className="flex items-center gap-3">
          <a
            href="http://localhost:8501"
            target="_blank"
            rel="noopener noreferrer"
            className="hidden rounded-full border border-navy px-4 py-2 text-sm text-navy hover:bg-slate-50 sm:inline-block"
          >
            Analyst view
          </a>
          <button
            type="button"
            disabled
            title="Demo mode"
            className="rounded-full bg-navy px-5 py-2 text-sm font-medium text-white opacity-90"
          >
            Demo
          </button>
        </div>
      </div>
    </header>
  );
}
