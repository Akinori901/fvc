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
}

export const screeningApi = {
  search: (params: ScreeningParams = {}) =>
    apiClient.get<ScreeningResult[]>("/stocks/screening/", { params }),
};
