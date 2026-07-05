import { useState } from "react";
import {
  Alert,
  Box,
  Button,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import { adminApi } from "@/api/admin";

export default function CreateAdminUserForm() {
  const queryClient = useQueryClient();
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [warning, setWarning] = useState<string | null>(null);

  const createMutation = useMutation({
    mutationFn: (e: string) => adminApi.createUser(e).then((r) => r.data),
    onSuccess: (row) => {
      setEmail("");
      setError(null);
      if (row.invite_email_sent === false) {
        setWarning(
          `ユーザー ${row.email} は作成されましたが、Cognito 招待メールの送信に失敗しました。`,
        );
      } else {
        setWarning(null);
      }
      queryClient.invalidateQueries({ queryKey: ["adminUsers"] });
    },
    onError: (err: unknown) => {
      const message =
        axios.isAxiosError(err) && err.response?.data?.detail
          ? String(err.response.data.detail)
          : "ユーザー作成に失敗しました";
      setError(message);
      setWarning(null);
    },
  });

  const handleSubmit = () => {
    const trimmed = email.trim();
    if (!trimmed) {
      setError("email は必須です");
      return;
    }
    setError(null);
    createMutation.mutate(trimmed);
  };

  return (
    <Box sx={{ mb: 3 }}>
      <Typography variant="subtitle1" gutterBottom>
        新規ユーザー作成
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
        email から auth_user を作成します。同じ email が <code>m_user_allowed_emails</code> にも自動登録され、当該 email で Cognito ログインすると初回 JIT で紐付きます。
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {warning && (
        <Alert severity="warning" sx={{ mb: 2 }} onClose={() => setWarning(null)}>
          {warning}
        </Alert>
      )}

      <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5}>
        <TextField
          size="small"
          type="email"
          label="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          fullWidth
          inputProps={{ maxLength: 254 }}
        />
        <Button
          variant="contained"
          onClick={handleSubmit}
          disabled={!email.trim() || createMutation.isPending}
        >
          作成
        </Button>
      </Stack>
    </Box>
  );
}
