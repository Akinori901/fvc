import apiClient from "./client";
import type { WatchlistItem } from "@/types/watchlist";

export const watchlistApi = {
  list: () => apiClient.get<WatchlistItem[]>("/watchlist/"),

  add: (data: { stock_code: string; memo?: string }) =>
    apiClient.post<WatchlistItem>("/watchlist/", data),

  remove: (stockCode: string) =>
    apiClient.delete(`/watchlist/${stockCode}/`),
};
