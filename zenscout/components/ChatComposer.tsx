"use client";

import { useCallback, useRef } from "react";
import { sendChat } from "@/lib/api";
import type { ChatMessage as ChatMessageType, ChatMode } from "@/lib/types";
import ChatMessage from "./ChatMessage";

type Props = {
  mode: ChatMode;
  market: string;
  input: string;
  onInputChange: (value: string) => void;
  messages: ChatMessageType[];
  setMessages: React.Dispatch<React.SetStateAction<ChatMessageType[]>>;
  loading: boolean;
  setLoading: (v: boolean) => void;
  showEmptyState: boolean;
  variant?: "default" | "landing";
  liveSearchAvailable?: boolean | null;
  onSessionSaved: (firstPrompt: string, messages: ChatMessageType[]) => void;
};

function extractTrendContext(messages: ChatMessageType[]): string[] {
  for (let i = messages.length - 1; i >= 0; i--) {
    const m = messages[i];
    if (m.role === "assistant" && m.response?.bloom_predictions?.length) {
      return m.response.bloom_predictions.map((p) => p.keyword).slice(0, 5);
    }
  }
  return [];
}

export default function ChatComposer({
  mode,
  market,
  input,
  onInputChange,
  messages,
  setMessages,
  loading,
  setLoading,
  showEmptyState,
  variant = "default",
  liveSearchAvailable,
  onSessionSaved,
}: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const firstPromptRef = useRef<string | null>(null);

  const scrollDown = () => {
    setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 80);
  };

  const submitMessage = useCallback(
    async (text: string, sendMode: ChatMode, trendContext: string[] = []) => {
      if (!text.trim() || loading) return;

      if (messages.length === 0) {
        firstPromptRef.current = text;
      }

      setLoading(true);
      onInputChange("");
      const userMessage: ChatMessageType = { role: "user", content: text };
      setMessages((prev) => [...prev, userMessage]);
      scrollDown();

      try {
        const response = await sendChat(text, sendMode, market, trendContext);
        setMessages((prev) => {
          const next = [...prev, { role: "assistant" as const, content: response.reply, response }];
          onSessionSaved(firstPromptRef.current ?? text, next);
          return next;
        });
      } catch (e) {
        const msg = e instanceof Error ? e.message : "Request failed";
        setMessages((prev) => {
          const next = [
            ...prev,
            {
              role: "assistant" as const,
              content: `Sorry — ${msg}. Start the API with \`make api\` in hercode-zenline-hackathon.`,
            },
          ];
          onSessionSaved(firstPromptRef.current ?? text, next);
          return next;
        });
      } finally {
        setLoading(false);
        scrollDown();
      }
    },
    [loading, market, messages.length, onInputChange, setMessages, setLoading, onSessionSaved]
  );

  const handleSend = useCallback(() => {
    const text = input.trim();
    if (!text) return;
    submitMessage(text, mode);
  }, [input, mode, submitMessage]);

  const handleCategorySelect = useCallback(
    (categoryId: string, label: string, trendKeywords: string[]) => {
      const trends = trendKeywords.length ? trendKeywords : extractTrendContext(messages);
      const prompt = `Category drill-down: ${label} — what styles and product features should we stock for Swiss outdoor retail?`;
      submitMessage(prompt, "category", trends);
    },
    [messages, submitMessage]
  );

  const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const isLanding = variant === "landing";

  return (
    <div className={`flex w-full flex-col ${showEmptyState ? "max-w-4xl mx-auto" : "max-w-3xl flex-1 min-h-0"}`}>
      {!showEmptyState && (
        <div className="mb-4 flex-1 min-h-0 overflow-y-auto px-1 space-y-4">
          {messages.map((m, i) => (
            <ChatMessage
              key={i}
              message={m}
              onCategorySelect={handleCategorySelect}
              categoryLoading={loading}
            />
          ))}
          {loading && (
            <p className="text-center text-sm text-stone-400 animate-pulse py-4">
              Searching the web live and synthesizing…
            </p>
          )}
          <div ref={bottomRef} />
        </div>
      )}

      <div className="relative w-full rounded-[28px] border border-stone-200/80 bg-surface shadow-sm">
        <textarea
          value={input}
          onChange={(e) => onInputChange(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder={
            isLanding
              ? "Ask about a category, an idea, or a price… e.g. 'Will via ferrata kits sell next summer?'"
              : "Ask about a category, an idea, or a price…"
          }
          rows={isLanding ? 3 : showEmptyState ? 3 : 2}
          disabled={loading}
          className="w-full resize-none bg-transparent px-5 pt-5 pb-14 text-[15px] text-stone-800 placeholder:text-stone-400 outline-none"
        />
        <div className="absolute bottom-3 left-4 flex items-center gap-2">
          <span className="rounded-full border border-stone-200 bg-stone-50 px-3 py-1 text-xs text-stone-500">
            Data access
          </span>
          <span
            className={`rounded-full border px-3 py-1 text-xs ${
              liveSearchAvailable
                ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                : liveSearchAvailable === false
                  ? "border-amber-200 bg-amber-50 text-amber-700"
                  : "border-stone-200 bg-stone-50 text-stone-500"
            }`}
          >
            {liveSearchAvailable ? "Web search" : liveSearchAvailable === false ? "Offline" : "Checking…"}
          </span>
        </div>
        <button
          type="button"
          onClick={handleSend}
          disabled={loading || !input.trim()}
          aria-label="Send message"
          className="absolute bottom-3 right-3 flex h-9 w-9 items-center justify-center rounded-full bg-stone-200 text-stone-600 transition hover:bg-stone-300 disabled:opacity-40"
        >
          <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12 19V5M5 12l7-7 7 7" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
      </div>

      {isLanding ? (
        <p className="mt-4 text-center text-xs leading-relaxed text-stone-400">
          Recommendations blend search, social, weather, events and marketplace demand — not just your sales history.
        </p>
      ) : (
        <p className="mt-4 text-center text-xs leading-relaxed text-stone-400">
          After trend spotting, pick a category to drill into styles and features to stock.
        </p>
      )}
    </div>
  );
}
