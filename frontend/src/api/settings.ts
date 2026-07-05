import apiClient from "./client";
import type { ApiConfigInfo } from "@/types/settings";

export const settingsApi = {
  getApiConfigs: () =>
    apiClient.get<ApiConfigInfo[]>("/settings/api-configs/"),

  updateApiConfig: (
    provider: string,
    data: { api_key?: string; plan?: string; is_enabled?: boolean }
  ) => apiClient.put<ApiConfigInfo>(`/settings/api-configs/${provider}/`, data),
};
