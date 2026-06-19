export type ChatMode = "trends" | "crosscheck" | "roi" | "freeform" | "category" | "competitors";

export type DemandDriver = "consumer_pull" | "trade_push" | "mixed";

export type SourceType = "news" | "marketplace" | "trade" | "social" | "discovery" | "web";

export interface MarketCapture {
  market: string;
  tam_total_chf_m: number;
  category_tam_chf_m: number;
  category_share_pct: number;
  estimated_capture_rate_pct: number;
  addressable_revenue_chf_m: number;
  methodology_note?: string;
}

export interface EvidenceItem {
  id: number;
  title: string;
  url: string;
  snippet: string;
  source_type: SourceType;
  relevance: number;
  domain?: string;
}

export interface TrajectoryPoint {
  label: string;
  demand_index: number;
  phase?: string;
}

export interface BloomPrediction {
  keyword: string;
  bloom_score: number;
  bloom_stage?: string;
  bloom_badge?: string;
  timing_window?: string;
  opportunity?: string;
  bloom_rationale?: string;
  weak_signal_note?: string;
  recommended_action?: string;
  confidence?: string;
  coverage_status?: string;
  trajectory?: TrajectoryPoint[];
  evidence_ids?: number[];
  evidence_urls?: string[];
  signal_breakdown?: {
    early_stage?: number;
    source_diversity?: number;
    coverage_gap?: number;
    recency?: number;
    source_count?: number;
    computed_score?: number;
    llm_score?: number;
  };
  score_math?: BloomScoreMath;
}

export interface BloomScoreMath {
  formula?: string;
  computed_formula?: string;
  weights?: Record<string, number>;
  components?: Record<string, number>;
  computed_score?: number;
  llm_score?: number;
  blend_weights?: { computed?: number; llm?: number };
  final_score?: number;
  plain_english?: string;
}

export interface ProductStocking {
  style?: string;
  features?: string[];
  example_products?: string;
  priority?: string;
  timing?: string;
  rationale?: string;
  evidence_ids?: number[];
  evidence_urls?: string[];
}

export interface CategoryOption {
  id: string;
  label: string;
  icon?: string;
  search_hint?: string;
}

export interface PlaybookItem {
  priority?: number;
  action: string;
  horizon?: string;
  rationale?: string;
  keyword?: string;
}

export interface ChartData {
  bloom_ranking?: Array<{ name: string; score: number; stage?: string }>;
  trajectories?: Array<{ keyword: string; points: TrajectoryPoint[] }>;
  source_mix?: Array<{ type: string; count: number }>;
  capture_funnel?: Array<{ label: string; value: number }>;
}

export interface Recommendation {
  rank?: number;
  combined_rank?: number;
  keyword?: string;
  opportunity?: string;
  signal_score?: number;
  confidence?: string;
  recommended_action?: string;
  evidence_urls?: string[];
  evidence_ids?: number[];
  coverage_status?: string;
  range_tag?: string;
  market_capture?: MarketCapture;
  assortment_items?: Array<{
    category: string;
    examples: string;
    priority: string;
  }>;
}

export interface EmergingTrend {
  keyword?: string;
  opportunity?: string;
  bloom_score?: number;
  bloom_badge?: string;
  timing_window?: string;
  recommended_action?: string;
  coverage_status?: string;
}

export interface ChatResponse {
  reply: string;
  mode: ChatMode;
  recommendations: Recommendation[];
  emerging_trends: EmergingTrend[];
  bloom_predictions?: BloomPrediction[];
  product_stocking?: ProductStocking[];
  evidence?: EvidenceItem[];
  charts?: ChartData;
  retailer_playbook?: PlaybookItem[];
  market_capture?: MarketCapture | null;
  evidence_urls: string[];
  demand_driver?: DemandDriver | null;
  score_explanation?: Record<string, unknown> | null;
  steps: string[];
  used_live_search: boolean;
  show_category_prompt?: boolean;
  category_options?: CategoryOption[];
  selected_category?: string | null;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  response?: ChatResponse;
}
