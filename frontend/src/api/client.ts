/**
 * バックエンド API への axios クライアント。
 *
 * 認証は Cognito (Amplify) に一本化済み。`fetchAuthSession()` から id token を
 * 取得して Authorization ヘッダに付与する。
 *
 * **なぜ access token ではなく id token か**:
 * Cognito の access token には email / name claim が含まれない (デフォルト
 * 仕様)。バックエンドの JIT provisioning が `auth_user.email` とのマッチング
 * に email を必要とするため、email を含む id token を送る。バックエンドは
 * JWKS で署名検証 + iss / aud / token_use を全て検証しているのでセキュリティ
 * 的には access token 送信と実質同等。
 *
 * 401 ハンドリング:
 * - Amplify が token refresh まで自動でやるので、401 が出た時点で refresh も
 *   失敗している → `signOut()` してログイン画面に戻す
 *
 * 設計書: docs/design/cognito-oauth-migration.md §8.4
 */
import axios, { type InternalAxiosRequestConfig } from "axios";
import { fetchAuthSession, signOut } from "aws-amplify/auth";

const apiClient = axios.create({
  baseURL: "/api",
  headers: {
    "Content-Type": "application/json",
  },
});

async function getAuthToken(): Promise<string | null> {
  try {
    const session = await fetchAuthSession();
    const token = session.tokens?.idToken?.toString();
    return token ?? null;
  } catch {
    return null;
  }
}

// Request interceptor: Cognito id token を Authorization に付与
apiClient.interceptors.request.use(async (config: InternalAxiosRequestConfig) => {
  const token = await getAuthToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor: 401 → signOut() + /login
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status !== 401) {
      return Promise.reject(error);
    }

    // ログイン状態でなければそのまま reject (未認証で叩いた API の素直な 401)
    const token = await getAuthToken();
    if (!token) {
      return Promise.reject(error);
    }

    // Cognito session があるのに 401 = Amplify の自動 refresh も失敗
    // signOut して /login に戻す (Hub.signedOut event で authStore も
    // クリアされる)
    try {
      await signOut();
    } catch {
      // signOut 失敗時も login へリダイレクト
    }
    if (typeof window !== "undefined") {
      window.location.href = "/login";
    }
    return Promise.reject(error);
  },
);

export default apiClient;
