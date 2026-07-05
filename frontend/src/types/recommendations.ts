export interface RecommendedStock {
  code: string;
  name: string;
  latest_price: string | null;
  metrics: Record<string, string>;
}

export interface Recommendations {
  generated_at: string;
  long_term: RecommendedStock[];
  day_trade: RecommendedStock[];
  range_bound: RecommendedStock[];
}
