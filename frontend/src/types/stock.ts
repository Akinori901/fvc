export interface Stock {
  id: number;
  code: string;
  name: string;
  market: string;
  market_type?: string; // "JP" | "US"。米国株はドル建て表示に使う
  sector: string;
  latest_price: string | null;
  latest_price_date: string | null;
  is_active: boolean;
  // 配当評価
  dividend_yield?: string | null;
  payout_ratio?: string | null;
  consecutive_dividend_years?: number | null;
  progressive_dividend_years?: number | null;
  dividend_score?: number | null;
  // FCF指標
  fcf?: number | null;
  fcf_yield?: string | null;
  fcf_margin?: string | null;
  fcf_score?: number | null;
  // オーナー経営指標
  is_owner_managed?: boolean;
  owner_ratio?: string | null;
  owner_match_type?: "exact" | "family" | "company" | null;
  representative_name?: string | null;
  owner_shareholders?: {
    shareholder_name: string;
    ownership_ratio: string;
    match_type: string;
    rank: number;
  }[];
  // 業界平均推計（業界下限ROEでの保守シナリオ適正株価）
  industry_metrics?: {
    sector: string;
    min_roe: string;
    max_roe: string;
    min_roe_fair_value: string;
    min_roe_fair_pbr: string;
  } | null;
  // スクリーニング系メトリクス（ヘッダーバッジ用）
  evaluation_zone?: string | null;
  growth_rate_label?: string | null;
  roe_trend?: string | null;
  eps_growth_yoy?: string | null;
  eps_cagr_3y?: string | null;
  sl_ratio?: string | null;
}

export interface StockFinancial {
  id: number;
  fiscal_year: number;
  bps: string;
  eps: string | null;
  roe: string | null;
  net_assets: number | null;
  total_shares: number | null;
  revenue: number | null;
  eps_forecast: string | null;
  adj_factor: string;
}

export interface StockPrice {
  id: number;
  date: string;
  close_price: string;
  pbr: string | null;
  volume: number | null;
}
