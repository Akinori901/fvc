import { useState } from "react";
import {
  Card,
  CardContent,
  Typography,
  Stack,
  Switch,
  FormControlLabel,
  TextField,
  Button,
  Alert,
  MenuItem,
  CircularProgress,
  Link,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { aiApi } from "@/api/ai";

const AI_MODELS = [
  { value: "gemini-2.5-flash", label: "Gemini 2.5 Flash（推奨・無料枠あり）" },
  { value: "gemini-2.5-pro", label: "Gemini 2.5 Pro（高精度）" },
  { value: "gemini-2.0-flash", label: "Gemini 2.0 Flash（旧モデル）" },
];

export default function AiConfigSection() {
  const queryClient = useQueryClient();

  const { data: config, isLoading } = useQuery({
    queryKey: ["aiConfig"],
    queryFn: () => aiApi.getConfig().then((r) => r.data),
  });

  const [apiKey, setApiKey] = useState("");
  const [model, setModel] = useState("gemini-2.5-flash");
  const [isEnabled, setIsEnabled] = useState(false);
  const [saved, setSaved] = useState(false);
  const [initialized, setInitialized] = useState(false);

  // サーバーデータで初期化（1回のみ）
  if (config && !initialized) {
    setModel(config.model);
    setIsEnabled(config.is_enabled);
    setInitialized(true);
  }

  const saveMutation = useMutation({
    mutationFn: () =>
      aiApi.updateConfig({
        ...(apiKey ? { api_key: apiKey } : {}),
        model,
        is_enabled: isEnabled,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["aiConfig"] });
      setSaved(true);
      setApiKey("");
      setTimeout(() => setSaved(false), 3000);
    },
  });

  if (isLoading) return null;

  return (
    <Card sx={{ mb: 3 }}>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          AI分析設定（Google Gemini）
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          個別銘柄ページの「なぜPBRが低いのか」分析と、
          <strong>サイドバーの「AIチャット」</strong>
          の両方でこの設定が使用されます。Gemini APIキーは
          <Link href="https://aistudio.google.com/apikey?hl=ja" target="_blank" rel="noopener">
            Google AI Studio
          </Link>
          で確認・取得できます（無料枠あり）。
        </Typography>

        {saved && (
          <Alert severity="success" sx={{ mb: 2 }}>
            設定を保存しました
          </Alert>
        )}
        {saveMutation.isError && (
          <Alert severity="error" sx={{ mb: 2 }}>
            保存に失敗しました
          </Alert>
        )}

        <Stack spacing={2}>
          <FormControlLabel
            control={
              <Switch
                checked={isEnabled}
                onChange={(e) => setIsEnabled(e.target.checked)}
              />
            }
            label="AI分析を有効にする"
          />

          <TextField
            label="Gemini APIキー"
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder={config?.has_api_key ? "登録済み（変更時のみ入力）" : "AIza..."}
            helperText={
              config?.has_api_key
                ? `APIキー登録済み • 最終更新: ${config.updated_at ? new Date(config.updated_at).toLocaleDateString("ja-JP") : "-"}`
                : "Google AI StudioのAPIキーを入力してください"
            }
            fullWidth
          />

          <TextField
            select
            label="使用モデル"
            value={model}
            onChange={(e) => setModel(e.target.value)}
            fullWidth
          >
            {AI_MODELS.map((m) => (
              <MenuItem key={m.value} value={m.value}>
                {m.label}
              </MenuItem>
            ))}
          </TextField>

          <Button
            variant="contained"
            onClick={() => saveMutation.mutate()}
            disabled={saveMutation.isPending}
            startIcon={saveMutation.isPending ? <CircularProgress size={16} /> : undefined}
          >
            {saveMutation.isPending ? "保存中..." : "保存"}
          </Button>
        </Stack>
      </CardContent>
    </Card>
  );
}
