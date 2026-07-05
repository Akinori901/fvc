import apiClient from "./client";
import type { Recommendations } from "@/types/recommendations";

export const recommendationsApi = {
  list: () => apiClient.get<Recommendations>("/stocks/recommendations/"),
};
