"use client";

import { useCallback, useRef, useState } from "react";
import { sendChat } from "@/lib/api";
import type { ChatMessage as ChatMessageType, ChatMode } from "@/lib/types";
import ChatMessage from "./ChatMessage";

type Props = {
  mode: ChatMode;
  market: string;
  input: string;
  onInputChange: (value: string) => void;
  onModeUsed?: () => void;
};

export default function ChatBox({
  mode,
  market,
  input,
  onInputChange,
  onModeUsed,
}: Props) {
  const [messages, setMessages] = useState<ChatMessageType[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  const scrollDown = () => {
    setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 100);
  };

  const handleSend = useCallback(async () => {
    const text = input.trim();
    if (!text || loading) return;

    setError(null);
    setLoading(true);
    onInputChange("");
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    scrollDown();

    try {
      const response = await sendChat(text, mode, market);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: response.reply, response },
      ]);
      onModeUsed?.();
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Request failed";
      setError(msg);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `Sorry — ${msg}. Is the API running on port 8000? Try: make api`,
        },
      ]);
    } finally {
      setLoading(false);
      scrollDown();
    }
  }, [input, loading, mode, market, onInputChange, onModeUsed]);

  const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="mx-auto max-w-4xl px-6 pb-16">
      <div className="min-h-[280px] max-h-[480px] overflow-y-auto rounded-t-2xl border border-b-0 border-slate-200 bg-slate-50/50 p-4 space-y-4">
        {messages.length === 0 && (
          <p className="text-center text-sm text-slate-500 py-12">
            Pick an intent above or type a question — Scout uses Claude + Tavily live.
          </p>
        )}
        {messages.map((m, i) => (
          <ChatMessage key={i} message={m} />
        ))}
        {loading && (
          <p className="text-center text-sm text-slate-500 animate-pulse">
            Scout is searching the web and synthesizing…
          </p>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="flex gap-2 rounded-b-2xl border border-slate-200 bg-white p-3 shadow-lg">
        <textarea
          value={input}
          onChange={(e) => onInputChange(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder="Ask ZenScout anything about outdoor trends, your product idea, or ROI…"
          rows={2}
          className="flex-1 resize-none rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none focus:border-navy focus:ring-1 focus:ring-navy/20"
          disabled={loading}
        />
        <button
          type="button"
          onClick={handleSend}
          disabled={loading || !input.trim()}
          className="self-end rounded-xl bg-navy px-6 py-3 text-sm font-medium text-white hover:bg-navy/90 disabled:opacity-50"
        >
          Send
        </button>
      </div>
      {error && <p className="mt-2 text-xs text-red-600">{error}</p>}
      <p className="mt-2 text-xs text-slate-400">
        Mode: <strong>{mode}</strong> · Market: <strong>{market}</strong> · Enter to send,
        Shift+Enter for new line
      </p>
    </div>
  );
}
