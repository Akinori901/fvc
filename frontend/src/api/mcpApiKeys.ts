import apiClient from "./client";
import type {
  IssuedMcpApiKey,
  McpApiKeyListResponse,
} from "@/types/mcpApiKey";

export const mcpApiKeysApi = {
  list: () => apiClient.get<McpApiKeyListResponse>("/v1/mcp/keys/"),

  issue: (label: string) =>
    apiClient.post<IssuedMcpApiKey>("/v1/mcp/keys/", { label }),

  revoke: (keyId: number) => apiClient.delete(`/v1/mcp/keys/${keyId}/`),
};
