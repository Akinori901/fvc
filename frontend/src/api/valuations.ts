import apiClient from "./client";
import type { ValuationResult, CalculateRequest, ReverseCalculateRequest, ImpliedGrowthResult } from "@/types/valuation";

export type { ValuationResult, CalculateRequest, ReverseCalculateRequest, ImpliedGrowthResult };

export const valuationsApi = {
  calculate: (data: CalculateRequest) =>
    apiClient.post<ValuationResult>("/valuations/calculate/", data),

  reverseCalculate: (data: ReverseCalculateRequest) =>
    apiClient.post<ImpliedGrowthResult>("/valuations/reverse-calculate/", data),

  list: (limit?: number) =>
    apiClient.get<ValuationResult[]>("/valuations/", {
      params: limit ? { limit } : undefined,
    }),

  get: (id: number) =>
    apiClient.get<ValuationResult>(`/valuations/${id}/`),

  listByStock: (code: string) =>
    apiClient.get<ValuationResult[]>(`/stocks/${code}/valuations/`),
};
