export interface EvaluationSignal {
  category: string;
  label: string;
  impact: number;
}

export interface ReitResult {
  code: string;
  name: string;
  sector: string;
  latest_price: string | null;
  latest_price_date: string | null;
  bps: string | null;
  p_nav: string | null;
  annual_dividend: string | null;
  dividend_yield: string | null;
  eps: string | null;
  evaluation_zone: string | null;
  evaluation_score: number | null;
  evaluation_signals: EvaluationSignal[];
  price_position_52w: string | null;
  payout_coverage: string | null;
}
