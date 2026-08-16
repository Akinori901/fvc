import apiClient from "./client";
import type { ScreeningResult } from "@/types/screening";

export interface ScreeningParams {
  growth_rate?: number;
  min_discount?: number;
  sector?: string;
  market_type?: string;
  include_inactive?: boolean;
  min_eps_growth_yoy?: number;
  min_eps_cagr_3y?: number;
  roe_trend?: "improving" | "declining" | "stable";
  min_roe?: number;
  max_sl_ratio?: number;
  min_dividend_yield?: number;
  max_payout_ratio?: number;
  min_consecutive_dividend_years?: number;
  min_progressive_dividend_years?: number;
  min_liquidity_level?: "high" | "medium" | "low" | "very_low";
  min_momentum_signal?: "strong_buy" | "buy" | "neutral" | "caution" | "sell";
  owner_managed_only?: boolean;
  min_fcf_yield?: number;
  long_balance_trend?: "increasing" | "decreasing";
  margin_trend_months?: number;
  margin_trend_threshold_pct?: number;
  // 買い時テクニカルシグナル（ON の時だけ送信）
  ma_golden_cross_only?: boolean;
  price_cross_ma25_only?: boolean;
  price_cross_ma75_only?: boolean;
  macd_golden_cross_only?: boolean;
  rsi_rebound_only?: boolean;
  pullback_buy_only?: boolean;
  // ページング/ソート/検索（サーバーサイド）
  limit?: number;
  offset?: number;
  sort_by?: string;
  order?: "asc" | "desc";
  search?: string;
  min_overall_score?: number;
}

export interface ScreeningPage {
  count: number;
  results: ScreeningResult[];
  generated_at: string | null;
}

export const screeningApi = {
  search: (params: ScreeningParams = {}) =>
    apiClient.get<ScreeningPage>("/stocks/screening/", { params }),
  sectors: (marketType = "JP") =>
    apiClient.get<string[]>("/stocks/screening/sectors/", { params: { market_type: marketType } }),
};
