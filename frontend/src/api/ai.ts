import apiClient from "./client";

export interface AiConfig {
  provider: string;
  model: string;
  is_enabled: boolean;
  has_api_key: boolean;
  updated_at: string | null;
}

export type ExpertRole =
  | "general"
  | "quant"
  | "fundamental"
  | "macro"
  | "technical"
  | "risk_mgmt";

export interface AnalyzeRequest {
  question_type: "pbr_low" | "investment_risk" | "growth_outlook" | "custom" | "price_forecast" | "price_drop_reason" | "dividend_analysis" | "sector_comparison";
  custom_question?: string;
  expert_role?: ExpertRole;
}

export interface AnalyzeResult {
  analysis: string;
  model: string;
  generated_at: string;
  prompt_tokens: number;
  completion_tokens: number;
}

export const aiApi = {
  getConfig: () => apiClient.get<AiConfig>("/ai/config/"),

  updateConfig: (data: {
    api_key?: string;
    model?: string;
    is_enabled?: boolean;
  }) => apiClient.put<AiConfig>("/ai/config/", data),

  analyzeStock: (code: string, data: AnalyzeRequest) =>
    apiClient.post<AnalyzeResult>(`/ai/stocks/${code}/analyze/`, data),
};
