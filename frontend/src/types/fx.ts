export interface FxRegression {
  beta_0: string;
  beta_1: string;
  fair_value: string;
  residual_std: string;
  r_squared: string;
  current_deviation: string;
  zone: "strong_buy" | "buy" | "neutral" | "sell" | "strong_sell";
}

export interface FxTechnicals {
  rsi_14: string | null;
  bb_upper: string | null;
  bb_middle: string | null;
  bb_lower: string | null;
  ma_200: string | null;
  ma_200_deviation: string | null;
}

export interface FxChartDataPoint {
  date: string;
  rate: string;
  fair_value?: string;
  upper_1s?: string;
  lower_1s?: string;
  upper_2s?: string;
  lower_2s?: string;
}

export interface FxAnalysis {
  current_rate: string;
  current_rate_date: string;
  us_10y: string | null;
  jp_10y: string | null;
  interest_rate_diff: string | null;
  regression: FxRegression | null;
  technicals: FxTechnicals;
  ppp_rate: string | null;
  ppp_deviation: string | null;
  buy_zone_lower: string | null;
  sell_zone_upper: string | null;
  strong_buy_lower: string | null;
  strong_sell_upper: string | null;
  chart_data: FxChartDataPoint[];
}
