import { useState } from "react";
import { Box, IconButton, Paper, Typography, Tooltip } from "@mui/material";
import ChatIcon from "@mui/icons-material/Chat";
import CloseIcon from "@mui/icons-material/Close";
import OpenInFullIcon from "@mui/icons-material/OpenInFull";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useAuthStore } from "@/stores/authStore";
import { chatApi } from "@/api/chat";
import { ROUTES } from "@/router/routes";
import ChatPanel from "./ChatPanel";
import ByokSetupGate from "./ByokSetupGate";

/**
 * 右下フローティングウィジェット。
 *
 * 未ログイン時は表示しない。BYOK 未設定なら開いた時にゲート案内、
 * 設定済みなら ChatPanel を表示。「全画面で開く」ボタンで /chat に遷移。
 */
export default function ChatWidget() {
  const [open, setOpen] = useState(false);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const navigate = useNavigate();

  const { data: status } = useQuery({
    queryKey: ["chatStatus"],
    queryFn: () => chatApi.getStatus().then((r) => r.data),
    // 開いた時のみフェッチでも良いが、残量バッジ用に常時取得
    enabled: isAuthenticated,
  });

  if (!isAuthenticated) {
    return null;
  }

  if (!open) {
    return (
      <Tooltip title="AIチャットを開く">
        <Box
          sx={{
            position: "fixed",
            bottom: 24,
            right: 24,
            zIndex: 1200,
          }}
        >
          <IconButton
            color="primary"
            onClick={() => setOpen(true)}
            sx={{
              bgcolor: "primary.main",
              color: "primary.contrastText",
              width: 56,
              height: 56,
              boxShadow: 3,
              "&:hover": { bgcolor: "primary.dark" },
            }}
          >
            <ChatIcon />
          </IconButton>
        </Box>
      </Tooltip>
    );
  }

  const isReady = status?.is_enabled === true;

  return (
    <Paper
      elevation={6}
      sx={{
        position: "fixed",
        bottom: 24,
        right: 24,
        width: { xs: "calc(100vw - 32px)", sm: 380 },
        height: { xs: "70vh", sm: 540 },
        zIndex: 1200,
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
      }}
    >
      {/* ヘッダ */}
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          px: 1.5,
          py: 1,
          bgcolor: "primary.main",
          color: "primary.contrastText",
        }}
      >
        <Typography variant="subtitle2" sx={{ flexGrow: 1 }}>
          AIチャット
        </Typography>
        <Tooltip title="全画面で開く">
          <IconButton
            size="small"
            onClick={() => {
              setOpen(false);
              navigate(ROUTES.CHAT);
            }}
            sx={{ color: "inherit" }}
          >
            <OpenInFullIcon fontSize="small" />
          </IconButton>
        </Tooltip>
        <IconButton size="small" onClick={() => setOpen(false)} sx={{ color: "inherit" }}>
          <CloseIcon fontSize="small" />
        </IconButton>
      </Box>

      {/* 本体 */}
      <Box sx={{ flexGrow: 1, overflow: "hidden", display: "flex", flexDirection: "column" }}>
        {isReady ? <ChatPanel /> : <ByokSetupGate />}
      </Box>
    </Paper>
  );
}
