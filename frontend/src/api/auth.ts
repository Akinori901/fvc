import apiClient from "./client";

interface DjangoUser {
  pk: number;
  username: string;
  email: string;
  is_superuser: boolean;
}

/**
 * 認証関連の Django API クライアント。
 *
 * Phase D で Cognito (Amplify) に一本化されたため、login / register /
 * refresh / logout / updateEmail / changePassword は撤去済み。
 * 認証フローは Amplify SDK が直接 Cognito と通信する (`amplify-account.ts`)。
 *
 * 残るのは `getUser` のみで、Django User 情報 (pk / username / email /
 * is_superuser) を返す `/api/auth/user/` を叩く。バックエンドの
 * `apps.core.views.UserDetailsView` が応答する。
 */
export const authApi = {
  getUser: () => apiClient.get<DjangoUser>("/auth/user/"),
};
