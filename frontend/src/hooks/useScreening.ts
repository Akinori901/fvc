import { useQuery } from "@tanstack/react-query";
import { screeningApi, type ScreeningParams } from "@/api/screening";

export function useScreening(params: ScreeningParams) {
  return useQuery({
    queryKey: ["screening", params],
    queryFn: () => screeningApi.search(params).then((r) => r.data),
    enabled: true,
    staleTime: 5 * 60 * 1000,
    gcTime: 30 * 60 * 1000,
  });
}
