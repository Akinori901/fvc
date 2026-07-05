import { useState } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Collapse,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  IconButton,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import KeyboardArrowUpIcon from "@mui/icons-material/KeyboardArrowUp";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import { adminApi } from "@/api/admin";
import type {
  AdminUserRow,
  CognitoLinkInfo,
  UserAllowedEmailInfo,
} from "@/types/admin";

type DeleteTarget =
  | { kind: "allowed-email"; userId: number; allowedId: number; label: string }
  | { kind: "cognito-link"; userId: number; linkId: number; label: string }
  | { kind: "user-delete"; userId: number; label: string }
  | null;

export default function AdminUsersTable() {
  const queryClient = useQueryClient();
  const { data, isLoading, isError } = useQuery({
    queryKey: ["adminUsers"],
    queryFn: () => adminApi.listUsers().then((r) => r.data),
  });

  const [expanded, setExpanded] = useState<Record<number, boolean>>({});
  const [deleteTarget, setDeleteTarget] = useState<DeleteTarget>(null);

  const removeAllowedMutation = useMutation({
    mutationFn: ({ userId, allowedId }: { userId: number; allowedId: number }) =>
      adminApi.removeAllowedEmail(userId, allowedId),
    onSuccess: () => {
      setDeleteTarget(null);
      queryClient.invalidateQueries({ queryKey: ["adminUsers"] });
    },
  });

  const deleteLinkMutation = useMutation({
    mutationFn: ({ userId, linkId }: { userId: number; linkId: number }) =>
      adminApi.deleteCognitoLink(userId, linkId),
    onSuccess: () => {
      setDeleteTarget(null);
      queryClient.invalidateQueries({ queryKey: ["adminUsers"] });
    },
  });

  const disableUserMutation = useMutation({
    mutationFn: (userId: number) => adminApi.disableUser(userId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["adminUsers"] }),
  });

  const enableUserMutation = useMutation({
    mutationFn: (userId: number) => adminApi.enableUser(userId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["adminUsers"] }),
  });

  const deleteUserMutation = useMutation({
    mutationFn: (userId: number) => adminApi.deleteUser(userId),
    onSuccess: () => {
      setDeleteTarget(null);
      queryClient.invalidateQueries({ queryKey: ["adminUsers"] });
    },
  });

  const toggleExpanded = (userId: number) => {
    setExpanded((prev) => ({ ...prev, [userId]: !prev[userId] }));
  };

  const handleConfirmDelete = () => {
    if (!deleteTarget) return;
    if (deleteTarget.kind === "allowed-email") {
      removeAllowedMutation.mutate({
        userId: deleteTarget.userId,
        allowedId: deleteTarget.allowedId,
      });
    } else if (deleteTarget.kind === "cognito-link") {
      deleteLinkMutation.mutate({
        userId: deleteTarget.userId,
        linkId: deleteTarget.linkId,
      });
    } else {
      deleteUserMutation.mutate(deleteTarget.userId);
    }
  };

  if (isLoading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", p: 2 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (isError) {
    return <Alert severity="error">ユーザー一覧の取得に失敗しました</Alert>;
  }

  return (
    <Box>
      <Typography variant="subtitle1" gutterBottom>
        ユーザー一覧
      </Typography>

      <TableContainer>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell />
              <TableCell>ID</TableCell>
              <TableCell>email</TableCell>
              <TableCell>username</TableCell>
              <TableCell>権限</TableCell>
              <TableCell>許可 email</TableCell>
              <TableCell>Cognito link</TableCell>
              <TableCell>最終ログイン</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {(data?.users ?? []).length === 0 ? (
              <TableRow>
                <TableCell colSpan={8} align="center">
                  <Typography variant="body2" color="text.secondary">
                    ユーザーが存在しません
                  </Typography>
                </TableCell>
              </TableRow>
            ) : (
              data!.users.map((user) => (
                <UserRow
                  key={user.id}
                  user={user}
                  expanded={!!expanded[user.id]}
                  onToggle={() => toggleExpanded(user.id)}
                  onRequestDeleteAllowedEmail={(allowed) =>
                    setDeleteTarget({
                      kind: "allowed-email",
                      userId: user.id,
                      allowedId: allowed.id,
                      label: allowed.email,
                    })
                  }
                  onRequestDeleteLink={(link) =>
                    setDeleteTarget({
                      kind: "cognito-link",
                      userId: user.id,
                      linkId: link.id,
                      label: `${link.provider} / ${link.cognito_email || link.cognito_sub.slice(0, 8)}`,
                    })
                  }
                  onRequestDeleteUser={() =>
                    setDeleteTarget({
                      kind: "user-delete",
                      userId: user.id,
                      label: user.email || user.username,
                    })
                  }
                  onToggleActive={() => {
                    if (user.is_active) {
                      disableUserMutation.mutate(user.id);
                    } else {
                      enableUserMutation.mutate(user.id);
                    }
                  }}
                  isToggleActivePending={
                    disableUserMutation.isPending || enableUserMutation.isPending
                  }
                />
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* 削除確認モーダル */}
      <Dialog open={deleteTarget !== null} onClose={() => setDeleteTarget(null)}>
        <DialogTitle>
          {deleteTarget?.kind === "allowed-email" && "許可 email を削除しますか？"}
          {deleteTarget?.kind === "cognito-link" && "Cognito link を削除しますか？"}
          {deleteTarget?.kind === "user-delete" && "ユーザーを完全削除しますか？"}
        </DialogTitle>
        <DialogContent>
          <DialogContentText>
            「{deleteTarget?.label}」を削除します。
            {deleteTarget?.kind === "cognito-link" &&
              " 該当ユーザーはこの identity で再度ログインすると、許可 email にマッチすれば新規 link が再生成されます。"}
            {deleteTarget?.kind === "allowed-email" &&
              " 以降この email でのログイン (招待制チェック) は拒否されます。既存 link は残ります。"}
            {deleteTarget?.kind === "user-delete" &&
              " ⚠️ CASCADE 削除で、このユーザーの portfolio / watchlist / 許可 email / Cognito link 等、関連するすべてのデータが消えます。元に戻せません。"}
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteTarget(null)}>キャンセル</Button>
          <Button
            color="error"
            variant="contained"
            onClick={handleConfirmDelete}
            disabled={
              removeAllowedMutation.isPending ||
              deleteLinkMutation.isPending ||
              deleteUserMutation.isPending
            }
          >
            {deleteTarget?.kind === "user-delete" ? "完全削除する" : "削除"}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

interface UserRowProps {
  user: AdminUserRow;
  expanded: boolean;
  onToggle: () => void;
  onRequestDeleteAllowedEmail: (allowed: UserAllowedEmailInfo) => void;
  onRequestDeleteLink: (link: CognitoLinkInfo) => void;
  onRequestDeleteUser: () => void;
  onToggleActive: () => void;
  isToggleActivePending: boolean;
}

function UserRow({
  user,
  expanded,
  onToggle,
  onRequestDeleteAllowedEmail,
  onRequestDeleteLink,
  onRequestDeleteUser,
  onToggleActive,
  isToggleActivePending,
}: UserRowProps) {
  return (
    <>
      <TableRow hover>
        <TableCell padding="none">
          <IconButton size="small" onClick={onToggle}>
            {expanded ? <KeyboardArrowUpIcon /> : <KeyboardArrowDownIcon />}
          </IconButton>
        </TableCell>
        <TableCell>{user.id}</TableCell>
        <TableCell>{user.email}</TableCell>
        <TableCell>{user.username}</TableCell>
        <TableCell>
          <Stack direction="row" spacing={0.5}>
            {user.is_superuser && (
              <Chip label="superuser" color="primary" size="small" />
            )}
            {user.is_staff && !user.is_superuser && (
              <Chip label="staff" color="default" size="small" />
            )}
            {!user.is_staff && !user.is_superuser && (
              <Chip label="user" variant="outlined" size="small" />
            )}
            {!user.is_active && (
              <Chip label="無効" color="error" size="small" variant="outlined" />
            )}
          </Stack>
        </TableCell>
        <TableCell>{user.allowed_emails.length}</TableCell>
        <TableCell>{user.cognito_links.length}</TableCell>
        <TableCell>
          {user.last_login
            ? new Date(user.last_login).toLocaleString("ja-JP")
            : "-"}
        </TableCell>
      </TableRow>
      <TableRow>
        <TableCell colSpan={8} sx={{ pb: 0, pt: 0, borderBottom: "none" }}>
          <Collapse in={expanded} timeout="auto" unmountOnExit>
            <Box sx={{ p: 2, backgroundColor: "action.hover" }}>
              <AllowedEmailSection
                userId={user.id}
                emails={user.allowed_emails}
                onRequestDelete={onRequestDeleteAllowedEmail}
              />
              <CognitoLinkSection
                links={user.cognito_links}
                onRequestDelete={onRequestDeleteLink}
              />
              <Box sx={{ mt: 2, pt: 2, borderTop: 1, borderColor: "divider" }}>
                <Typography variant="subtitle2" gutterBottom>
                  ユーザー操作
                </Typography>
                <Stack direction="row" spacing={1}>
                  <Button
                    size="small"
                    variant="outlined"
                    color={user.is_active ? "warning" : "success"}
                    onClick={onToggleActive}
                    disabled={isToggleActivePending}
                  >
                    {user.is_active ? "ユーザーを無効化" : "ユーザーを有効化"}
                  </Button>
                  <Button
                    size="small"
                    variant="outlined"
                    color="error"
                    onClick={onRequestDeleteUser}
                  >
                    ユーザーを完全削除
                  </Button>
                </Stack>
              </Box>
            </Box>
          </Collapse>
        </TableCell>
      </TableRow>
    </>
  );
}

interface AllowedEmailSectionProps {
  userId: number;
  emails: UserAllowedEmailInfo[];
  onRequestDelete: (allowed: UserAllowedEmailInfo) => void;
}

function AllowedEmailSection({
  userId,
  emails,
  onRequestDelete,
}: AllowedEmailSectionProps) {
  const queryClient = useQueryClient();
  const [email, setEmail] = useState("");
  const [label, setLabel] = useState("");
  const [error, setError] = useState<string | null>(null);

  const addMutation = useMutation({
    mutationFn: (input: { email: string; label: string }) =>
      adminApi.addAllowedEmail(userId, input.email, input.label).then((r) => r.data),
    onSuccess: () => {
      setEmail("");
      setLabel("");
      setError(null);
      queryClient.invalidateQueries({ queryKey: ["adminUsers"] });
    },
    onError: (err: unknown) => {
      const message =
        axios.isAxiosError(err) && err.response?.data?.detail
          ? String(err.response.data.detail)
          : "追加に失敗しました";
      setError(message);
    },
  });

  const handleAdd = () => {
    const e = email.trim();
    if (!e) return;
    addMutation.mutate({ email: e, label: label.trim() });
  };

  return (
    <Box sx={{ mb: 2 }}>
      <Typography variant="subtitle2" gutterBottom>
        許可 email
      </Typography>

      {emails.length === 0 ? (
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
          登録されていません
        </Typography>
      ) : (
        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mb: 1 }}>
          {emails.map((e) => (
            <Chip
              key={e.id}
              label={e.label ? `${e.email} (${e.label})` : e.email}
              onDelete={() => onRequestDelete(e)}
              deleteIcon={
                <Tooltip title="削除">
                  <DeleteOutlineIcon />
                </Tooltip>
              }
              size="small"
            />
          ))}
        </Stack>
      )}

      {error && (
        <Alert severity="error" sx={{ mb: 1 }}>
          {error}
        </Alert>
      )}

      <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
        <TextField
          size="small"
          type="email"
          label="追加する email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          fullWidth
          inputProps={{ maxLength: 254 }}
        />
        <TextField
          size="small"
          label="ラベル (任意)"
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          sx={{ minWidth: 200 }}
          inputProps={{ maxLength: 100 }}
        />
        <Button
          variant="outlined"
          onClick={handleAdd}
          disabled={!email.trim() || addMutation.isPending}
        >
          追加
        </Button>
      </Stack>
    </Box>
  );
}

interface CognitoLinkSectionProps {
  links: CognitoLinkInfo[];
  onRequestDelete: (link: CognitoLinkInfo) => void;
}

function CognitoLinkSection({ links, onRequestDelete }: CognitoLinkSectionProps) {
  return (
    <Box>
      <Typography variant="subtitle2" gutterBottom>
        Cognito link
      </Typography>

      {links.length === 0 ? (
        <Typography variant="body2" color="text.secondary">
          紐付き link はありません
        </Typography>
      ) : (
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>provider</TableCell>
                <TableCell>cognito_email</TableCell>
                <TableCell>cognito_sub</TableCell>
                <TableCell>最終ログイン</TableCell>
                <TableCell align="right">操作</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {links.map((link) => (
                <TableRow key={link.id}>
                  <TableCell>
                    <Chip
                      label={link.provider}
                      size="small"
                      color={link.provider === "google" ? "warning" : "default"}
                    />
                  </TableCell>
                  <TableCell>{link.cognito_email || "-"}</TableCell>
                  <TableCell>
                    <code style={{ fontSize: "0.75rem" }}>
                      {link.cognito_sub.slice(0, 16)}…
                    </code>
                  </TableCell>
                  <TableCell>
                    {link.last_signed_in_at
                      ? new Date(link.last_signed_in_at).toLocaleString("ja-JP")
                      : "-"}
                  </TableCell>
                  <TableCell align="right">
                    <Tooltip title="この link を削除">
                      <IconButton
                        size="small"
                        color="error"
                        onClick={() => onRequestDelete(link)}
                      >
                        <DeleteOutlineIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </Box>
  );
}
