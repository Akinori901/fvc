import { Box, Typography, Button, Stack, Alert } from "@mui/material";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import SettingsIcon from "@mui/icons-material/Settings";
import { Link } from "react-router-dom";
import { ROUTES } from "@/router/routes";

/**
 * BYOK 未設定ユーザー向けセットアップ案内。
 *
 * チャットを使うには Gemini か OpenAI の API キーが必要であることを説明し、
 * 設定画面への誘導と無料枠のある Gemini への外部リンクを提供する。
 */
export default function ByokSetupGate() {
  return (
    <Box sx={{ p: 3, maxWidth: 640, mx: "auto" }}>
      <Typography variant="h6" gutterBottom>
        AIチャットを利用するには
      </Typography>

      <Alert severity="info" sx={{ mb: 2 }}>
        本機能はあなたの AI API キーで動作します。Gemini は無料枠があるため、
        まずはこちらから始めるのがおすすめです。
      </Alert>

      <Stack spacing={1.5}>
        <Typography variant="body2" color="text.secondary">
          1. 無料枠のある Gemini API キーを取得（推奨）
        </Typography>
        <Button
          variant="outlined"
          endIcon={<OpenInNewIcon />}
          href="https://aistudio.google.com/app/apikey"
          target="_blank"
          rel="noopener noreferrer"
          fullWidth
        >
          Google AI Studio で Gemini APIキーを取得
        </Button>

        <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
          2. もしくは OpenAI を使う場合（有料）
        </Typography>
        <Button
          variant="outlined"
          endIcon={<OpenInNewIcon />}
          href="https://platform.openai.com/api-keys"
          target="_blank"
          rel="noopener noreferrer"
          fullWidth
        >
          OpenAI Platform で APIキーを取得
        </Button>

        <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
          3. 取得したキーを設定画面で登録
        </Typography>
        <Button
          component={Link}
          to={ROUTES.SETTINGS}
          variant="contained"
          startIcon={<SettingsIcon />}
          fullWidth
        >
          設定画面で AIキーを登録する
        </Button>
      </Stack>
    </Box>
  );
}
