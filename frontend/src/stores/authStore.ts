/**
 * 認証状態の zustand ストア。
 *
 * 認証は Cognito (Amplify) 経由に一本化されており、token は Amplify が
 * IndexedDB に管理するため zustand には積まない。本ストアでは Django User
 * 情報 (pk / username / email / is_superuser) と認証フラグだけを保持する。
 *
 * 更新フロー:
 * - ログイン: `auth-hub-listener.ts` が `signedIn` event を受けて
 *   `/api/auth/user/` を叩き `setAuthenticatedUser` を呼ぶ。
 *   `ProtectedRoute` の初回マウントでも `getCurrentUser()` 成功後に
 *   同じ API を叩いて補完する (リロード後の復元用)。
 * - ログアウト: `signedOut` event で `logout()` が呼ばれる。
 *
 * persist は user 情報のリロード時の即時表示用 (Cognito セッション復元の
 * 待ち時間で UI が空にならないため)。実際の認証可否は ProtectedRoute が
 * Amplify の `getCurrentUser()` で都度判定する。
 */
import { create } from "zustand";
import { persist } from "zustand/middleware";

interface User {
  pk: number;
  username: string;
  email: string;
  is_superuser: boolean;
}

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  setUser: (user: User) => void;
  /**
   * Cognito ログイン成功時に呼ぶ。user を埋めて isAuthenticated を立てる。
   */
  setAuthenticatedUser: (user: User) => void;
  /**
   * Cognito の `signedOut` Hub event から呼ばれる。ユーザー状態をクリアする。
   */
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      isAuthenticated: false,
      setUser: (user) => set({ user }),
      setAuthenticatedUser: (user) => set({ user, isAuthenticated: true }),
      logout: () => set({ user: null, isAuthenticated: false }),
    }),
    {
      name: "fvc-auth",
    },
  ),
);
