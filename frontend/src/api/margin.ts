import apiClient from "./client";

export interface MarginBalanceRecord {
  date: string;
  long_balance: number | null;
  long_balance_change: number | null;
  short_balance: number | null;
  short_balance_change: number | null;
  sl_ratio: string | null;
}

export interface StockMarginResponse {
  latest: MarginBalanceRecord | null;
  history: MarginBalanceRecord[];
}

export const marginApi = {
  getStockMargin: (code: string) =>
    apiClient.get<StockMarginResponse>(`/stocks/${code}/margin/`),
};
