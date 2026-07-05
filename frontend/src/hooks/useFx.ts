import { useQuery } from "@tanstack/react-query";
import { fxApi } from "@/api/fx";

export function useFxAnalysis() {
  return useQuery({
    queryKey: ["fx-analysis"],
    queryFn: () => fxApi.getAnalysis().then((r) => r.data),
    staleTime: 5 * 60 * 1000, // 5分
  });
}
