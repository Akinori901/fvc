import { useState } from "react";
import {
  Alert,
  Button,
  Card,
  CardContent,
  Chip,
  FormControlLabel,
  Link,
  Stack,
  Switch,
  TextField,
  Typography,
} from "@mui/material";
import { useApiConfigs, useUpdateApiConfig } from "@/hooks/useSettings";

const PROVIDER = "edinet";

/**
 * EDINET API 設定（管理者専用）。
 *
 * EDINET の有価証券報告書から大株主データを取得し、
 * オーナー経営銘柄の判定に使用する。
 */
export default function EdinetConfigSection() {
  const { data: configs } = useApiConfigs();
  const updateMutation = useUpdateApiConfig();

  const edinet = configs?.find((c) => c.provider === PROVIDER);
  const isRegistered = edinet !== undefined;

  const [apiKey, setApiKey] = useState("");
  const [enabled, setEnabled] = useState(edinet?.is_enabled ?? true);
  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    updateMutation.mutate(
      {
        provider: PROVIDER,
        data: {
          // 空欄のときは既存キーを維持する
          ...(apiKey ? { api_key: apiKey } : {}),
          is_enabled: enabled,
        },
      },
      {
        onSuccess: () => {
          setSaved(true);
          setApiKey("");
          setTimeout(() => setSaved(false), 3000);
        },
      }
    );
  };

  // 新規登録時はキー必須（未登録なのに空欄で保存しても意味がないため）
  const isSaveDisabled = updateMutation.isPending || (!isRegistered && !apiKey);

  return (
    <Card sx={{ mb: 3 }}>
      <CardContent>
        <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
          <Typography variant="h6">EDINET API 設定</Typography>
          <Chip
            label={isRegistered ? "登録済み" : "未登録"}
            size="small"
            color={isRegistered ? "success" : "default"}
          />
        </Stack>

        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          有価証券報告書から大株主データを取得し、オーナー経営銘柄の判定に使用します。
          APIキーは{" "}
          <Link
            href="https://api.edinet-fsa.go.jp/api/auth/index.aspx?mode=2"
            target="_blank"
            rel="noopener noreferrer"
          >
            EDINET の登録ページ
          </Link>{" "}
          から無料で取得できます。
        </Typography>

        {saved && (
          <Alert severity="success" sx={{ mb: 2 }}>
            設定を保存しました
          </Alert>
        )}

        {updateMutation.isError && (
          <Alert severity="error" sx={{ mb: 2 }}>
            保存に失敗しました。管理者権限があるか確認してください。
          </Alert>
        )}

        <Stack spacing={2}>
          <FormControlLabel
            control={<Switch checked={enabled} onChange={(e) => setEnabled(e.target.checked)} />}
            label="EDINET APIを有効にする"
          />

          <TextField
            label="APIキー"
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            helperText={
              isRegistered
                ? "登録済みです。変更する場合のみ入力してください（表示はされません）"
                : "EDINETで発行したAPIキーを入力してください"
            }
            fullWidth
          />

          <Button variant="contained" onClick={handleSave} disabled={isSaveDisabled}>
            保存
          </Button>
        </Stack>
      </CardContent>
    </Card>
  );
}
