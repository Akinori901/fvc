import { useState } from "react";
import {
  Alert,
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { manualFinancialApi, type ManualFinancialInput } from "@/api/manualFinancial";
import { formatCurrency, formatPercent, formatMultiple } from "@/utils/format";

interface Props {
  open: boolean;
  onClose: () => void;
  stockCode: string;
  stockName: string;
  defaultFiscalYear?: number;
}

const SOURCE_OPTIONS = [
  { value: "shikiho", label: "四季報" },
  { value: "minkabu", label: "ミンカブ" },
  { value: "irpage", label: "IR/会社HP" },
  { value: "other", label: "その他" },
];

export default function ManualFinancialInputModal({
  open,
  onClose,
  stockCode,
  stockName,
  defaultFiscalYear,
}: Props) {
  const currentYear = new Date().getFullYear();
  const [fiscalYear, setFiscalYear] = useState(defaultFiscalYear ?? currentYear - 1);
  const [bps, setBps] = useState("");
  const [eps, setEps] = useState("");
  const [epsForecast, setEpsForecast] = useState("");
  const [revenue, setRevenue] = useState("");
  const [operatingIncome, setOperatingIncome] = useState("");
  const [source, setSource] = useState("shikiho");
  const [note, setNote] = useState("");

  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (data: ManualFinancialInput) => manualFinancialApi.save(stockCode, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["stocks", stockCode, "financials"] });
      queryClient.invalidateQueries({ queryKey: ["stocks", stockCode, "financials", "manual"] });
      queryClient.invalidateQueries({ queryKey: ["screening"] });
      onClose();
    },
  });

  const handleSubmit = () => {
    const payload: ManualFinancialInput = {
      fiscal_year: fiscalYear,
      bps: bps !== "" ? Number(bps) : null,
      eps: eps !== "" ? Number(eps) : null,
      eps_forecast: epsForecast !== "" ? Number(epsForecast) : null,
      revenue: revenue !== "" ? Number(revenue) : null,
      operating_income: operatingIncome !== "" ? Number(operatingIncome) : null,
      source,
      note,
    };
    mutation.mutate(payload);
  };

  const calculation = mutation.data?.data.calculation;

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        財務データ手動入力
        <Typography variant="body2" color="text.secondary">
          {stockCode} {stockName}
        </Typography>
      </DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ mt: 1 }}>
          <Alert severity="info" sx={{ fontSize: "0.8rem" }}>
            J-Quants 同期時に同年度のデータが自動取得された場合、自動データが優先されます。
          </Alert>

          <TextField
            label="会計年度"
            type="number"
            size="small"
            value={fiscalYear}
            onChange={(e) => setFiscalYear(Number(e.target.value))}
            inputProps={{ min: 2000, max: currentYear }}
            fullWidth
          />

          <Stack direction="row" spacing={2}>
            <TextField
              label="BPS（円）"
              size="small"
              value={bps}
              onChange={(e) => setBps(e.target.value)}
              placeholder="例: 1584.90"
              fullWidth
            />
            <TextField
              label="EPS（円）"
              size="small"
              value={eps}
              onChange={(e) => setEps(e.target.value)}
              placeholder="例: 120.50"
              fullWidth
            />
          </Stack>

          <TextField
            label="予想EPS（円）"
            size="small"
            value={epsForecast}
            onChange={(e) => setEpsForecast(e.target.value)}
            placeholder="例: 135.00"
            fullWidth
          />

          <Stack direction="row" spacing={2}>
            <TextField
              label="売上高（百万円）"
              size="small"
              value={revenue}
              onChange={(e) => setRevenue(e.target.value)}
              placeholder="例: 1200000"
              fullWidth
            />
            <TextField
              label="営業利益（百万円）"
              size="small"
              value={operatingIncome}
              onChange={(e) => setOperatingIncome(e.target.value)}
              placeholder="例: 85000"
              fullWidth
            />
          </Stack>

          <FormControl size="small" fullWidth>
            <InputLabel>情報ソース</InputLabel>
            <Select value={source} label="情報ソース" onChange={(e) => setSource(e.target.value)}>
              {SOURCE_OPTIONS.map((opt) => (
                <MenuItem key={opt.value} value={opt.value}>
                  {opt.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <TextField
            label="メモ"
            size="small"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            multiline
            rows={2}
            fullWidth
          />

          {/* 即時計算結果 */}
          {mutation.isSuccess && calculation && (
            <Alert severity="success">
              <Typography variant="body2" fontWeight="bold" gutterBottom>
                計算結果（成長率 5% 仮定）
              </Typography>
              <Box sx={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 0.5 }}>
                <Typography variant="body2">適正PBR: {formatMultiple(Number(calculation.fair_pbr))}</Typography>
                <Typography variant="body2">適正株価: {formatCurrency(Number(calculation.fair_value))}</Typography>
                <Typography variant="body2">現在PBR: {formatMultiple(Number(calculation.current_pbr))}</Typography>
                <Typography
                  variant="body2"
                  color={Number(calculation.discount_rate) >= 0 ? "success.main" : "error.main"}
                  fontWeight="bold"
                >
                  乖離率: {formatPercent(Number(calculation.discount_rate))}
                </Typography>
              </Box>
            </Alert>
          )}

          {mutation.isSuccess && !calculation && (
            <Alert severity="warning">
              データを保存しましたが、株価データまたは条件が不足のため計算できませんでした。
            </Alert>
          )}

          {mutation.isError && (
            <Alert severity="error">保存に失敗しました。入力値を確認してください。</Alert>
          )}
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>キャンセル</Button>
        <Button
          variant="contained"
          onClick={handleSubmit}
          disabled={mutation.isPending}
        >
          {mutation.isPending ? "保存中..." : "保存・計算"}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
