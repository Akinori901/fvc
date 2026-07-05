import apiClient from "./client";
import type { ReitResult } from "@/types/reit";

export const reitApi = {
  list: (market_type = "JP") =>
    apiClient.get<ReitResult[]>("/stocks/reit/", { params: { market_type } }),
};
