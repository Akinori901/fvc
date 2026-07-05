import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Box,
  Typography,
  Button,
  Card,
  CardContent,
  Stack,
  TextField,
  MenuItem,
  IconButton,
  Alert,
  Divider,
  Table,
  TableHead,
  TableRow,
  TableCell,
  TableBody,
} from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/Delete";
import SaveIcon from "@mui/icons-material/Save";
import {
  usePortfolioAccounts,
  useAccountSnapshots,
  useUpsertSnapshot,
  useDeleteSnapshot,
} from "@/hooks/useFamilyPortfolio";
import { formatCurrency } from "@/utils/format";
import type { AccountHolding, AccountSnapshotInput } from "@/types/familyPortfolio";

const ASSET_TYPES = [
  { value: "stock", label: "株式" },
  { value: "etf", label: "ETF" },
  { value: "fund", label: "投資信託" },
  { value: "bond", label: "債券" },
  { value: "cash", label: "現金" },
  { value: "other", label: "その他" },
];

interface HoldingRow {
  ticker_code: string;
  asset_name: string;
  asset_type: string;
  quantity: string;
  unit_price: string;
  value_jpy: string;
  cost_jpy: string;
  built_date: string;
}

const emptyHolding = (): HoldingRow => ({
  ticker_code: "",
  asset_name: "",
  asset_type: "stock",
  quantity: "",
  unit_price: "",
  value_jpy: "",
  cost_jpy: "",
  built_date: "",
});

// YYYY-MM → YYYY-MM-01 (月の最終日に近い形)
const toSnapshotDate = (month: string) => {
  const [y, m] = month.split("-").map(Number) as [number, number];
  const lastDay = new Date(y, m, 0).getDate();
  return `${y}-${String(m).padStart(2, "0")}-${String(lastDay).padStart(2, "0")}`;
};

const toMonthValue = (dateStr: string) => dateStr.slice(0, 7);

