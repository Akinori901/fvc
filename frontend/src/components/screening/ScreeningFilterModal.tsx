import { useState, useEffect } from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Switch,
  FormControlLabel,
  Typography,
  Divider,
  Stack,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Autocomplete,
  Box,
} from "@mui/material";
import type { ScreeningFilters } from "@/types/screeningPreset";
import { DEFAULT_FILTERS } from "@/types/screeningPreset";
import IndicatorHelpTooltip, { HELP_TEXTS } from "@/components/stock/IndicatorHelpTooltip";

interface Props {
  open: boolean;
  onClose: () => void;
  filters: ScreeningFilters;
  onApply: (filters: ScreeningFilters) => void;
  sectors: string[];
}

export default function ScreeningFilterModal({ open, onClose, filters, onApply, sectors }: Props) {
  const [local, setLocal] = useState<ScreeningFilters>(filters);

  useEffect(() => {
    if (open) setLocal(filters);
  }, [open, filters]);

  const set = <K extends keyof ScreeningFilters>(key: K, value: ScreeningFilters[K]) =>
    setLocal((prev) => ({ ...prev, [key]: value }));

  const numOrNull = (v: string): number | null => {
    if (v === "") return null;
    const n = Number(v);
    return isNaN(n) ? null : n;
  };

  const intOrNull = (v: string): number | null => {
    if (v === "") return null;
    const n = parseInt(v, 10);
    return isNaN(n) ? null : n;
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>スクリーニングフィルター設定</DialogTitle>
      <DialogContent dividers>
        <Stack spacing={2.5}>
          {/* 基本 */}
          <Typography variant="subtitle2" color="primary">基本</Typography>
          <Autocomplete
            options={sectors}
            value={local.sector}
            onChange={(_, v) => set("sector", v)}
            renderInput={(params) => <TextField {...params} label="セクター" size="small" />}
            size="small"
          />
          <FormControlLabel
            control={<Switch checked={local.include_inactive} onChange={(e) => set("include_inactive", e.target.checked)} />}
            label="上場廃止を含む"
          />

          <Divider />
          <Typography variant="subtitle2" color="primary">バリュエーション</Typography>
          <TextField
            label="割安度(乖離率)下限 %"
            type="number"
            size="small"
            value={local.min_discount ?? ""}
            onChange={(e) => set("min_discount", numOrNull(e.target.value))}
          />
          <TextField
            label="ROE下限"
            type="number"
            size="small"
            value={local.min_roe ?? ""}
            onChange={(e) => set("min_roe", numOrNull(e.target.value))}
          />
          <FormControl size="small">
            <InputLabel>総合評価</InputLabel>
            <Select
              value={local.min_overall_score ?? ""}
              label="総合評価"
              onChange={(e) => set("min_overall_score", String(e.target.value) === "" ? null : Number(e.target.value))}
            >
              <MenuItem value="">すべて</MenuItem>
              <MenuItem value={-1}>レンジ中以上</MenuItem>
              <MenuItem value={2}>買い推奨以上</MenuItem>
              <MenuItem value={5}>超割安のみ</MenuItem>
            </Select>
          </FormControl>

          <Divider />
          <Typography variant="subtitle2" color="primary">成長</Typography>
          <TextField
            label="EPS成長率(前年比)最低 %"
            type="number"
            size="small"
            value={local.min_eps_growth_yoy != null ? (local.min_eps_growth_yoy * 100).toString() : ""}
            onChange={(e) => set("min_eps_growth_yoy", e.target.value === "" ? null : Number(e.target.value) / 100)}
          />
          <TextField
            label="EPS CAGR 3年最低 %"
            type="number"
            size="small"
            value={local.min_eps_cagr_3y != null ? (local.min_eps_cagr_3y * 100).toString() : ""}
            onChange={(e) => set("min_eps_cagr_3y", e.target.value === "" ? null : Number(e.target.value) / 100)}
          />
          <FormControlLabel
            control={
              <Switch
                checked={local.roe_trend === "improving"}
                onChange={(e) => set("roe_trend", e.target.checked ? "improving" : null)}
              />
            }
            label="ROE改善中のみ"
          />

          <Divider />
          <Typography variant="subtitle2" color="primary">信用</Typography>
          <TextField
            label="信売比率上限"
            type="number"
            size="small"
            value={local.max_sl_ratio ?? ""}
            onChange={(e) => set("max_sl_ratio", numOrNull(e.target.value))}
          />

          <Divider />
          <Typography variant="subtitle2" color="primary">テクニカル</Typography>
          <FormControl size="small">
            <InputLabel>モメンタム最低</InputLabel>
            <Select
              value={local.min_momentum_signal ?? ""}
              label="モメンタム最低"
              onChange={(e) => set("min_momentum_signal", (e.target.value || null) as ScreeningFilters["min_momentum_signal"])}
            >
              <MenuItem value="">指定なし</MenuItem>
              <MenuItem value="sell">売り以上</MenuItem>
              <MenuItem value="caution">注意以上</MenuItem>
              <MenuItem value="neutral">中立以上</MenuItem>
              <MenuItem value="buy">買い以上</MenuItem>
              <MenuItem value="strong_buy">強買いのみ</MenuItem>
            </Select>
          </FormControl>
          <FormControl size="small">
            <InputLabel>流動性最低</InputLabel>
            <Select
              value={local.min_liquidity_level ?? ""}
              label="流動性最低"
              onChange={(e) => set("min_liquidity_level", (e.target.value || null) as ScreeningFilters["min_liquidity_level"])}
            >
              <MenuItem value="">指定なし</MenuItem>
              <MenuItem value="very_low">極低以上</MenuItem>
              <MenuItem value="low">低以上</MenuItem>
              <MenuItem value="medium">中以上</MenuItem>
              <MenuItem value="high">高のみ</MenuItem>
            </Select>
          </FormControl>

          <Divider />
          <Typography variant="subtitle2" color="primary">買い時シグナル</Typography>
          <Typography variant="caption" color="text.secondary">
            テクニカル指標が買い時を示す銘柄に絞り込みます（複数選択で AND 条件）。
          </Typography>
          {(
            [
              ["ma_golden_cross_only", "MAゴールデンクロス（25日線が75日線を上抜け）", "maGoldenCross"],
              ["price_cross_ma25_only", "株価が25日線を上抜け", "priceCrossMa25"],
              ["price_cross_ma75_only", "株価が75日線を上抜け", "priceCrossMa75"],
              ["macd_golden_cross_only", "MACDゴールデンクロス", "macdGoldenCross"],
              ["rsi_rebound_only", "RSI売られ過ぎから反発", "rsiRebound"],
              ["pullback_buy_only", "押し目買い（上昇トレンド中の25日線反発）", "pullbackBuy"],
            ] as const
          ).map(([key, label, helpKey]) => (
            <FormControlLabel
              key={key}
              control={<Switch checked={local[key]} onChange={(e) => set(key, e.target.checked)} />}
              label={
                <Box sx={{ display: "flex", alignItems: "center" }}>
                  {label}
                  <IndicatorHelpTooltip title={HELP_TEXTS[helpKey]} />
                </Box>
              }
            />
          ))}

          <Divider />
          <Typography variant="subtitle2" color="primary">配当</Typography>
          <TextField
            label="配当利回り下限 %"
            type="number"
            size="small"
            value={local.min_dividend_yield ?? ""}
            onChange={(e) => set("min_dividend_yield", numOrNull(e.target.value))}
          />
          <TextField
            label="配当性向上限 %"
            type="number"
            size="small"
            value={local.max_payout_ratio ?? ""}
            onChange={(e) => set("max_payout_ratio", numOrNull(e.target.value))}
          />
          <TextField
            label="連続配当年数下限"
            type="number"
            size="small"
            value={local.min_consecutive_dividend_years ?? ""}
            onChange={(e) => set("min_consecutive_dividend_years", intOrNull(e.target.value))}
          />
          <TextField
            label="累進配当年数下限"
            type="number"
            size="small"
            value={local.min_progressive_dividend_years ?? ""}
            onChange={(e) => set("min_progressive_dividend_years", intOrNull(e.target.value))}
          />

          <Divider />
          <Typography variant="subtitle2" color="primary">FCF</Typography>
          <TextField
            label="FCF利回り下限 %"
            type="number"
            size="small"
            value={local.min_fcf_yield ?? ""}
            onChange={(e) => set("min_fcf_yield", numOrNull(e.target.value))}
          />

          <Divider />
          <Typography variant="subtitle2" color="primary">信用買残トレンド</Typography>
          <Typography variant="caption" color="text.secondary">
            信用買残は将来の売り圧力。決算利益の伸びと「買残の減少」を組み合わせると需給改善の候補を探せます。
          </Typography>
          <FormControl size="small" fullWidth>
            <InputLabel>信用買残の増減</InputLabel>
            <Select
              label="信用買残の増減"
              value={local.long_balance_trend ?? ""}
              onChange={(e) =>
                set("long_balance_trend", (e.target.value || null) as ScreeningFilters["long_balance_trend"])
              }
            >
              <MenuItem value="">指定なし</MenuItem>
              <MenuItem value="decreasing">減少している</MenuItem>
              <MenuItem value="increasing">増加している</MenuItem>
            </Select>
          </FormControl>
          <FormControl size="small" fullWidth disabled={local.long_balance_trend === null}>
            <InputLabel>評価期間</InputLabel>
            <Select
              label="評価期間"
              value={local.margin_trend_months}
              onChange={(e) => set("margin_trend_months", Number(e.target.value))}
            >
              {Array.from({ length: 12 }, (_, i) => i + 1).map((m) => (
                <MenuItem key={m} value={m}>{m}ヶ月</MenuItem>
              ))}
            </Select>
          </FormControl>
          <TextField
            label="変化率の閾値 %（例: 10 で 10%以上の増減）"
            type="number"
            size="small"
            disabled={local.long_balance_trend === null}
            value={local.margin_trend_threshold_pct ?? ""}
            onChange={(e) => set("margin_trend_threshold_pct", numOrNull(e.target.value))}
            helperText="未指定なら増減の方向のみで判定します"
          />

          <Divider />
          <Typography variant="subtitle2" color="primary">経営</Typography>
          <FormControlLabel
            control={<Switch checked={local.owner_managed_only} onChange={(e) => set("owner_managed_only", e.target.checked)} />}
            label="オーナー経営銘柄のみ"
          />
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={() => setLocal(DEFAULT_FILTERS)} color="inherit">リセット</Button>
        <Button onClick={onClose}>キャンセル</Button>
        <Button variant="contained" onClick={() => { onApply(local); onClose(); }}>適用</Button>
      </DialogActions>
    </Dialog>
  );
}
