import { Alert, Box, Divider, Typography } from "@mui/material";
import { useAuthStore } from "@/stores/authStore";
import CreateAdminUserForm from "@/components/admin/CreateAdminUserForm";
import AdminUsersTable from "@/components/admin/AdminUsersTable";
import CognitoUserPoolTable from "@/components/admin/CognitoUserPoolTable";

/**
 * 管理者専用: auth_user / 許可 email / Cognito link / Cognito User Pool 一覧。
 *
 * router (`/admin/users`) + Sidebar 両方で `is_superuser` ガード済みだが、
 * 直接 URL アクセスへの防御として本ページ内でも guard する。
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

      <CreateAdminUserForm />

      <Divider sx={{ my: 3 }} />

      <AdminUsersTable />

      <Divider sx={{ my: 3 }} />

      <CognitoUserPoolTable />
    </Box>
  );
}
