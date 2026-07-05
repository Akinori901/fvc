/**
 * Admin 管理 API 型定義。
 *
 * バックエンド `apps/auth_cognito/presentation/serializers/admin_serializers.py`
 * のレスポンス構造に対応する。
 */

export interface CognitoLinkInfo {
  id: number;
  cognito_sub: string;
  provider: string;
  cognito_email: string;
  last_signed_in_at: string | null;
}

export interface UserAllowedEmailInfo {
  id: number;
  email: string;
  label: string;
}

export interface AdminUserRow {
  id: number;
  email: string;
  username: string;
  is_superuser: boolean;
  is_staff: boolean;
  is_active: boolean;
  date_joined: string;
  last_login: string | null;
  cognito_links: CognitoLinkInfo[];
  allowed_emails: UserAllowedEmailInfo[];
  // 新規作成レスポンスでのみ意味を持つ。Cognito 招待メール送信の成否。
  // 一覧 GET では常に true。
  invite_email_sent: boolean;
}

export interface CognitoUserRow {
  username: string;
  email: string;
  status: string;
  enabled: boolean;
  user_create_date: string | null;
  user_last_modified_date: string | null;
  identity_provider: string;
  linked_user_id: number | null;
}

export interface AdminUserListResponse {
  users: AdminUserRow[];
}

export interface CognitoUserListResponse {
  users: CognitoUserRow[];
}
