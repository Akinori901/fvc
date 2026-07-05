import apiClient from "./client";
import type {
  ExecuteTradeRequest,
  PaperPosition,
  PaperPositionList,
  PaperTrade,
  ResetResult,
  TradeResult,
} from "@/types/paperTrading";

export const paperTradingApi = {
  listPositions: () =>
    apiClient.get<PaperPositionList>("/paper-trading/positions/"),

  getPosition: (code: string) =>
    apiClient.get<PaperPosition | null>(`/paper-trading/positions/${code}/`),

  executeTrade: (data: ExecuteTradeRequest) =>
    apiClient.post<TradeResult>("/paper-trading/trades/", data),

  getTradeHistory: (stockCode?: string) =>
    apiClient.get<PaperTrade[]>("/paper-trading/trades/", {
      params: stockCode ? { stock_code: stockCode } : undefined,
    }),

  reset: () => apiClient.delete<ResetResult>("/paper-trading/reset/"),
};
