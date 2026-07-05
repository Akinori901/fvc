import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { syncApi } from "@/api/sync";
import type { SyncTriggerRequest } from "@/api/sync";

export function useSyncLogs(limit?: number) {
  return useQuery({
    queryKey: ["syncLogs", limit],
    queryFn: () => syncApi.logs(limit).then((r) => r.data),
  });
}

export function useSyncTrigger() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: SyncTriggerRequest) => syncApi.trigger(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["syncLogs"] });
      queryClient.invalidateQueries({ queryKey: ["stocks"] });
      queryClient.invalidateQueries({ queryKey: ["screening"] });
      queryClient.invalidateQueries({ queryKey: ["etf-list"] });
      queryClient.invalidateQueries({ queryKey: ["reit-list"] });
      queryClient.invalidateQueries({ queryKey: ["stockFinancials"] });
      queryClient.invalidateQueries({ queryKey: ["stockPrices"] });
    },
  });
}
