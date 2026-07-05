import { useQuery } from "@tanstack/react-query";
import { etfApi } from "@/api/etf";

export function useEtfList(market_type = "JP") {
  return useQuery({
    queryKey: ["etf-list", market_type],
    queryFn: () => etfApi.list(market_type).then((r) => r.data),
  });
}
