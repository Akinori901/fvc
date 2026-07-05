import { useQuery } from "@tanstack/react-query";
import { stocksApi } from "@/api/stocks";
import type { TechnicalPeriod } from "@/types/technical";

export function useStocks() {
  return useQuery({
    queryKey: ["stocks"],
    queryFn: () => stocksApi.list().then((r) => r.data),
  });
}

export function useStock(code: string) {
  return useQuery({
    queryKey: ["stocks", code],
    queryFn: () => stocksApi.get(code).then((r) => r.data),
    enabled: !!code,
  });
}

export function useStockFinancials(code: string) {
  return useQuery({
    queryKey: ["stocks", code, "financials"],
    queryFn: () => stocksApi.getFinancials(code).then((r) => r.data),
    enabled: !!code,
  });
}

export function useStockPrices(code: string, limit?: number) {
  return useQuery({
    queryKey: ["stocks", code, "prices", limit],
    queryFn: () => stocksApi.getPrices(code, limit).then((r) => r.data),
    enabled: !!code,
  });
}

export function useStockTechnicals(code: string, period: TechnicalPeriod = "1y") {
  return useQuery({
    queryKey: ["stocks", code, "technical", period],
    queryFn: () => stocksApi.getTechnical(code, period).then((r) => r.data),
    enabled: !!code,
    staleTime: 5 * 60 * 1000,
  });
}
