import apiClient from "./client";
import type { EtfResult } from "@/types/etf";

export const etfApi = {
  list: (market_type = "JP") =>
    apiClient.get<EtfResult[]>("/stocks/etf/", { params: { market_type } }),
};
