import apiClient from "./client";

export interface SyncLog {
  id: number;
  sync_type: string;
  provider: string;
  market: string;
  status: string;
  started_at: string;
  finished_at: string | null;
  total_count: number;
  success_count: number;
  error_count: number;
}

export interface SyncTriggerRequest {
  sync_type: "stocks" | "financials" | "prices" | "dividends" | "all";
  market?: "JP" | "US";
  codes?: string[];
}

export const syncApi = {
  trigger: (data: SyncTriggerRequest) =>
    apiClient.post("/stocks/sync/", data),

  logs: (limit?: number) =>
    apiClient.get<SyncLog[]>("/stocks/sync/logs/", {
      params: limit ? { limit } : undefined,
    }),
};
