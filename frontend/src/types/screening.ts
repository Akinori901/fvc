import type { EvaluationZone } from "@/utils/evaluation";

export interface ScreeningResult {
  code: string;
  name: string;
  sector: string;
  latest_price: string | null;
  latest_price_date: string | null;
  bps: string | null;
  eps: string | null;
  roe: string | null;
  fair_pbr: string | null;
  fair_value: string | null;
  discount_rate: string | null;
  evaluation_zone: EvaluationZone | null;
  current_pbr: string | null;
  implied_growth_rate: string | null;
  growth_rate_label: string | null;
  company_forecast_growth_rate: string | null;
  is_active: boolean;
  not_calculable_reason: string | null;
  is_manual_financial: boolean;
  eps_growth_yoy: string | null;
  eps_cagr_3y: string | null;
  roe_trend: "improving" | "declining" | "stable" | null;
  revenue_growth_yoy: string | null;
  op_income_growth_yoy: string | null;
  sl_ratio: string | null;
  long_balance: number | null;
  short_balance: number | null;
  long_balance_change: number | null;
  // 信用買残トレンド（指定期間の増減）
  long_balance_change_pct: string | null;
  long_balance_trend: "increasing" | "decreasing" | "flat" | null;
  // テクニカル指標（52週高値効果）
  price_position_52w: string | null;
  near_52w_high: boolean | null;
  distance_from_52w_high: string | null;
  volume_ratio_20d: string | null;
  ma_25_deviation: string | null;
  momentum_signal: "strong_buy" | "buy" | "neutral" | "caution" | "sell" | null;
  // 流動性指標
  avg_turnover_20d: string | null;
  liquidity_level: "high" | "medium" | "low" | "very_low" | null;
  // 配当評価
  dividend_yield: string | null;
  payout_ratio: string | null;
  consecutive_dividend_years: number | null;
  progressive_dividend_years: number | null;
  dividend_score: number | null;
  // FCF指標
  fcf: number | null;
  fcf_yield: string | null;
  fcf_margin: string | null;
  fcf_score: number | null;
  // オーナー経営指標
  is_owner_managed: boolean;
  owner_ratio: string | null;
  owner_match_type: "exact" | "family" | "company" | null;
}
