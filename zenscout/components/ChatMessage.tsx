"use client";

import type { ChatMessage as ChatMessageType } from "@/lib/types";
import ScoutResults from "./ScoutResults";

type Props = {
  message: ChatMessageType;
  onCategorySelect?: (categoryId: string, label: string, trendKeywords: string[]) => void;
  categoryLoading?: boolean;
};

export default function ChatMessage({ message, onCategorySelect, categoryLoading }: Props) {
  const isUser = message.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start w-full"}`}>
      <div
        className={`max-w-[min(100%,720px)] rounded-2xl px-4 py-3 ${
          isUser
            ? "bg-stone-800 text-white"
            : "border border-stone-200 bg-surface text-stone-800 w-full max-w-3xl"
        }`}
      >
        <p className="whitespace-pre-wrap text-[14px] leading-relaxed">{message.content}</p>
        {message.response && !isUser && (
          <ScoutResults
            data={message.response}
            onCategorySelect={onCategorySelect}
            categoryLoading={categoryLoading}
          />
        )}
      </div>
    </div>
  );
}
