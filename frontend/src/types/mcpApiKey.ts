export interface McpApiKeySummary {
  id: number;
  label: string;
  key_prefix: string;
  is_active: boolean;
  last_used_at: string | null;
  created_at: string;
}

export interface McpApiKeyListResponse {
  count: number;
  items: McpApiKeySummary[];
}

export interface IssuedMcpApiKey {
  id: number;
  label: string;
  key_prefix: string;
  plain_key: string;
  created_at: string;
}
