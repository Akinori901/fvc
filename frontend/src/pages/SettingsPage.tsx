import { useState } from "react";
import {
  Box,
  Typography,
  Card,
  CardContent,
  TextField,
  Button,
  Stack,
  MenuItem,
  Alert,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Switch,
  FormControlLabel,
} from "@mui/material";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import CancelIcon from "@mui/icons-material/Cancel";
import { useApiConfigs, useUpdateApiConfig } from "@/hooks/useSettings";
import LoadingSpinner from "@/components/common/LoadingSpinner";
import AiConfigSection from "@/components/settings/AiConfigSection";
import McpApiKeySection from "@/components/settings/McpApiKeySection";
import EdinetConfigSection from "@/components/settings/EdinetConfigSection";
import {
  changeCognitoPassword,
  confirmCognitoEmailUpdate,
  startCognitoEmailUpdate,
} from "@/auth/amplify-account";
import { useAuthStore } from "@/stores/authStore";

const PLANS = ["free", "light", "standard", "premium"];

const FEATURE_TABLE = [
  { label: "銘柄一覧同期", key: "stock_list_sync" },
  { label: "財務データ同期", key: "financial_sync" },
  { label: "株価同期", key: "price_sync" },
  { label: "適正株価算出（手動入力）", key: "manual_calculation" },
] as const;

const PLAN_FEATURES_ALL: Record<string, Record<string, boolean | number | string>> = {
  free: { stock_list_sync: true, financial_sync: false, financial_years: 0, price_sync: false, manual_calculation: true, label: "Free" },
  light: { stock_list_sync: true, financial_sync: true, financial_years: 2, price_sync: false, manual_calculation: true, label: "Light" },
  standard: { stock_list_sync: true, financial_sync: true, financial_years: 10, price_sync: true, manual_calculation: true, label: "Standard" },
  premium: { stock_list_sync: true, financial_sync: true, financial_years: -1, price_sync: true, manual_calculation: true, label: "Premium" },
};

