import apiClient from "./client";

export interface ChatStatus {
  has_config: boolean;
  is_enabled: boolean;
  provider: string;
  model: string;
  daily_used: number;
  daily_limit: number;
  daily_remaining: number;
}

export interface ChatSession {
  id: number;
  provider: string;
  title: string;
  started_at: string | null;
  last_message_at: string | null;
}

export interface ChatMessage {
  id: number;
  role: "user" | "assistant" | "tool";
  content: string;
  tool_name: string;
  tool_args: Record<string, unknown>;
  tool_result: Record<string, unknown>;
  prompt_tokens: number;
  completion_tokens: number;
  model_used: string;
  provider: string;
  created_at: string | null;
}

export interface ToolCallSummary {
  tool_name: string;
  arguments: Record<string, unknown>;
  succeeded: boolean;
}

export interface SendMessageResponse {
  session_id: number;
  assistant_message: string;
  provider: string;
  model: string;
  prompt_tokens: number;
  completion_tokens: number;
  iterations: number;
  truncated: boolean;
  tool_calls: ToolCallSummary[];
}

export interface SendMessageRequest {
  user_message: string;
  session_id?: number | null;
  use_admin_key?: boolean;
}

export const chatApi = {
  /** BYOK 状態 + 当日使用量 */
  getStatus: () => apiClient.get<ChatStatus>("/chat/status/"),

  /** セッション一覧（last_message_at 降順） */
  listSessions: () => apiClient.get<ChatSession[]>("/chat/sessions/"),

  /** セッション内メッセージ一覧 */
  listMessages: (sessionId: number) =>
    apiClient.get<ChatMessage[]>(`/chat/sessions/${sessionId}/messages/`),

  /** メッセージ送信（Function Calling 内包） */
  sendMessage: (data: SendMessageRequest) =>
    apiClient.post<SendMessageResponse>("/chat/messages/", data),

  /** セッション削除 */
  deleteSession: (sessionId: number) =>
    apiClient.delete<void>(`/chat/sessions/${sessionId}/`),
};
