import type { ChatMessage, ChatMode } from "./types";

export type RecentChat = {
  id: string;
  label: string;
  mode: ChatMode;
  market: string;
  prompt: string;
  messages: ChatMessage[];
  updatedAt: number;
};

const STORAGE_KEY = "zenscout-recent-chats";
const MAX_RECENT = 20;

export function truncateLabel(text: string, max = 44): string {
  const t = text.replace(/\s+/g, " ").trim();
  if (t.length <= max) return t;
  return t.slice(0, max - 1) + "…";
}

export function loadRecentChats(): RecentChat[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as RecentChat[];
    return Array.isArray(parsed) ? parsed.sort((a, b) => b.updatedAt - a.updatedAt) : [];
  } catch {
    return [];
  }
}

export function saveRecentChat(chat: RecentChat): RecentChat[] {
  const existing = loadRecentChats().filter((c) => c.id !== chat.id);
  const next = [chat, ...existing].slice(0, MAX_RECENT);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  return next;
}

export function createRecentChat(
  prompt: string,
  mode: ChatMode,
  market: string,
  messages: ChatMessage[]
): RecentChat {
  return {
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
    label: truncateLabel(prompt),
    mode,
    market,
    prompt,
    messages,
    updatedAt: Date.now(),
  };
}
