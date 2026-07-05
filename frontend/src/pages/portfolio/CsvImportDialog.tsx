import { useRef, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  MenuItem,
  Popover,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import HelpOutlineIcon from "@mui/icons-material/HelpOutline";
import UploadFileIcon from "@mui/icons-material/UploadFile";
import { usePreviewCsv, useImportCsv, useFamilyMembers } from "@/hooks/useFamilyPortfolio";
import { formatCurrency } from "@/utils/format";
import { ASSET_CLASS_LABELS } from "@/types/familyPortfolio";
import type { AssetClass, CsvHoldingDiff, CsvPreviewResult } from "@/types/familyPortfolio";

const PROVIDERS = [
  { value: "rakuten", label: "楽天証券（保有商品）" },
  { value: "rakuten_fund", label: "楽天証券（投資信託）" },
  { value: "rakuten_margin", label: "楽天証券（信用取引）" },
  { value: "rakuten_ideco", label: "楽天証券（iDeCo）" },
  { value: "sbi_portfolio", label: "SBI証券（ポートフォリオ）" },
  { value: "sbi_margin", label: "SBI証券（信用建玉）" },
] as const;

const PROVIDER_HELP: Record<string, { title: string; steps: string[] }> = {
  rakuten: {
    title: "楽天証券 保有商品CSVのダウンロード方法",
    steps: [
      "楽天証券にログイン",
      "「資産残高・保有商品」ページを開く",
      "「保有商品一覧」タブを選択",
      "表示切替で「すべて」を選択",
      "「CSV ダウンロード」ボタンをクリック",
    ],
  },
  rakuten_fund: {
    title: "楽天証券 投資信託CSVのダウンロード方法",
    steps: [
      "楽天証券にログイン",
      "「資産残高・保有商品」ページを開く",
      "「保有商品一覧」タブを選択",
      "表示切替で「投資信託」を選択",
      "「CSV ダウンロード」ボタンをクリック",
    ],
  },
  rakuten_margin: {
    title: "楽天証券 信用取引CSVのダウンロード方法",
    steps: [
      "楽天証券にログイン",
      "「信用取引」→「建玉一覧」ページを開く",
      "「CSV ダウンロード」ボタンをクリック",
    ],
  },
  rakuten_ideco: {
    title: "楽天証券 iDeCo CSVのダウンロード方法",
    steps: [
      "楽天証券 確定拠出年金サイトにログイン",
      "「資産状況」ページを開く",
      "資産残高の表をコピーしてCSV保存",
    ],
  },
  sbi_portfolio: {
    title: "SBI証券 ポートフォリオCSVのダウンロード方法",
    steps: [
      "SBI証券にログイン",
      "ヘッダー右上の「ポートフォリオ」アイコンをクリック",
      "「一括表示」を選択",
      "表の上または下にある「CSVダウンロード」ボタンをクリック",
      "現状は投資信託セクションのみ対応 (米株/預り金等は未対応)",
      "ファイル名に日付が含まれないため、スナップショット日は手動で指定してください",
    ],
  },
  sbi_margin: {
    title: "SBI証券 信用建玉CSVのダウンロード方法",
    steps: [
      "SBI証券にログイン",
      "「口座管理」→「信用建玉」ページを開く",
      "表示形式は「個別銘柄」を選択",
      "「CSVダウンロード」ボタンをクリック",
      "ファイル名: marginbalance(JP)_YYYYMMDD_HHMMSS.csv",
      "売建は負のポジションとして取り込まれます",
    ],
  },
};

const DIFF_STATUS_LABELS: Record<CsvHoldingDiff["status"], string> = {
  new: "追加",
  removed: "削除",
  changed: "変更",
  unchanged: "変更なし",
};

const DIFF_STATUS_COLORS: Record<CsvHoldingDiff["status"], string> = {
  new: "success",
  removed: "error",
  changed: "warning",
  unchanged: "default",
};

function DiffDetail({ groups }: { groups: CsvPreviewResult["account_groups"] }) {
  const groupsWithDiff = groups.filter((g) => g.diff);
  if (groupsWithDiff.length === 0) return null;

  return (
    <Box>
      <Typography variant="subtitle2" sx={{ mb: 1 }}>
        差分詳細
      </Typography>
      {groupsWithDiff.map((g, gi) => {
        const diff = g.diff!;
        const changedOrNew = diff.holdings_diff.filter((h) => h.status !== "unchanged");
        if (changedOrNew.length === 0) {
          return (
            <Alert key={gi} severity="info" sx={{ mb: 1 }}>
              {g.asset_type_raw}（{g.account_type_raw}）: 変更なし
            </Alert>
          );
        }
        return (
          <Box key={gi} sx={{ mb: 2 }}>
            <Typography variant="body2" fontWeight="bold" sx={{ mb: 0.5 }}>
              {g.asset_type_raw}（{g.account_type_raw}） — 前回: {diff.existing_snapshot_date}
            </Typography>
            <TableContainer sx={{ maxHeight: 300 }}>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>状態</TableCell>
                    <TableCell>銘柄</TableCell>
                    <TableCell align="right">数量</TableCell>
                    <TableCell align="right">前回評価額</TableCell>
                    <TableCell align="right">今回評価額</TableCell>
                    <TableCell align="right">増減</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {changedOrNew.map((h, hi) => {
                    const oldVal = h.old_value_jpy ? Number(h.old_value_jpy) : null;
                    const newVal = h.new_value_jpy ? Number(h.new_value_jpy) : null;
                    const change = oldVal != null && newVal != null ? newVal - oldVal : null;
                    return (
                      <TableRow key={hi}>
                        <TableCell>
                          <Chip
                            label={DIFF_STATUS_LABELS[h.status]}
                            size="small"
                            color={DIFF_STATUS_COLORS[h.status] as "success" | "error" | "warning" | "default"}
                            variant="outlined"
                          />
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2">
                            {h.ticker_code ? `${h.ticker_code} ` : ""}{h.asset_name}
                          </Typography>
                        </TableCell>
                        <TableCell align="right">
                          {h.status === "changed" && h.old_quantity !== h.new_quantity ? (
                            <Typography variant="body2">
                              {h.old_quantity} → {h.new_quantity}
                            </Typography>
                          ) : (
                            <Typography variant="body2">{h.new_quantity ?? h.old_quantity ?? "-"}</Typography>
                          )}
                        </TableCell>
                        <TableCell align="right">
                          {oldVal != null ? formatCurrency(oldVal) : "-"}
                        </TableCell>
                        <TableCell align="right">
                          {newVal != null ? formatCurrency(newVal) : "-"}
                        </TableCell>
                        <TableCell align="right">
                          {change != null ? (
                            <Typography
                              variant="body2"
                              color={change >= 0 ? "success.main" : "error.main"}
                              fontWeight="bold"
                            >
                              {change >= 0 ? "+" : ""}{formatCurrency(change)}
                            </Typography>
                          ) : (
                            "-"
                          )}
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </TableContainer>
          </Box>
        );
      })}
    </Box>
  );
}

interface Props {
  open: boolean;
  onClose: () => void;
}

export default function CsvImportDialog({ open, onClose }: Props) {
  const [provider, setProvider] = useState("rakuten");
  const [file, setFile] = useState<File | null>(null);
  const [memberId, setMemberId] = useState<number | "">("");
  const [preview, setPreview] = useState<CsvPreviewResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // ヘルプ Popover
  const [helpAnchor, setHelpAnchor] = useState<HTMLElement | null>(null);

  const { data: members = [] } = useFamilyMembers();
  const previewMutation = usePreviewCsv();
  const importMutation = useImportCsv();

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0] ?? null;
    setFile(f);
    setPreview(null);
    setError(null);
    setSuccessMsg(null);
  };

  const handlePreview = () => {
    if (!file) return;
    setError(null);
    previewMutation.mutate(
      { file, provider, familyMemberId: memberId ? (memberId as number) : undefined },
      {
        onSuccess: (data) => setPreview(data),
        onError: (err) => {
          const msg =
            (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
            "プレビューに失敗しました";
          setError(msg);
        },
      },
    );
  };

  const handleImport = () => {
    if (!file || !memberId || !preview) return;
    setError(null);
    importMutation.mutate(
      { file, provider, familyMemberId: memberId as number, snapshotDate: preview.snapshot_date },
      {
        onSuccess: (data) => {
          setSuccessMsg(data.message);
          setPreview(null);
          setFile(null);
          if (fileInputRef.current) fileInputRef.current.value = "";
        },
        onError: (err) => {
          const msg =
            (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
            "インポートに失敗しました";
          setError(msg);
        },
      },
    );
  };

  const handleClose = () => {
    setFile(null);
    setPreview(null);
    setError(null);
    setSuccessMsg(null);
    setMemberId("");
    onClose();
  };

  const helpInfo = PROVIDER_HELP[provider];
  const totalValue = preview?.account_groups.reduce((s, g) => s + Number(g.total_value_jpy), 0) ?? 0;
  const totalHoldings = preview?.account_groups.reduce((s, g) => s + g.holdings_count, 0) ?? 0;

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="md" fullWidth>
      <DialogTitle>
        <Stack direction="row" alignItems="center" spacing={1}>
          <UploadFileIcon />
          <span>CSVインポート</span>
        </Stack>
      </DialogTitle>
      <DialogContent>
        <Stack spacing={2.5} sx={{ mt: 1 }}>
          {/* プロバイダ選択 + ヘルプ */}
          <Stack direction="row" spacing={1} alignItems="flex-end">
            <TextField
              select
              label="証券会社"
              value={provider}
              onChange={(e) => {
                setProvider(e.target.value);
                setPreview(null);
                setFile(null);
                setError(null);
              }}
              sx={{ minWidth: 200 }}
            >
              {PROVIDERS.map((p) => (
                <MenuItem key={p.value} value={p.value}>
                  {p.label}
                </MenuItem>
              ))}
            </TextField>
            {helpInfo && (
              <>
                <IconButton size="small" onClick={(e) => setHelpAnchor(e.currentTarget)}>
                  <HelpOutlineIcon />
                </IconButton>
                <Popover
                  open={!!helpAnchor}
                  anchorEl={helpAnchor}
                  onClose={() => setHelpAnchor(null)}
                  anchorOrigin={{ vertical: "bottom", horizontal: "left" }}
                >
                  <Box sx={{ p: 2, maxWidth: 360 }}>
                    <Typography variant="subtitle2" gutterBottom>
                      {helpInfo.title}
                    </Typography>
                    <Box component="ol" sx={{ pl: 2.5, m: 0 }}>
                      {helpInfo.steps.map((step, i) => (
                        <Typography component="li" variant="body2" key={i} sx={{ mb: 0.5 }}>
                          {step}
                        </Typography>
                      ))}
                    </Box>
                  </Box>
                </Popover>
              </>
            )}
          </Stack>

          {/* ファイル選択 */}
          <Box>
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv"
              onChange={handleFileChange}
              style={{ display: "none" }}
            />
            <Stack direction="row" spacing={1} alignItems="center">
              <Button variant="outlined" onClick={() => fileInputRef.current?.click()}>
                ファイルを選択
              </Button>
              <Typography variant="body2" color="text.secondary">
                {file ? file.name : "CSVファイルを選択してください"}
              </Typography>
            </Stack>
          </Box>

          {/* メンバー選択（プレビュー前に選択 → 差分表示可能） */}
          {file && (
            <TextField
              select
              label="取込先の家族メンバー"
              value={memberId}
              onChange={(e) => {
                setMemberId(Number(e.target.value));
                setPreview(null);
              }}
              fullWidth
              required
              helperText="この証券会社の口座を持っているメンバーを選択してください"
            >
              {members.map((m) => (
                <MenuItem key={m.id} value={m.id}>
                  {m.name}
                </MenuItem>
              ))}
            </TextField>
          )}

          {/* プレビューボタン */}
          {file && !preview && (
            <Button
              variant="contained"
              onClick={handlePreview}
              disabled={previewMutation.isPending}
              sx={{ alignSelf: "flex-start" }}
            >
              {previewMutation.isPending ? "解析中..." : "プレビュー"}
            </Button>
          )}

          {error && <Alert severity="error">{error}</Alert>}
          {successMsg && <Alert severity="success">{successMsg}</Alert>}

          {/* プレビュー結果 */}
          {preview && (
            <>
              <Alert severity="info">
                {preview.snapshot_date} 時点 / {totalHoldings}銘柄 / 合計{" "}
                {formatCurrency(totalValue)}
              </Alert>

              {Object.keys(preview.exchange_rates).length > 0 && (
                <Stack direction="row" spacing={1}>
                  {Object.entries(preview.exchange_rates).map(([code, rate]) => (
                    <Chip key={code} label={`${code}: ${rate}円`} size="small" variant="outlined" />
                  ))}
                </Stack>
              )}

              <TableContainer sx={{ maxHeight: 400 }}>
                <Table size="small" stickyHeader>
                  <TableHead>
                    <TableRow>
                      <TableCell>種別</TableCell>
                      <TableCell>口座</TableCell>
                      <TableCell>資産クラス</TableCell>
                      <TableCell align="right">銘柄数</TableCell>
                      <TableCell align="right">時価合計(円)</TableCell>
                      <TableCell align="right">前回比</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {preview.account_groups.map((g, i) => {
                      const diff = g.diff;
                      const valueChange = diff ? Number(diff.value_change_jpy) : null;
                      return (
                        <TableRow key={i}>
                          <TableCell>{g.asset_type_raw}</TableCell>
                          <TableCell>{g.account_type_raw}</TableCell>
                          <TableCell>
                            <Chip
                              label={ASSET_CLASS_LABELS[g.asset_class as AssetClass] ?? g.asset_class}
                              size="small"
                              color="primary"
                              variant="outlined"
                            />
                          </TableCell>
                          <TableCell align="right">{g.holdings_count}</TableCell>
                          <TableCell align="right">{formatCurrency(g.total_value_jpy)}</TableCell>
                          <TableCell align="right">
                            {diff ? (
                              <Typography
                                variant="body2"
                                color={valueChange! >= 0 ? "success.main" : "error.main"}
                                fontWeight="bold"
                                component="span"
                              >
                                {valueChange! >= 0 ? "+" : ""}{formatCurrency(valueChange!)}
                              </Typography>
                            ) : (
                              <Chip label="新規" size="small" color="success" variant="outlined" />
                            )}
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </TableContainer>

              {/* 差分詳細 */}
              {preview.account_groups.some((g) => g.diff) && (
                <DiffDetail groups={preview.account_groups} />
              )}
            </>
          )}
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose}>閉じる</Button>
        {preview && (
          <Button
            variant="contained"
            onClick={handleImport}
            disabled={!memberId || importMutation.isPending}
          >
            {importMutation.isPending ? "インポート中..." : "インポート実行"}
          </Button>
        )}
      </DialogActions>
    </Dialog>
  );
}
