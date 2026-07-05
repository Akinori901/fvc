export interface ValuationResult {
  id: number;
  stock_id: number;
  growth_rate: string;
  fair_pbr: string;
  fair_value: string;
  current_price: string;
  discount_rate: string;
  is_undervalued: boolean;
  // ゴードン成長モデル追加フィールド（旧レコードは null）
  roe: string | null;
  cost_of_capital: string | null;
  bps: string | null;
  current_pbr: string | null;
  implied_growth_rate: string | null;
}

export interface CalculateRequest {
  stock_code: string;
  growth_rate: number;
  current_price?: number | null;
}

export interface ReverseCalculateRequest {
  stock_code: string;
  current_price?: number | null;
}

export interface ImpliedGrowthResult {
  stock_code: string;
  stock_name: string;
  current_price: string;
  bps: string;
  roe: string;
  cost_of_capital: string;
  current_pbr: string;
  implied_growth_rate: string;
  growth_rate_label: string;
}
