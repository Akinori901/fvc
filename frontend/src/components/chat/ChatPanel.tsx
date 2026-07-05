import { useEffect, useRef, useState } from "react";
import {
  Box,
  TextField,
  IconButton,
  Typography,
  Alert,
  CircularProgress,
  Chip,
  Tooltip,
  Switch,
  FormControlLabel,
} from "@mui/material";
import SendIcon from "@mui/icons-material/Send";
import RestartAltIcon from "@mui/icons-material/RestartAlt";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import { chatApi, type ChatMessage } from "@/api/chat";
import { useAuthStore } from "@/stores/authStore";
import ChatMessageBubble from "./ChatMessageBubble";

interface ChatPanelProps {
  /** 全画面表示か（true）、フローティングウィジェットか（false） */
  fullscreen?: boolean;
}

/**
 * チャットの主要 UI。メッセージ一覧 + 入力フォーム + 残量表示 + 管理者トグル。
 *
 * 親コンポーネント（ChatPage / ChatWidget）は BYOK 未設定時の Gate 表示を担当し、
 * 設定済みの場合のみ本コンポーネントを描画する。
 */
export default function ChatPanel({ fullscreen = false }: ChatPanelProps) {
  const queryClient = useQueryClient();
  const user = useAuthStore((s) => s.user);
  const isSuperuser = Boolean(user?.is_superuser);

  const [sessionId, setSessionId] = useState<number | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [useAdminKey, setUseAdminKey] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [setupRequired, setSetupRequired] = useState(false);
  const scrollRef = useRef<HTMLDivElement | null>(null);

  // ステータス（残量・provider）
  const statusQuery = useQuery({
    queryKey: ["chatStatus"],
    queryFn: () => chatApi.getStatus().then((r) => r.data),
    refetchInterval: 60_000,
  });

  // メッセージ送信
  const sendMutation = useMutation({
    mutationFn: chatApi.sendMessage,
    onSuccess: async (resp) => {
      setSessionId(resp.data.session_id);
      // セッションのメッセージ列を再取得（ツール呼び出しも含むため）
      const fresh = await chatApi.listMessages(resp.data.session_id);
      setMessages(fresh.data);
      setInput("");
      setErrorMessage(null);
      queryClient.invalidateQueries({ queryKey: ["chatStatus"] });
    },
    onError: (err: unknown) => {
      if (axios.isAxiosError(err)) {
        const status = err.response?.status;
        const detail = (err.response?.data as { detail?: string } | undefined)?.detail;
        if (status === 402) {
          setSetupRequired(true);
          setErrorMessage(detail ?? "AI設定が登録されていません。設定画面で API キーを登録してください。");
        } else if (status === 429) {
          setErrorMessage(detail ?? "本日の上限に達しました。明日のJST 0時にリセットされます。");
        } else if (status === 400) {
          setErrorMessage(detail ?? "APIキーが無効です。設定画面で再登録してください。");
        } else if (status === 503) {
          setErrorMessage(detail ?? "AIサービスが一時的に利用できません。少し時間をおいてからお試しください。");
        } else {
          setErrorMessage(detail ?? "送信に失敗しました。");
        }
      } else {
        setErrorMessage("送信に失敗しました。");
      }
    },
  });

  // メッセージ追加後にスクロール
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, sendMutation.isPending]);

  const handleSend = () => {
    const trimmed = input.trim();
    if (!trimmed || sendMutation.isPending) return;
    setErrorMessage(null);
    setSetupRequired(false);
    sendMutation.mutate({
      user_message: trimmed,
      session_id: sessionId,
      use_admin_key: useAdminKey,
    });
  };

  const handleReset = () => {
    setSessionId(null);
    setMessages([]);
    setInput("");
    setErrorMessage(null);
  };

  const status = statusQuery.data;
  const remaining = status?.daily_remaining ?? null;
  const remainingColor = remaining === null
    ? "default"
    : remaining > 50
      ? "success"
      : remaining > 10
        ? "warning"
        : "error";

  return (
    <Box sx={{ display: "flex", flexDirection: "column", height: "100%" }}>
      {/* ヘッダ: provider / 残量 / リセット / 管理者トグル */}
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          gap: 1,
          px: 2,
          py: 1,
          borderBottom: "1px solid",
          borderColor: "divider",
          flexWrap: "wrap",
        }}
      >
        {status && (
          <>
            <Chip
              size="small"
              label={`${status.provider || "?"}: ${status.model || "?"}`}
              variant="outlined"
            />
            <Chip
              size="small"
              label={`今日あと ${remaining ?? "?"} / ${status.daily_limit} 回`}
              color={remainingColor as "default" | "success" | "warning" | "error"}
            />
          </>
        )}
        <Box sx={{ flexGrow: 1 }} />
        {isSuperuser && (
          <Tooltip title="管理者の OpenAI キーで応答する（テスト・デモ用途）">
            <FormControlLabel
              control={
                <Switch
                  size="small"
                  checked={useAdminKey}
                  onChange={(e) => setUseAdminKey(e.target.checked)}
                />
              }
              label="管理者キー"
              slotProps={{ typography: { variant: "caption" } }}
              sx={{ mr: 0 }}
            />
          </Tooltip>
        )}
        <Tooltip title="会話をリセット">
          <span>
            <IconButton size="small" onClick={handleReset} disabled={messages.length === 0}>
              <RestartAltIcon fontSize="small" />
            </IconButton>
          </span>
        </Tooltip>
      </Box>

      {/* メッセージリスト */}
      <Box
        ref={scrollRef}
        sx={{
          flexGrow: 1,
          overflowY: "auto",
          px: 2,
          py: 1.5,
          bgcolor: "background.default",
          minHeight: fullscreen ? "auto" : 320,
        }}
      >
        {messages.length === 0 && !sendMutation.isPending && (
          <Box sx={{ textAlign: "center", color: "text.secondary", mt: 4 }}>
            <Typography variant="body2">
              質問例: 「7203 の状況は？」「今買える割安株は？」「USD/JPY のフェアバリューは？」
            </Typography>
          </Box>
        )}
        {messages.map((m) => (
          <ChatMessageBubble key={m.id} message={m} />
        ))}
        {sendMutation.isPending && (
          <Box sx={{ display: "flex", alignItems: "center", gap: 1, color: "text.secondary", mt: 1 }}>
            <CircularProgress size={16} />
            <Typography variant="body2">考え中...</Typography>
          </Box>
        )}
      </Box>

      {/* エラー表示 */}
      {errorMessage && (
        <Alert
          severity={setupRequired ? "info" : "error"}
          sx={{ mx: 2, mb: 1, mt: 1 }}
          onClose={() => setErrorMessage(null)}
        >
          {errorMessage}
        </Alert>
      )}

      {/* 入力フォーム */}
      <Box
        sx={{
          display: "flex",
          gap: 1,
          p: 2,
          borderTop: "1px solid",
          borderColor: "divider",
          alignItems: "flex-end",
        }}
      >
        <TextField
          fullWidth
          multiline
          maxRows={4}
          size="small"
          placeholder="株について質問する..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
              e.preventDefault();
              handleSend();
            }
          }}
          disabled={sendMutation.isPending}
        />
        <Tooltip title="送信 (Cmd/Ctrl + Enter)">
          <span>
            <IconButton
              color="primary"
              onClick={handleSend}
              disabled={!input.trim() || sendMutation.isPending}
              sx={{ alignSelf: "flex-end", mb: 0.5 }}
            >
              <SendIcon />
            </IconButton>
          </span>
        </Tooltip>
      </Box>
    </Box>
  );
}
