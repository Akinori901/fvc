/**
 * 認証必須ルートのガード。
 *
 * Amplify の `getCurrentUser()` が成功すれば認証済み、失敗すれば `/login` へ
 * リダイレクトする。初回マウント時はチェックが完了するまで CircularProgress
 * を表示する。
 *
 * 認証成功時には `/api/auth/user/` で Django User を取得し authStore に反映
 * する (Hub.signedIn は新規ログイン時しか発火しないため、リロード後は
 * ここで明示的に呼ぶ)。
 *
 * 設計書: docs/design/cognito-oauth-migration.md §8.4
 */
import { useEffect, useState } from "react";
import { Navigate, Outlet } from "react-router-dom";
import { Box, CircularProgress } from "@mui/material";
import { getCurrentUser } from "aws-amplify/auth";

import { authApi } from "@/api/auth";
import { useAuthStore } from "@/stores/authStore";

export default function ProtectedRoute() {
  const setAuthenticatedUser = useAuthStore((s) => s.setAuthenticatedUser);

  const [isChecking, setIsChecking] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getCurrentUser()
      .then(() => {
        if (cancelled) return;
        setIsAuthenticated(true);
        // /api/auth/user/ で Django User を取得して authStore に反映
        authApi
          .getUser()
          .then((res) => {
            if (!cancelled) setAuthenticatedUser(res.data);
          })
          .catch(() => {
            // 失敗してもログイン状態は維持 (個別画面で再試行できるため)
          });
      })
      .catch(() => {
        // 未ログイン
      })
      .finally(() => {
        if (!cancelled) setIsChecking(false);
      });
    return () => {
      cancelled = true;
    };
  }, [setAuthenticatedUser]);

  if (isChecking) {
    return (
      <Box
        sx={{
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <CircularProgress />
      </Box>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}
