import apiClient from "./client";

export interface DividendRecord {
  date: string;
  amount: string;
  source: string;
}

export const dividendApi = {
  getStockDividends: (code: string) =>
    apiClient.get<DividendRecord[]>(`/stocks/${code}/dividends/`),
};
