"use client";

import type { RecentChat } from "@/lib/recentChats";

type Props = {
  recentChats: RecentChat[];
  onNewChat: () => void;
  onSelectRecent: (chat: RecentChat) => void;
  activeId?: string;
  liveSearchAvailable?: boolean | null;
};

function SparkleIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path d="M12 2l1.2 4.2L17.5 8 13.2 9.2 12 13.5 10.8 9.2 6.5 8l4.3-1.8L12 2zm0 10.5l.9 3.1 3.2 1.4-3.2 1.3-.9 3.2-.9-3.2-3.2-1.3 3.2-1.4.9-3.1z" />
    </svg>
  );
}

export default function Sidebar({
  recentChats,
  onNewChat,
  onSelectRecent,
  activeId,
  liveSearchAvailable,
}: Props) {
  return (
    <aside className="flex h-screen w-[260px] shrink-0 flex-col border-r border-stone-200/80 bg-sidebar px-4 py-5">
      <div className="flex items-center gap-2 px-2">
        <SparkleIcon className="h-4 w-4 text-accent" />
        <span className="text-[15px] font-semibold tracking-tight text-stone-900">ZenScout</span>
      </div>

      {liveSearchAvailable !== null && (
        <p
          className={`mt-3 px-2 text-[11px] ${
            liveSearchAvailable ? "text-emerald-600" : "text-amber-600"
          }`}
        >
          {liveSearchAvailable
            ? "Live web search ready"
            : "Add API keys in .env and run make api"}
        </p>
      )}

      <button
        type="button"
        onClick={onNewChat}
        className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl border border-stone-200 bg-surface px-4 py-2.5 text-sm font-medium text-stone-800 shadow-sm transition hover:bg-white"
      >
        <span className="text-lg leading-none">+</span>
        New chat
      </button>

      <div className="mt-8 flex-1 overflow-y-auto">
        <p className="px-2 text-xs font-medium text-stone-400">Recent</p>
        {recentChats.length === 0 ? (
          <p className="mt-3 px-2 text-[12px] leading-relaxed text-stone-400">
            Your chats will appear here after you ask something.
          </p>
        ) : (
          <ul className="mt-2 space-y-0.5">
            {recentChats.map((item) => (
              <li key={item.id}>
                <button
                  type="button"
                  onClick={() => onSelectRecent(item)}
                  className={`w-full rounded-lg px-2 py-2 text-left text-[13px] transition hover:bg-stone-200/50 ${
                    activeId === item.id ? "bg-stone-200/60 text-stone-900" : "text-stone-600"
                  }`}
                >
                  {item.label}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="mt-auto flex items-center gap-3 border-t border-stone-200/80 pt-4">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-accent text-sm font-semibold text-white">
          C
        </div>
        <div className="min-w-0">
          <p className="truncate text-sm font-medium text-stone-900">Category manager</p>
          <p className="truncate text-xs text-stone-500">Swiss outdoor retail</p>
        </div>
      </div>
    </aside>
  );
}

export { SparkleIcon };
