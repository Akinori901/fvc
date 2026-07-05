export type TechnicalPeriod = "1m" | "3m" | "6m" | "1y" | "all";

export interface IndicatorSeriesPoint {
  date: string;
  close: string;
  ma_25: string | null;
  ma_75: string | null;
  ma_200: string | null;
  bb_upper: string | null;
  bb_middle: string | null;
  bb_lower: string | null;
  rsi_14: string | null;
  macd: string | null;
  macd_signal: string | null;
  macd_hist: string | null;
  stoch_k: string | null;
  stoch_d: string | null;
  atr_14: string | null;
}

export type BbSignal = "above_upper" | "below_lower" | "inside";
export type RsiSignal = "overbought" | "oversold" | "neutral";
export type StochSignal = "overbought" | "oversold" | "neutral";
export type MacdCross = "golden" | "dead" | "none";
export type MomentumSignal =
  | "strong_up"
  | "up"
  | "flat"
  | "down"
  | "strong_down";

export interface IndicatorLatest {
  ma_25: string | null;
  ma_75: string | null;
  ma_200: string | null;
  ma_25_deviation_pct: string | null;
  ma_75_deviation_pct: string | null;
  ma_200_deviation_pct: string | null;
  bb_upper: string | null;
  bb_middle: string | null;
  bb_lower: string | null;
  bb_position: string | null;
  bb_signal: BbSignal | null;
  rsi_14: string | null;
  rsi_signal: RsiSignal | null;
  macd: string | null;
  macd_signal: string | null;
  macd_hist: string | null;
  macd_cross: MacdCross | null;
  stoch_k: string | null;
  stoch_d: string | null;
  stoch_signal: StochSignal | null;
  atr_14: string | null;
  atr_pct: string | null;
  momentum_25d_pct: string | null;
  momentum_signal: MomentumSignal | null;
}

export interface StockTechnical {
  code: string;
  data_points: number;
  insufficient_data: boolean;
  atr_approximation: "close_to_close" | "true_range";
  latest: IndicatorLatest | null;
  series: IndicatorSeriesPoint[];
}
