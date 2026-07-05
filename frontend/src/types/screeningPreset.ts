export interface ScreeningFilters {
  growth_rate: number;
  sector: string | null;
  include_inactive: boolean;
  min_discount: number | null;
  min_eps_growth_yoy: number | null;
  min_eps_cagr_3y: number | null;
  roe_trend: "improving" | "declining" | "stable" | null;
  min_roe: number | null;
  max_sl_ratio: number | null;
  min_dividend_yield: number | null;
  max_payout_ratio: number | null;
  min_consecutive_dividend_years: number | null;
  min_progressive_dividend_years: number | null;
  min_liquidity_level: "high" | "medium" | "low" | "very_low" | null;
  min_momentum_signal: "strong_buy" | "buy" | "neutral" | "caution" | "sell" | null;
  owner_managed_only: boolean;
  min_fcf_yield: number | null;
  min_overall_score: number | null;
}

export const DEFAULT_FILTERS: ScreeningFilters = {
  growth_rate: 0.03,
  sector: null,
  include_inactive: false,
  min_discount: null,
  min_eps_growth_yoy: null,
  min_eps_cagr_3y: null,
  roe_trend: null,
  min_roe: null,
  max_sl_ratio: null,
  min_dividend_yield: null,
  max_payout_ratio: null,
  min_consecutive_dividend_years: null,
  min_progressive_dividend_years: null,
  min_liquidity_level: null,
  min_momentum_signal: null,
  owner_managed_only: false,
  min_fcf_yield: null,
  min_overall_score: null,
};

export interface ScreeningPreset {
  id: number;
  name: string;
  priority: number;
  filters: ScreeningFilters;
}
