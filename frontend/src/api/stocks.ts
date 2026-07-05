import apiClient from "./client";
import type { Stock, StockFinancial, StockPrice } from "@/types/stock";
import type { StockTechnical, TechnicalPeriod } from "@/types/technical";

export type { Stock, StockFinancial, StockPrice };

export const stocksApi = {
  list: () => apiClient.get<Stock[]>("/stocks/"),

  get: (code: string) => apiClient.get<Stock>(`/stocks/${code}/`),

  create: (data: Omit<Stock, "id">) =>
    apiClient.post<Stock>("/stocks/", data),

  update: (code: string, data: Partial<Stock>) =>
    apiClient.put<Stock>(`/stocks/${code}/`, data),

  delete: (code: string) => apiClient.delete(`/stocks/${code}/`),

  getFinancials: (code: string) =>
    apiClient.get<StockFinancial[]>(`/stocks/${code}/financials/`),

  createFinancial: (
    code: string,
    data: Omit<StockFinancial, "id">
  ) => apiClient.post<StockFinancial>(`/stocks/${code}/financials/`, data),

  getPrices: (code: string, limit?: number) =>
    apiClient.get<StockPrice[]>(`/stocks/${code}/prices/`, {
      params: limit ? { limit } : undefined,
    }),

  getTechnical: (code: string, period: TechnicalPeriod = "1y") =>
    apiClient.get<StockTechnical>(`/stocks/${code}/technical/`, {
      params: { period },
    }),

  resetFinancials: (
    code: string,
    options: { keep_manual?: boolean; resync?: boolean } = {}
  ) =>
    apiClient.post<{
      deleted_auto: number;
      deleted_manual: number;
      synced_count: number;
      sync_error: string | null;
      message: string;
    }>(`/stocks/${code}/financials/reset/`, options),
};
