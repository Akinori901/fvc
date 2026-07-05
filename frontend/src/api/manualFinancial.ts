import apiClient from "./client";

export interface ManualFinancialData {
  fiscal_year: number;
  bps: string | null;
  eps: string | null;
  roe: string | null;
  eps_forecast: string | null;
  revenue: number | null;
  operating_income: number | null;
  source: string;
  source_label: string;
  note: string;
  is_overridden_by_auto: boolean;
  updated_at: string;
}

export interface ManualFinancialInput {
  fiscal_year: number;
  bps?: number | null;
  eps?: number | null;
  roe?: number | null;
  eps_forecast?: number | null;
  revenue?: number | null;
  operating_income?: number | null;
  source?: string;
  note?: string;
  growth_rate?: number;
}

export interface ManualFinancialCalculation {
  fair_pbr: string;
  fair_value: string;
  discount_rate: string;
  current_pbr: string;
}

export interface ManualFinancialResponse {
  financial: ManualFinancialData & { is_manual: boolean };
  calculation: ManualFinancialCalculation | null;
}

export const manualFinancialApi = {
  list: (code: string) =>
    apiClient.get<ManualFinancialData[]>(`/stocks/${code}/financials/manual/`),

  save: (code: string, data: ManualFinancialInput) =>
    apiClient.post<ManualFinancialResponse>(`/stocks/${code}/financials/manual/`, data),

  delete: (code: string, fiscalYear: number) =>
    apiClient.delete(`/stocks/${code}/financials/manual/${fiscalYear}/`),
};
