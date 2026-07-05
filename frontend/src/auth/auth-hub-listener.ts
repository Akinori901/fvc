/**
 * Amplify Auth の Hub event を購読して authStore を更新する listener。
 *
 * 初期化は副作用 import で行う (`main.tsx` から `import "./auth-hub-listener"`)。
 *
 * 購読する event:
 * - `signedIn`: Cognito Hosted UI から戻ってきた直後、または `signIn()` 成功時。
 *   `/api/auth/user/` を叩いて Django User を取得し authStore にセットする。
 *   apiClient (Step 4 以降) は fetchAuthSession() から token を取って付与するため、
 *   この時点で Amplify の token は既に有効。
 * - `signedOut`: `signOut()` 成功時。authStore をクリアする。
 * - `tokenRefresh_failure`: refresh token も期限切れ。authStore をクリアして
 *   /login へ誘導する。
 * - `signInWithRedirect_failure`: OAuth redirect で失敗。コンソールに記録する
 *   のみ (UI 側で別途エラー表示する)。
 *
 * 環境変数 VITE_COGNITO_USER_POOL_ID が未設定の環境では Hub listener を
 * 登録しない (Amplify.configure もスキップされているため event が発火しないが、
 * 念のため明示的にガードする)。
 */
import { Hub } from "aws-amplify/utils";

import apiClient from "@/api/client";
import { useAuthStore } from "@/stores/authStore";

const isCognitoConfigured = Boolean(
  import.meta.env.VITE_COGNITO_USER_POOL_ID &&
    import.meta.env.VITE_COGNITO_WEB_CLIENT_ID &&
    import.meta.env.VITE_COGNITO_DOMAIN_PREFIX,
);

interface DjangoUser {
  pk: number;
  username: string;
  email: string;
  is_superuser: boolean;
}

async function loadDjangoUserAndStore(): Promise<void> {
  try {
    // apiClient の request interceptor が Amplify session の id token を
    // Authorization ヘッダに付与する。バックエンドは Cognito JWT を verify して
    // JIT provisioning で auth_user.email とマッチングし Django User を解決する。
    const { data } = await apiClient.get<DjangoUser>("/auth/user/");
    useAuthStore.getState().setAuthenticatedUser(data);
  } catch (error) {
    console.error("[auth-hub] Failed to load Django user after sign-in:", error);
  }
}

if (isCognitoConfigured) {
  Hub.listen("auth", ({ payload }) => {
    switch (payload.event) {
      case "signedIn":
        void loadDjangoUserAndStore();
        break;
      case "signedOut":
        useAuthStore.getState().logout();
        break;
      case "tokenRefresh_failure":
        console.warn("[auth-hub] Token refresh failed. Forcing logout.");
        useAuthStore.getState().logout();
        if (typeof window !== "undefined") {
          window.location.href = "/login";
        }
        break;
      case "signInWithRedirect_failure":
        console.error(
          "[auth-hub] signInWithRedirect failure:",
          payload.data?.error,
        );
        break;
      default:
        // 他の event (tokenRefresh など) はログのみで握る
        break;
    }
  });
}