function AccountSection() {
  const { user, setUser } = useAuthStore();
  const [email, setEmail] = useState(user?.email ?? "");
  const [emailMsg, setEmailMsg] = useState<{ type: "success" | "error" | "info"; text: string } | null>(null);
  const [emailLoading, setEmailLoading] = useState(false);
  const [emailConfirmCode, setEmailConfirmCode] = useState("");
  const [needsEmailConfirmation, setNeedsEmailConfirmation] = useState(false);

  const [oldPassword, setOldPassword] = useState("");
  const [newPassword1, setNewPassword1] = useState("");
  const [newPassword2, setNewPassword2] = useState("");
  const [pwMsg, setPwMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [pwLoading, setPwLoading] = useState(false);

  const handleUpdateEmail = async () => {
    if (!email.trim()) return;
    setEmailLoading(true);
    setEmailMsg(null);
    try {
      // Amplify updateUserAttributes → 確認コード入力フェーズへ
      const needsConfirmation = await startCognitoEmailUpdate(email.trim());
      if (needsConfirmation) {
        setNeedsEmailConfirmation(true);
        setEmailMsg({
          type: "info",
          text: "確認コードを新しいメールアドレス宛に送信しました。受信したコードを入力してください。",
        });
      } else {
        // 即時反映 (通常起こらないが念のため)
        setUser({ ...user!, email: email.trim() });
        setEmailMsg({ type: "success", text: "メールアドレスを更新しました" });
      }
    } catch {
      setEmailMsg({ type: "error", text: "メールアドレスの更新に失敗しました" });
    } finally {
      setEmailLoading(false);
    }
  };

  const handleConfirmEmail = async () => {
    if (!emailConfirmCode.trim()) return;
    setEmailLoading(true);
    setEmailMsg(null);
    try {
      await confirmCognitoEmailUpdate(emailConfirmCode.trim());
      setUser({ ...user!, email: email.trim() });
      setNeedsEmailConfirmation(false);
      setEmailConfirmCode("");
      setEmailMsg({ type: "success", text: "メールアドレスを更新しました" });
    } catch {
      setEmailMsg({
        type: "error",
        text: "確認コードが正しくないか期限切れです。再度メールアドレス更新からやり直してください。",
      });
    } finally {
      setEmailLoading(false);
    }
  };

  const handleChangePassword = async () => {
    if (newPassword1 !== newPassword2) {
      setPwMsg({ type: "error", text: "新しいパスワードが一致しません" });
      return;
    }
    if (newPassword1.length < 8) {
      setPwMsg({ type: "error", text: "パスワードは8文字以上にしてください" });
      return;
    }
    setPwLoading(true);
    setPwMsg(null);
    try {
      await changeCognitoPassword(oldPassword, newPassword1);
      setPwMsg({ type: "success", text: "パスワードを変更しました" });
      setOldPassword("");
      setNewPassword1("");
      setNewPassword2("");
    } catch {
      setPwMsg({ type: "error", text: "パスワード変更に失敗しました。現在のパスワードを確認してください" });
    } finally {
      setPwLoading(false);
    }
  };

  return (
    <Card sx={{ mb: 3 }}>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          アカウント設定
        </Typography>

        <Stack spacing={2}>
          <TextField
            label="表示名"
            value={user?.username ?? ""}
            disabled
            fullWidth
            size="small"
          />

          {emailMsg && (
            <Alert severity={emailMsg.type}>{emailMsg.text}</Alert>
          )}

          <Stack direction="row" spacing={1} alignItems="flex-start">
            <TextField
              label="メールアドレス"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              fullWidth
              size="small"
              disabled={needsEmailConfirmation}
            />
            <Button
              variant="outlined"
              onClick={handleUpdateEmail}
              disabled={
                emailLoading ||
                needsEmailConfirmation ||
                email.trim() === (user?.email ?? "")
              }
              sx={{ whiteSpace: "nowrap", minWidth: 80 }}
            >
              更新
            </Button>
          </Stack>

          {needsEmailConfirmation && (
            <Stack direction="row" spacing={1} alignItems="flex-start">
              <TextField
                label="確認コード"
                value={emailConfirmCode}
                onChange={(e) => setEmailConfirmCode(e.target.value)}
                fullWidth
                size="small"
                helperText="新しいメールアドレスに届いた6桁のコード"
              />
              <Button
                variant="contained"
                onClick={handleConfirmEmail}
                disabled={emailLoading || !emailConfirmCode.trim()}
                sx={{ whiteSpace: "nowrap", minWidth: 80 }}
              >
                確定
              </Button>
            </Stack>
          )}

          <Typography variant="subtitle1" sx={{ mt: 2 }}>
            パスワード変更
          </Typography>

          {pwMsg && (
            <Alert severity={pwMsg.type}>{pwMsg.text}</Alert>
          )}

          <TextField
            label="現在のパスワード"
            type="password"
            value={oldPassword}
            onChange={(e) => setOldPassword(e.target.value)}
            fullWidth
            size="small"
          />
          <TextField
            label="新しいパスワード"
            type="password"
            value={newPassword1}
            onChange={(e) => setNewPassword1(e.target.value)}
            fullWidth
            size="small"
          />
          <TextField
            label="新しいパスワード（確認）"
            type="password"
            value={newPassword2}
            onChange={(e) => setNewPassword2(e.target.value)}
            fullWidth
            size="small"
          />

          <Button
            variant="contained"
            onClick={handleChangePassword}
            disabled={pwLoading || !oldPassword || !newPassword1 || !newPassword2}
          >
            パスワードを変更
          </Button>
        </Stack>
      </CardContent>
    </Card>
  );
}

export default function SettingsPage() {
  const user = useAuthStore((s) => s.user);
  const isAdmin = user?.is_superuser ?? false;
  const { data: configs, isLoading } = useApiConfigs();
  const updateMutation = useUpdateApiConfig();

  const jquants = configs?.find((c) => c.provider === "jquants");

  const [apiKey, setApiKey] = useState("");
  const [plan, setPlan] = useState(jquants?.plan || "free");
  const [enabled, setEnabled] = useState(jquants?.is_enabled ?? false);
  const [saved, setSaved] = useState(false);

  // Update local state when data loads
  if (jquants && plan === "free" && jquants.plan !== "free") {
    setPlan(jquants.plan);
    setEnabled(jquants.is_enabled);
  }

  const handleSave = () => {
    updateMutation.mutate(
      {
        provider: "jquants",
        data: {
          ...(apiKey ? { api_key: apiKey } : {}),
          plan,
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

  if (isLoading) return <LoadingSpinner />;

  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        設定
      </Typography>

      {/* アカウント情報・メールアドレス変更・パスワード変更 */}
      <AccountSection />

      {/* AI設定 (全ユーザー: 個人の OpenAI/Gemini キー登録) */}
      <AiConfigSection />

      {/* 外部AI連携 APIキー (全ユーザー: MCP / Custom GPT 等の外部連携用) */}
      <McpApiKeySection />

      {/* 管理者専用セクション */}
      {isAdmin && (
        <>
          {/* J-Quants 設定 */}
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                J-Quants API 設定
              </Typography>

              {saved && (
                <Alert severity="success" sx={{ mb: 2 }}>
                  設定を保存しました
                </Alert>
              )}

              <Stack spacing={2}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={enabled}
                      onChange={(e) => setEnabled(e.target.checked)}
                    />
                  }
                  label="J-Quants APIを有効にする"
                />

                <TextField
                  label="APIキー"
                  type="password"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  helperText="J-QuantsのAPIキーを入力してください（変更時のみ）"
                  fullWidth
                />

                <TextField
                  select
                  label="契約プラン"
                  value={plan}
                  onChange={(e) => setPlan(e.target.value)}
                  fullWidth
                >
                  {PLANS.map((p) => (
                    <MenuItem key={p} value={p}>
                      {p.charAt(0).toUpperCase() + p.slice(1)}
                    </MenuItem>
                  ))}
                </TextField>

                <Button
                  variant="contained"
                  onClick={handleSave}
                  disabled={updateMutation.isPending}
                >
                  保存
                </Button>
              </Stack>
            </CardContent>
          </Card>

          {/* EDINET 設定（大株主データ = オーナー経営判定に使用） */}
          <EdinetConfigSection />

          {/* プラン別機能比較 */}
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                プラン別機能比較
              </Typography>

              <TableContainer component={Paper} variant="outlined">
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>機能</TableCell>
                      {PLANS.map((p) => (
                        <TableCell key={p} align="center">
                          {String(PLAN_FEATURES_ALL[p]?.label ?? p)}
                          {jquants?.plan === p && " (現在)"}
                        </TableCell>
                      ))}
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {FEATURE_TABLE.map(({ label, key }) => (
                      <TableRow key={key}>
                        <TableCell>{label}</TableCell>
                        {PLANS.map((p) => (
                          <TableCell key={p} align="center">
                            {PLAN_FEATURES_ALL[p]?.[key] ? (
                              <CheckCircleIcon
                                fontSize="small"
                                sx={{ color: "success.main" }}
                              />
                            ) : (
                              <CancelIcon
                                fontSize="small"
                                sx={{ color: "error.main" }}
                              />
                            )}
                          </TableCell>
                        ))}
                      </TableRow>
                    ))}
                    <TableRow>
                      <TableCell>財務データ取得期間</TableCell>
                      <TableCell align="center">-</TableCell>
                      <TableCell align="center">2年</TableCell>
                      <TableCell align="center">10年</TableCell>
                      <TableCell align="center">全期間</TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        </>
      )}
    </Box>
  );
}