export default function AccountInputPage() {
  const { id } = useParams<{ id: string }>();
  const accountId = Number(id);
  const navigate = useNavigate();

  const { data: accounts = [] } = usePortfolioAccounts();
  const { data: snapshots = [] } = useAccountSnapshots(accountId);
  const upsertMutation = useUpsertSnapshot();
  const deleteMutation = useDeleteSnapshot();

  const account = accounts.find((a) => a.id === accountId);

  // 選択中の月
  const currentMonth = new Date();
  const defaultMonth = `${currentMonth.getFullYear()}-${String(currentMonth.getMonth() + 1).padStart(2, "0")}`;
  const [selectedMonth, setSelectedMonth] = useState(defaultMonth);

  // フォーム状態
  const [totalValue, setTotalValue] = useState("");
  const [totalCost, setTotalCost] = useState("");
  const [exchangeRate, setExchangeRate] = useState("");
  const [notes, setNotes] = useState("");
  const [holdings, setHoldings] = useState<HoldingRow[]>([]);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  // 選択月のスナップショットがあれば読み込む
  useEffect(() => {
    const snap = snapshots.find((s) => toMonthValue(s.snapshot_date) === selectedMonth);
    if (snap) {
      setTotalValue(snap.total_value_jpy);
      setTotalCost(snap.total_cost_jpy ?? "");
      setExchangeRate(snap.exchange_rate ?? "");
      setNotes(snap.notes ?? "");
      setHoldings(
        snap.holdings.map((h) => ({
          ticker_code: h.ticker_code ?? "",
          asset_name: h.asset_name,
          asset_type: h.asset_type,
          quantity: h.quantity ?? "",
          unit_price: h.unit_price ?? "",
          value_jpy: h.value_jpy,
          cost_jpy: h.cost_jpy ?? "",
          built_date: h.built_date ?? "",
        }))
      );
    } else {
      setTotalValue("");
      setTotalCost("");
      setExchangeRate("");
      setNotes("");
      setHoldings([]);
    }
    setSaveSuccess(false);
    setSaveError(null);
  }, [selectedMonth, snapshots]);

  const handleAddHolding = () => setHoldings((prev) => [...prev, emptyHolding()]);
  const handleRemoveHolding = (i: number) =>
    setHoldings((prev) => prev.filter((_, idx) => idx !== i));
  const handleHoldingChange = (i: number, field: keyof HoldingRow, value: string) =>
    setHoldings((prev) => prev.map((h, idx) => (idx === i ? { ...h, [field]: value } : h)));

  // 保有明細の合計から自動計算
  const autoCalcTotal = () => {
    const sum = holdings.reduce((acc, h) => acc + (Number(h.value_jpy) || 0), 0);
    if (sum > 0) setTotalValue(String(sum));
  };

  const handleSave = () => {
    if (!totalValue) return;
    setSaveError(null);
    const snapshotDate = toSnapshotDate(selectedMonth);
    const holdingData: AccountHolding[] = holdings
      .filter((h) => h.asset_name && h.value_jpy)
      .map((h) => ({
        ticker_code: h.ticker_code || undefined,
        asset_name: h.asset_name,
        asset_type: h.asset_type,
        quantity: h.quantity || undefined,
        unit_price: h.unit_price || undefined,
        value_jpy: h.value_jpy,
        cost_jpy: h.cost_jpy || undefined,
        built_date: h.built_date || null,
      }));

    const data: AccountSnapshotInput = {
      snapshot_date: snapshotDate,
      total_value_jpy: totalValue,
      total_cost_jpy: totalCost || null,
      exchange_rate: exchangeRate || null,
      notes,
      holdings: holdingData,
    };
    upsertMutation.mutate(
      { accountId, data },
      {
        onSuccess: () => {
          setSaveSuccess(true);
          setTimeout(() => setSaveSuccess(false), 3000);
        },
        onError: (err: unknown) => {
          const response = (err as { response?: { data?: unknown } })?.response;
          const detail =
            (response?.data as { detail?: string } | undefined)?.detail ??
            (typeof response?.data === "object" ? JSON.stringify(response?.data) : null) ??
            (err as Error)?.message ??
            "保存に失敗しました";
          setSaveError(detail);
        },
      }
    );
  };

  const handleDelete = () => {
    const snap = snapshots.find((s) => toMonthValue(s.snapshot_date) === selectedMonth);
    if (!snap) return;
    if (!window.confirm("このスナップショットを削除しますか？")) return;
    deleteMutation.mutate({ accountId, date: snap.snapshot_date });
  };

  const existingSnap = snapshots.find((s) => toMonthValue(s.snapshot_date) === selectedMonth);
  const isUsd = account?.currency === "USD";

  return (
    <Box>
      <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 2 }}>
        <IconButton onClick={() => navigate("/portfolio")}>
          <ArrowBackIcon />
        </IconButton>
        <Box>
          <Typography variant="h5">月次残高入力</Typography>
          {account && (
            <Typography variant="body2" color="text.secondary">
              {account.family_member_name} / {account.nickname || account.institution}（{account.asset_class_display}）
            </Typography>
          )}
        </Box>
      </Stack>

      {saveSuccess && (
        <Alert severity="success" sx={{ mb: 2 }}>
          保存しました。
        </Alert>
      )}
      {saveError && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setSaveError(null)}>
          {saveError}
        </Alert>
      )}

      <Card>
        <CardContent>
          <Stack spacing={3}>
            {/* 月選択 */}
            <TextField
              label="記録月"
              type="month"
              value={selectedMonth}
              onChange={(e) => setSelectedMonth(e.target.value)}
              slotProps={{ inputLabel: { shrink: true } }}
              sx={{ width: 200 }}
            />

            <Divider />

            {/* 残高入力 */}
            <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
              <TextField
                label="評価額合計（円換算後）"
                type="number"
                value={totalValue}
                onChange={(e) => setTotalValue(e.target.value)}
                required
                inputProps={{ step: 1000 }}
                sx={{ flex: 1 }}
                helperText={
                  isUsd
                    ? "JPY 換算後の合計を入力（例: SBI CSV の『円換算評価額』）"
                    : totalValue
                      ? formatCurrency(Number(totalValue))
                      : ""
                }
              />
              <TextField
                label="取得原価合計（円換算後）任意"
                type="number"
                value={totalCost}
                onChange={(e) => setTotalCost(e.target.value)}
                inputProps={{ step: 1000 }}
                sx={{ flex: 1 }}
                helperText={totalCost ? `損益: ${formatCurrency(Number(totalValue || 0) - Number(totalCost))}` : ""}
              />
              {isUsd && (
                <TextField
                  label="USD/JPY レート"
                  type="number"
                  value={exchangeRate}
                  onChange={(e) => setExchangeRate(e.target.value)}
                  inputProps={{ step: 0.01 }}
                  sx={{ width: 160 }}
                  helperText="例: 159.51"
                />
              )}
            </Stack>
            <TextField
              label="メモ（任意）"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              multiline
              rows={2}
            />

            <Divider />

            {/* 個別明細 */}
            <Box>
              <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
                <Typography variant="subtitle2">
                  個別明細（任意）
                  {isUsd && (
                    <Typography component="span" variant="caption" color="text.secondary" sx={{ ml: 1 }}>
                      単価は USD、評価額・取得原価は JPY 換算後で入力してください
                    </Typography>
                  )}
                </Typography>
                <Stack direction="row" spacing={1}>
                  {holdings.length > 0 && (
                    <Button size="small" onClick={autoCalcTotal}>
                      合計を自動計算
                    </Button>
                  )}
                  <Button size="small" startIcon={<AddIcon />} onClick={handleAddHolding}>
                    明細追加
                  </Button>
                </Stack>
              </Stack>

              {holdings.length > 0 && (
                <Box sx={{ overflowX: "auto" }}>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>種別</TableCell>
                        <TableCell>ティッカー</TableCell>
                        <TableCell>銘柄・商品名</TableCell>
                        <TableCell>数量</TableCell>
                        <TableCell>{isUsd ? "単価(USD)" : "単価(円)"}</TableCell>
                        <TableCell>評価額(円換算後)</TableCell>
                        <TableCell>取得原価(円換算後)</TableCell>
                        {account?.trading_type === "margin" && <TableCell>建玉日</TableCell>}
                        <TableCell />
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {holdings.map((h, i) => (
                        <TableRow key={i}>
                          <TableCell sx={{ minWidth: 100 }}>
                            <TextField
                              select
                              size="small"
                              value={h.asset_type}
                              onChange={(e) => handleHoldingChange(i, "asset_type", e.target.value)}
                              fullWidth
                            >
                              {ASSET_TYPES.map((t) => (
                                <MenuItem key={t.value} value={t.value}>{t.label}</MenuItem>
                              ))}
                            </TextField>
                          </TableCell>
                          <TableCell sx={{ minWidth: 90 }}>
                            <TextField
                              size="small"
                              value={h.ticker_code}
                              onChange={(e) => handleHoldingChange(i, "ticker_code", e.target.value)}
                              placeholder={isUsd ? "AAPL" : "7203"}
                              fullWidth
                            />
                          </TableCell>
                          <TableCell sx={{ minWidth: 160 }}>
                            <TextField
                              size="small"
                              value={h.asset_name}
                              onChange={(e) => handleHoldingChange(i, "asset_name", e.target.value)}
                              placeholder={isUsd ? "Apple" : "トヨタ自動車"}
                              required
                              fullWidth
                            />
                          </TableCell>
                          <TableCell sx={{ minWidth: 80 }}>
                            <TextField
                              size="small"
                              type="number"
                              value={h.quantity}
                              onChange={(e) => handleHoldingChange(i, "quantity", e.target.value)}
                              fullWidth
                            />
                          </TableCell>
                          <TableCell sx={{ minWidth: 100 }}>
                            <TextField
                              size="small"
                              type="number"
                              value={h.unit_price}
                              onChange={(e) => handleHoldingChange(i, "unit_price", e.target.value)}
                              fullWidth
                            />
                          </TableCell>
                          <TableCell sx={{ minWidth: 120 }}>
                            <TextField
                              size="small"
                              type="number"
                              value={h.value_jpy}
                              onChange={(e) => handleHoldingChange(i, "value_jpy", e.target.value)}
                              required
                              fullWidth
                            />
                          </TableCell>
                          <TableCell sx={{ minWidth: 120 }}>
                            <TextField
                              size="small"
                              type="number"
                              value={h.cost_jpy}
                              onChange={(e) => handleHoldingChange(i, "cost_jpy", e.target.value)}
                              fullWidth
                            />
                          </TableCell>
                          {account?.trading_type === "margin" && (
                            <TableCell sx={{ minWidth: 140 }}>
                              <TextField
                                size="small"
                                type="date"
                                value={h.built_date}
                                onChange={(e) => handleHoldingChange(i, "built_date", e.target.value)}
                                fullWidth
                                InputLabelProps={{ shrink: true }}
                              />
                            </TableCell>
                          )}
                          <TableCell>
                            <IconButton size="small" color="error" onClick={() => handleRemoveHolding(i)}>
                              <DeleteIcon fontSize="small" />
                            </IconButton>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </Box>
              )}
            </Box>

            {/* 操作ボタン */}
            <Stack direction="row" spacing={2} justifyContent="flex-end">
              {existingSnap && (
                <Button color="error" onClick={handleDelete} disabled={deleteMutation.isPending}>
                  削除
                </Button>
              )}
              <Button
                variant="contained"
                startIcon={<SaveIcon />}
                onClick={handleSave}
                disabled={!totalValue || upsertMutation.isPending}
              >
                {existingSnap ? "更新" : "保存"}
              </Button>
            </Stack>
          </Stack>
        </CardContent>
      </Card>

      {/* スナップショット履歴 */}
      {snapshots.length > 0 && (
        <Box sx={{ mt: 3 }}>
          <Typography variant="subtitle2" gutterBottom>入力済み履歴</Typography>
          <Stack spacing={1}>
            {snapshots.slice(0, 12).map((s) => (
              <Card
                key={s.id}
                variant="outlined"
                sx={{
                  cursor: "pointer",
                  bgcolor: toMonthValue(s.snapshot_date) === selectedMonth ? "action.selected" : "inherit",
                }}
                onClick={() => setSelectedMonth(toMonthValue(s.snapshot_date))}
              >
                <CardContent sx={{ py: 1, "&:last-child": { pb: 1 } }}>
                  <Stack direction="row" justifyContent="space-between">
                    <Typography variant="body2">{s.snapshot_date}</Typography>
                    <Typography variant="body2" fontWeight="bold">
                      {formatCurrency(Number(s.total_value_jpy))}
                    </Typography>
                    {s.total_cost_jpy && (
                      <Typography
                        variant="body2"
                        color={
                          Number(s.total_value_jpy) >= Number(s.total_cost_jpy)
                            ? "success.main"
                            : "error.main"
                        }
                      >
                        {Number(s.total_value_jpy) >= Number(s.total_cost_jpy) ? "+" : ""}
                        {formatCurrency(Number(s.total_value_jpy) - Number(s.total_cost_jpy))}
                      </Typography>
                    )}
                  </Stack>
                </CardContent>
              </Card>
            ))}
          </Stack>
        </Box>
      )}
    </Box>
  );
}
