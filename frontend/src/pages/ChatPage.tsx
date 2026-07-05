import { Box, CircularProgress, Paper } from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { chatApi } from "@/api/chat";
import ChatPanel from "@/components/chat/ChatPanel";
import ByokSetupGate from "@/components/chat/ByokSetupGate";

/**
 * AIチャット全画面ページ。
 *
 * BYOK 未設定なら ByokSetupGate を表示、設定済みなら ChatPanel を表示。
 */
export default function ChatPage() {
  const { data: status, isLoading } = useQuery({
    queryKey: ["chatStatus"],
    queryFn: () => chatApi.getStatus().then((r) => r.data),
  });

  if (isLoading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", mt: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (!status?.is_enabled) {
    return <ByokSetupGate />;
  }

  return (
    <Paper
      elevation={0}
      sx={{
        height: "calc(100vh - 140px)",
        display: "flex",
        flexDirection: "column",
        border: "1px solid",
        borderColor: "divider",
      }}
    >
      <ChatPanel fullscreen />
    </Paper>
  );
}
