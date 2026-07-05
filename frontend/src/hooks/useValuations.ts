import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { valuationsApi } from "@/api/valuations";
import type { CalculateRequest, ReverseCalculateRequest } from "@/types/valuation";

export function useValuations(limit?: number) {
  return useQuery({
    queryKey: ["valuations", limit],
    queryFn: () => valuationsApi.list(limit).then((r) => r.data),
  });
}

export function useValuation(id: number) {
  return useQuery({
    queryKey: ["valuations", id],
    queryFn: () => valuationsApi.get(id).then((r) => r.data),
    enabled: !!id,
  });
}

export function useStockValuations(code: string) {
  return useQuery({
    queryKey: ["stocks", code, "valuations"],
    queryFn: () => valuationsApi.listByStock(code).then((r) => r.data),
    enabled: !!code,
  });
}

export function useCalculateFairValue() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CalculateRequest) =>
      valuationsApi.calculate(data).then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["valuations"] });
    },
  });
}

export function useReverseCalculate() {
  return useMutation({
    mutationFn: (data: ReverseCalculateRequest) =>
      valuationsApi.reverseCalculate(data).then((r) => r.data),
  });
}
