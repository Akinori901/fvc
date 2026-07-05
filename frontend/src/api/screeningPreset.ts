import apiClient from "./client";
import type { ScreeningFilters, ScreeningPreset } from "@/types/screeningPreset";

export const screeningPresetApi = {
  list: () => apiClient.get<ScreeningPreset[]>("/stocks/screening/presets/"),

  create: (data: { name: string; priority: number; filters: ScreeningFilters }) =>
    apiClient.post<ScreeningPreset>("/stocks/screening/presets/", data),

  update: (id: number, data: { name: string; priority: number; filters: ScreeningFilters }) =>
    apiClient.put<ScreeningPreset>(`/stocks/screening/presets/${id}/`, data),

  delete: (id: number) => apiClient.delete(`/stocks/screening/presets/${id}/`),
};
