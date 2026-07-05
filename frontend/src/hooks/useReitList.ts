import { useQuery } from "@tanstack/react-query";
import { reitApi } from "@/api/reit";

export function useReitList(market_type = "JP") {
  return useQuery({
    queryKey: ["reit-list", market_type],
    queryFn: () => reitApi.list(market_type).then((r) => r.data),
  });
}
