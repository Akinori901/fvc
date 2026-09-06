import { Alert, Box, Divider, Typography } from "@mui/material";
import { useAuthStore } from "@/stores/authStore";
import CreateAdminUserForm from "@/components/admin/CreateAdminUserForm";
import AdminUsersTable from "@/components/admin/AdminUsersTable";

/**
 * 管理者専用: auth_user / 許可 email / Cognito link の一覧。
 *
 * router (`/admin/users`) + Sidebar 両方で `is_superuser` ガード済みだが、
 * 直接 URL アクセスへの防御として本ページ内でも guard する。
 *
 * Cognito User Pool 実体 (ユーザー無効化/削除/招待メール送信など) の管理は
 * 認証コンソール側の役割であり、本画面では扱わない。
 */
export default function AdminUsersPage() {
  const user = useAuthStore((s) => s.user);
  if (!user?.is_superuser) {
    return (
      <Box>
        <Alert severity="error">このページにアクセスする権限がありません</Alert>
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        ユーザー管理
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        auth_user の作成、許可 email の追加/削除、Cognito link の削除を行います。
        招待制: <code>m_user_allowed_emails</code> に登録された email のみ Cognito 経由でログイン可能です。
      </Typography>

      <Alert severity="info" sx={{ mb: 3 }}>
        Cognito ユーザー(User Pool)自体の管理(無効化・削除・招待メール送信など)は認証コンソールで行います。
      </Alert>

      <CreateAdminUserForm />

      <Divider sx={{ my: 3 }} />

      <AdminUsersTable />
    </Box>
  );
}
