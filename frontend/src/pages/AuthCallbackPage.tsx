/**
 * Cognito Hosted UI からのリダイレクト戻り先。
 *
 * Amplify が裏で `?code=xxx` を access/id/refresh token に交換し、
 * 完了すると `Hub` 経由で `signedIn` event が発火する。
 * auth-hub-listener がこれを受けて authStore に Django User をセットする。
 *
 * 本コンポーネントは authStore.isAuthenticated を観測し、true になったら
 * ダッシュボードへ遷移する。タイムアウト時はエラー表示してログイン画面へ戻す。
 *
 * 設計書: docs/design/cognito-oauth-migration.md §8.3
 */
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Alert, Box, CircularProgress, Typography } from "@mui/material";

import { ROUTES } from "@/router/routes";
import { useAuthStore } from "@/stores/authStore";

const CALLBACK_TIMEOUT_MS = 15_000;

export default function AuthCallbackPage() {
  const navigate = useNavigate();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isAuthenticated) {
      navigate(ROUTES.DASHBOARD, { replace: true });
      return;
    }

    const timer = window.setTimeout(() => {
      setError(
        "ログインに時間がかかっています。しばらく待っても変わらない場合は、ログイン画面に戻ってやり直してください。",
      );
    }, CALLBACK_TIMEOUT_MS);

    return () => window.clearTimeout(timer);
  }, [isAuthenticated, navigate]);

  return (
    <Box
      sx={{
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: 2,
        bgcolor: "background.default",
      }}
    >
      {error ? (
        <>
          <Alert severity="error" sx={{ maxWidth: 480 }}>
            {error}
          </Alert>
          <Typography variant="body2">
            <a href={ROUTES.LOGIN}>ログイン画面に戻る</a>
          </Typography>
        </>
      ) : (
        <>
          <CircularProgress />
          <Typography variant="body2" color="text.secondary">
            ログイン処理中...
          </Typography>
        </>
      )}
    </Box>
  );
}
