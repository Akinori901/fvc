import { useQuery } from "@tanstack/react-query";
import { recommendationsApi } from "@/api/recommendations";

export function useRecommendations() {
  return useQuery({
    queryKey: ["recommendations"],
    queryFn: () => recommendationsApi.list().then((r) => r.data),
    // 計算が重いのでキャッシュを長めに（1時間）
    staleTime: 60 * 60 * 1000,
    gcTime: 2 * 60 * 60 * 1000,
  });
}
