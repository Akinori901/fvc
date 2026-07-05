import apiClient from "./client";
import type { FxAnalysis } from "@/types/fx";

export const fxApi = {
  getAnalysis: () => apiClient.get<FxAnalysis>("/fx/analysis/"),
};
