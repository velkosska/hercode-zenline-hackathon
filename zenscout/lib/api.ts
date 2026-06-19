import type { ChatMode, ChatResponse } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type LiveTrendPoint = {
  name: string;
  momentum: number;
  url?: string;
};

export type LiveTrendsResponse = {
  market: string;
  live: boolean;
  data_source?: "tavily" | "pipeline" | "none";
  notice?: string | null;
  updated_at: string;
  series: LiveTrendPoint[];
  source_count: number;
};

export type CompetitorRow = {
  keyword: string;
  overall: string;
  retailers: Record<string, { status: string; listings: number }>;
  sample_urls: string[];
};

export type CompetitorSnapshot = {
  market: string;
  live: boolean;
  updated_at: string;
  retailer_domains: string[];
  rows: CompetitorRow[];
  gap_count: number;
};

export type DashboardOpportunity = {
  id: string;
  rank: number;
  keyword: string;
  title: string;
  subtitle: string;
  category_tag: string;
  status: "buy_now" | "worth_testing" | "keep_watching";
  status_label: string;
  addressable_chf_m: number;
  market_label: string;
  start_stocking: string;
  peak_label: string;
  source_count: number;
  recommended_action: string;
  chat_prompt: string;
};

export type DashboardTrendSeries = {
  key: string;
  label: string;
  keyword: string;
  color: string;
  current_score: number;
  score_math?: import("./types").BloomScoreMath;
};

export type DashboardResponse = {
  market: string;
  region_label: string;
  sector_label: string;
  updated_at: string;
  scan_date?: string;
  data_source?: "tavily" | "pipeline" | "none";
  live_search?: boolean;
  notice?: string | null;
  how_it_works: Array<{ step: string; title: string; body: string }>;
  chat_prompts: Array<{
    id: string;
    mode: ChatMode;
    title: string;
    description: string;
    prompt: string;
    accent: string;
  }>;
  metrics: {
    opportunities_found: number;
    ready_to_buy: number;
    worth_testing: number;
    keep_watching: number;
    total_market_chf_m: number;
  };
  opportunities: DashboardOpportunity[];
  trend_chart: {
    series: DashboardTrendSeries[];
    chart_points: Array<Record<string, string | number>>;
    notice?: string | null;
  };
  filters: Array<{ id: string; label: string; count: number }>;
};

export async function fetchDashboard(market = "CH"): Promise<DashboardResponse | null> {
  try {
    const res = await fetch(`${API_URL}/dashboard?market=${market}`, { cache: "no-store" });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export async function checkLiveSearch(): Promise<boolean> {
  try {
    const res = await fetch(`${API_URL}/health`, { cache: "no-store" });
    if (!res.ok) return false;
    const data = await res.json();
    return Boolean(data.live_search_available);
  } catch {
    return false;
  }
}

export async function fetchLiveTrends(market = "CH"): Promise<LiveTrendsResponse | null> {
  try {
    const res = await fetch(`${API_URL}/live-trends?market=${market}`, { cache: "no-store" });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export async function fetchCompetitorSnapshot(market = "CH"): Promise<CompetitorSnapshot | null> {
  try {
    const res = await fetch(`${API_URL}/competitor-snapshot?market=${market}`, { cache: "no-store" });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export async function sendChat(
  message: string,
  mode: ChatMode = "freeform",
  market: string = "CH",
  trendContext: string[] = []
): Promise<ChatResponse> {
  const res = await fetch(`${API_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, mode, market, trend_context: trendContext }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    const detail = err.detail;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail) || "Chat request failed");
  }
  return res.json();
}
