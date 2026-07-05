import { useState } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { adminApi } from "@/api/admin";

export default function CognitoUserPoolTable() {
  const queryClient = useQueryClient();
  const { data, isLoading, isError } = useQuery({
    queryKey: ["adminCognitoUsers"],
    queryFn: () => adminApi.listCognitoUsers().then((r) => r.data),
  });

  const [deleteTarget, setDeleteTarget] = useState<{ username: string; email: string } | null>(null);

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["adminCognitoUsers"] });
    // 紐付きが変わるので auth_user 一覧も再取得
    queryClient.invalidateQueries({ queryKey: ["adminUsers"] });
  };

  const disableMutation = useMutation({
    mutationFn: (username: string) => adminApi.disableCognitoUser(username),
    onSuccess: invalidate,
  });

  const enableMutation = useMutation({
    mutationFn: (username: string) => adminApi.enableCognitoUser(username),
    onSuccess: invalidate,
  });

  const deleteMutation = useMutation({
    mutationFn: (username: string) => adminApi.deleteCognitoUser(username),
    onSuccess: () => {
      setDeleteTarget(null);
      invalidate();
    },
  });

  if (isLoading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", p: 2 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (isError) {
    return <Alert severity="error">Cognito User Pool の取得に失敗しました</Alert>;
  }

  const users = data?.users ?? [];

  return (
    <Box>
      <Typography variant="subtitle1" gutterBottom>
        Cognito User Pool 一覧
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
        AWS Cognito 側のユーザー一覧。Disable/Enable はログイン可否を即座に切替、削除は完全削除 + m_cognito_links の同期削除を行う。
      </Typography>

      <TableContainer>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>username (sub)</TableCell>
              <TableCell>email</TableCell>
              <TableCell>status</TableCell>
              <TableCell>enabled</TableCell>
              <TableCell>identity_provider</TableCell>
              <TableCell>auth_user 紐付き</TableCell>
              <TableCell>作成日</TableCell>
              <TableCell align="right">操作</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {users.length === 0 ? (
              <TableRow>
                <TableCell colSpan={8} align="center">
                  <Typography variant="body2" color="text.secondary">
                    Cognito ユーザーが存在しません
                  </Typography>
                </TableCell>
              </TableRow>
            ) : (
              users.map((u) => (
                <TableRow key={u.username}>
                  <TableCell>
                    <code style={{ fontSize: "0.75rem" }}>
                      {u.username.slice(0, 16)}…
                    </code>
                  </TableCell>
                  <TableCell>{u.email || "-"}</TableCell>
                  <TableCell>
                    <Chip label={u.status} size="small" variant="outlined" />
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={u.enabled ? "有効" : "無効"}
                      size="small"
                      color={u.enabled ? "success" : "default"}
                    />
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={u.identity_provider}
                      size="small"
                      color={u.identity_provider === "Google" ? "warning" : "default"}
                    />
                  </TableCell>
                  <TableCell>
                    {u.linked_user_id !== null ? (
                      `user_id=${u.linked_user_id}`
                    ) : (
                      <Typography variant="caption" color="text.secondary">
                        紐付きなし
                      </Typography>
                    )}
                  </TableCell>
                  <TableCell>
                    {u.user_create_date
                      ? new Date(u.user_create_date).toLocaleDateString("ja-JP")
                      : "-"}
                  </TableCell>
                  <TableCell align="right">
                    <Stack direction="row" spacing={0.5} justifyContent="flex-end">
                      {u.enabled ? (
                        <Button
                          size="small"
                          variant="outlined"
                          color="warning"
                          onClick={() => disableMutation.mutate(u.username)}
                          disabled={disableMutation.isPending}
                        >
                          Disable
                        </Button>
                      ) : (
                        <Button
                          size="small"
                          variant="outlined"
                          color="success"
                          onClick={() => enableMutation.mutate(u.username)}
                          disabled={enableMutation.isPending}
                        >
                          Enable
                        </Button>
                      )}
                      <Button
                        size="small"
                        variant="outlined"
                        color="error"
                        onClick={() =>
                          setDeleteTarget({ username: u.username, email: u.email })
                        }
                      >
                        削除
                      </Button>
                    </Stack>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* 削除確認モーダル */}
      <Dialog open={deleteTarget !== null} onClose={() => setDeleteTarget(null)}>
        <DialogTitle>Cognito ユーザーを削除しますか?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            「{deleteTarget?.email || deleteTarget?.username}」を Cognito User Pool から完全削除します。
            紐付き m_cognito_links レコードも同時に削除されます。
            該当ユーザーは Cognito 経由でログインできなくなります (auth_user 自体は残ります)。
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteTarget(null)}>キャンセル</Button>
          <Button
            color="error"
            variant="contained"
            onClick={() => deleteTarget && deleteMutation.mutate(deleteTarget.username)}
            disabled={deleteMutation.isPending}
          >
            削除
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
