import { Alert } from "@mui/material";

interface Props {
  message?: string;
}

export default function ErrorAlert({ message = "データの取得に失敗しました" }: Props) {
  return (
    <Alert severity="error" sx={{ mb: 2 }}>
      {message}
    </Alert>
  );
}
