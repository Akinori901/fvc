import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { settingsApi } from "@/api/settings";

export function useApiConfigs() {
  return useQuery({
    queryKey: ["apiConfigs"],
    queryFn: () => settingsApi.getApiConfigs().then((r) => r.data),
  });
}

export function useUpdateApiConfig() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      provider,
      data,
    }: {
      provider: string;
      data: { api_key?: string; plan?: string; is_enabled?: boolean };
    }) => settingsApi.updateApiConfig(provider, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["apiConfigs"] });
    },
  });
}
