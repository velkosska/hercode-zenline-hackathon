"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import ActionCards from "@/components/ActionCards";
import BloomMultiChart from "@/components/BloomMultiChart";
import ChatComposer from "@/components/ChatComposer";
import ChatMessage from "@/components/ChatMessage";
import DashboardHero from "@/components/DashboardHero";
import DashboardMetrics from "@/components/DashboardMetrics";
import DashboardNav from "@/components/DashboardNav";
import HowItWorks from "@/components/HowItWorks";
import OpportunityGrid from "@/components/OpportunityGrid";
import { checkLiveSearch, fetchDashboard, type DashboardOpportunity, type DashboardResponse } from "@/lib/api";
import type { ChatMessage as ChatMessageType, ChatMode } from "@/lib/types";
import {
  createRecentChat,
  loadRecentChats,
  saveRecentChat,
  type RecentChat,
} from "@/lib/recentChats";

export default function HomePage() {
  const [market, setMarket] = useState("CH");
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null);
  const [dashboardLoading, setDashboardLoading] = useState(true);
  const [mode, setMode] = useState<ChatMode>("freeform");
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ChatMessageType[]>([]);
  const [loading, setLoading] = useState(false);
  const [liveSearchAvailable, setLiveSearchAvailable] = useState<boolean | null>(null);
  const sessionIdRef = useRef<string | null>(null);
  const chatRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    checkLiveSearch().then(setLiveSearchAvailable);
  }, []);

  useEffect(() => {
    setDashboardLoading(true);
    fetchDashboard(market).then((data) => {
      setDashboard(data);
      setDashboardLoading(false);
    });
  }, [market]);

  const scrollToChat = () => {
    chatRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const handleIntent = (m: ChatMode, prompt: string) => {
    setMode(m);
    setInput(prompt);
    sessionIdRef.current = null;
    scrollToChat();
  };

  const handleOpenStory = (opp: DashboardOpportunity) => {
    setMode("trends");
    setInput(opp.chat_prompt);
    sessionIdRef.current = null;
    scrollToChat();
  };

  const handleSessionSaved = useCallback(
    (firstPrompt: string, nextMessages: ChatMessageType[]) => {
      const currentId = sessionIdRef.current;
      let chat: RecentChat;

      if (currentId) {
        const existing = loadRecentChats().find((c) => c.id === currentId);
        chat = {
          ...(existing ?? createRecentChat(firstPrompt, mode, market, nextMessages)),
          messages: nextMessages,
          updatedAt: Date.now(),
        };
      } else {
        chat = createRecentChat(firstPrompt, mode, market, nextMessages);
        sessionIdRef.current = chat.id;
      }

      saveRecentChat(chat);
    },
    [mode, market]
  );

  return (
    <div className="min-h-screen bg-canvas">
      <DashboardNav
        market={market}
        sectorLabel={dashboard?.sector_label ?? "Outdoor Retail"}
        regionLabel={dashboard?.region_label ?? "DACH"}
      />

      <main className="mx-auto max-w-6xl px-6">
        <div className="flex justify-end pt-4">
          <select
            value={market}
            onChange={(e) => setMarket(e.target.value)}
            className="rounded-full border border-stone-200/80 bg-surface px-3 py-1.5 text-xs text-stone-600 shadow-sm"
          >
            <option value="CH">Switzerland (CH)</option>
            <option value="DACH">DACH</option>
            <option value="US">US</option>
          </select>
        </div>

        <DashboardHero updatedAt={dashboard?.updated_at} scanDate={dashboard?.scan_date} />

        {dashboardLoading || !dashboard ? (
          <div className="space-y-8 py-8">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-40 animate-pulse rounded-3xl bg-stone-200/40" />
            ))}
          </div>
        ) : (
          <>
            <HowItWorks steps={dashboard.how_it_works} />
            <BloomMultiChart trendChart={dashboard.trend_chart} market={market} dataSource={dashboard.data_source} />
            <ActionCards prompts={dashboard.chat_prompts} onSelect={handleIntent} />
            <DashboardMetrics metrics={dashboard.metrics} />

            <section ref={chatRef} id="chat" className="mt-10 scroll-mt-24">
              <div className="mb-5 text-center">
                <div className="inline-flex items-center gap-2 text-stone-700">
                  <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
                    <path d="M21 15a4 4 0 01-4 4H8l-5 3V7a4 4 0 014-4h10a4 4 0 014 4z" strokeLinejoin="round" />
                  </svg>
                  <h2 className="text-lg font-semibold">Ask ZenScout anything</h2>
                </div>
                <p className="mt-2 text-[14px] text-stone-500">
                  Categories, ideas, ROI — get a plain-English answer grounded in market signals.
                </p>
              </div>

              {messages.length > 0 && (
                <div className="mb-6 space-y-4 rounded-2xl border border-stone-200/80 bg-surface p-4">
                  {messages.map((m, i) => (
                    <ChatMessage key={i} message={m} categoryLoading={loading} />
                  ))}
                  {loading && (
                    <p className="text-center text-sm text-stone-400 animate-pulse py-2">
                      Searching the web live and synthesizing…
                    </p>
                  )}
                </div>
              )}

              <ChatComposer
                mode={mode}
                market={market}
                input={input}
                onInputChange={setInput}
                messages={messages}
                setMessages={setMessages}
                loading={loading}
                setLoading={setLoading}
                showEmptyState={true}
                variant="landing"
                liveSearchAvailable={liveSearchAvailable}
                onSessionSaved={handleSessionSaved}
              />
            </section>

            <OpportunityGrid
              opportunities={dashboard.opportunities}
              filters={dashboard.filters}
              onOpenStory={handleOpenStory}
            />
          </>
        )}
      </main>
    </div>
  );
}
