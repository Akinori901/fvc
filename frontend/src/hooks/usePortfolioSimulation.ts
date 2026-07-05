import { useQuery } from "@tanstack/react-query";

import { familyPortfolioApi } from "@/api/familyPortfolio";
import type { SimulationResponse } from "@/types/familyPortfolio";

export function usePortfolioSimulation(
  years: number,
  view: string,
  fundGrowthRate: number,
  enabled: boolean,
) {
  return useQuery<SimulationResponse>({
    queryKey: ["portfolio-simulation", years, view, fundGrowthRate],
    queryFn: () =>
      familyPortfolioApi
        .simulation({ years, view, fund_growth_rate: fundGrowthRate })
        .then((r) => r.data),
    enabled,
  });
}
