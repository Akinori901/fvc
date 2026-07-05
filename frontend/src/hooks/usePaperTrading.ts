import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { paperTradingApi } from "@/api/paperTrading";
import type { ExecuteTradeRequest } from "@/types/paperTrading";

const KEYS = {
  positions: ["paperTradingPositions"] as const,
  position: (code: string) => ["paperTradingPosition", code] as const,
  trades: (code?: string) => ["paperTradingTrades", code] as const,
};

export function usePaperPositions() {
  return useQuery({
    queryKey: KEYS.positions,
    queryFn: () => paperTradingApi.listPositions().then((r) => r.data),
  });
}

export function usePaperPosition(code: string) {
  return useQuery({
    queryKey: KEYS.position(code),
    queryFn: () => paperTradingApi.getPosition(code).then((r) => r.data),
    enabled: !!code,
  });
}

export function usePaperTradeHistory(stockCode?: string) {
  return useQuery({
    queryKey: KEYS.trades(stockCode),
    queryFn: () =>
      paperTradingApi.getTradeHistory(stockCode).then((r) => r.data),
  });
}

export function useExecuteTrade() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: ExecuteTradeRequest) =>
      paperTradingApi.executeTrade(data).then((r) => r.data),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: KEYS.positions });
      queryClient.invalidateQueries({
        queryKey: KEYS.position(variables.stock_code),
      });
      queryClient.invalidateQueries({ queryKey: KEYS.trades() });
      queryClient.invalidateQueries({
        queryKey: KEYS.trades(variables.stock_code),
      });
    },
  });
}

export function useResetPaperTrading() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => paperTradingApi.reset().then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: KEYS.positions });
      queryClient.invalidateQueries({ queryKey: ["paperTradingPosition"] });
      queryClient.invalidateQueries({ queryKey: ["paperTradingTrades"] });
    },
  });
}
