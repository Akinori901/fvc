export interface WatchlistItem {
  id: number;
  stock_code: string;
  stock_name: string;
  memo: string;
  // screening data (optional, enriched by backend)
  latest_price?: string | null;
  fair_value?: string | null;
  discount_rate?: string | null;
  evaluation_zone?: string | null;
  growth_rate_label?: string | null;
  eps_growth_yoy?: string | null;
  eps_cagr_3y?: string | null;
  roe_trend?: string | null;
  sl_ratio?: string | null;
  dividend_yield?: string | null;
  consecutive_dividend_years?: number | null;
  progressive_dividend_years?: number | null;
  is_owner_managed?: boolean | null;
}
