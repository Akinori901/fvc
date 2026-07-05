import { useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Stack,
  Typography,
} from "@mui/material";
import { signInWithRedirect, signOut } from "aws-amplify/auth";

export default function LoginPage() {
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleLogin = async (provider: "COGNITO" | "Google") => {
    setError("");
    setLoading(true);
    try {
      // Amplify は前回のログインセッションを IndexedDB / Local Storage に
      // 残すため、既にログイン中の状態で signInWithRedirect を呼ぶと
      // UserAlreadyAuthenticatedException が発生する。事前に signOut して
      // 確実にクリーンな状態から開始する (global: false でローカルセッション
      // だけクリア、Hosted UI へのリダイレクトは発生しない)。
      try {
        await signOut({ global: false });
      } catch {
        // 未ログイン時等の例外は無視
      }

      await signInWithRedirect(
        provider === "Google" ? { provider: "Google" } : undefined,
      );
      // 成功時は Hosted UI へリダイレクトされるため以降のコードは実行されない
    } catch (err) {
      console.error("[LoginPage] signInWithRedirect failed:", err);
      setError("ログインの開始に失敗しました。時間をおいて再度お試しください。");
      setLoading(false);
    }
  };

  return (
    <Box
      sx={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        bgcolor: "background.default",
      }}
    >
      <Card sx={{ maxWidth: 400, width: "100%", mx: 2 }}>
        <CardContent sx={{ p: 4 }}>
          <Typography variant="h5" align="center" gutterBottom>
            Fair Value Calculator
          </Typography>
          <Typography
            variant="body2"
            align="center"
            color="text.secondary"
            sx={{ mb: 3 }}
          >
            ログイン
          </Typography>

          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}

          <Stack spacing={1.5}>
            <Button
              variant="contained"
              fullWidth
              size="large"
              onClick={() => handleLogin("COGNITO")}
              disabled={loading}
            >
              {loading ? "ログイン画面に移動中..." : "ログイン"}
            </Button>
            <Button
              variant="outlined"
              fullWidth
              size="large"
              onClick={() => handleLogin("Google")}
              disabled={loading}
            >
              Google でログイン
            </Button>
          </Stack>
        </CardContent>
      </Card>
    </Box>
  );
}
