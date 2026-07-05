export interface EvaluationSignal {
  category: string;
  label: string;
  impact: number;
}

export interface EtfResult {
  code: string;
  name: string;
  sector: string;
  latest_price: string | null;
  latest_price_date: string | null;
  annual_dividend: string | null;
  dividend_yield: string | null;
  return_52w: string | null;
  net_assets: number | null;
  latest_price_52w_ago: string | null;
  evaluation_zone: string | null;
  evaluation_score: number | null;
  evaluation_signals: EvaluationSignal[];
  price_position_52w: string | null;
}
