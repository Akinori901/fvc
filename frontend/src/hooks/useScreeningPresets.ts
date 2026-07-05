import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { screeningPresetApi } from "@/api/screeningPreset";
import type { ScreeningFilters } from "@/types/screeningPreset";

export function useScreeningPresets() {
  return useQuery({
    queryKey: ["screeningPresets"],
    queryFn: () => screeningPresetApi.list().then((r) => r.data),
  });
}

export function useSaveScreeningPreset() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: { name: string; priority: number; filters: ScreeningFilters; id?: number }) =>
      data.id
        ? screeningPresetApi.update(data.id, { name: data.name, priority: data.priority, filters: data.filters })
        : screeningPresetApi.create({ name: data.name, priority: data.priority, filters: data.filters }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["screeningPresets"] }),
  });
}

export function useDeleteScreeningPreset() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => screeningPresetApi.delete(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["screeningPresets"] }),
  });
}
