import { Card, CardContent, Grid, Typography, Box, Chip } from "@mui/material";
import type {
  IndicatorLatest,
  RsiSignal,
  BbSignal,
  StochSignal,
  MacdCross,
  MomentumSignal,
} from "@/types/technical";
import IndicatorHelpTooltip, { HELP_TEXTS } from "./IndicatorHelpTooltip";

const RSI_LABELS: Record<RsiSignal, { label: string; color: "error" | "success" | "default" }> = {
  overbought: { label: "買われすぎ", color: "error" },
  oversold: { label: "売られすぎ", color: "success" },
  neutral: { label: "中立", color: "default" },
};

const BB_LABELS: Record<BbSignal, { label: string; color: "error" | "success" | "default" }> = {
  above_upper: { label: "上限突破", color: "error" },
  below_lower: { label: "下限割れ", color: "success" },
  inside: { label: "バンド内", color: "default" },
};

const STOCH_LABELS: Record<StochSignal, { label: string; color: "error" | "success" | "default" }> = {
  overbought: { label: "買われすぎ", color: "error" },
  oversold: { label: "売られすぎ", color: "success" },
  neutral: { label: "中立", color: "default" },
};

const MACD_LABELS: Record<MacdCross, { label: string; color: "success" | "error" | "default" }> = {
  golden: { label: "ゴールデンクロス", color: "success" },
  dead: { label: "デッドクロス", color: "error" },
  none: { label: "シグナルなし", color: "default" },
};

const MOMENTUM_LABELS: Record<MomentumSignal, { label: string; color: "success" | "error" | "warning" | "default" }> = {
  strong_up: { label: "強い上昇", color: "success" },
  up: { label: "上昇", color: "success" },
  flat: { label: "横ばい", color: "default" },
  down: { label: "下落", color: "warning" },
  strong_down: { label: "強い下落", color: "error" },
};

function fmtNum(v: string | null, fractionDigits = 2): string {
  if (v === null) return "—";
  const n = Number(v);
  if (Number.isNaN(n)) return "—";
  return n.toLocaleString(undefined, {
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  });
}

function fmtPct(v: string | null): string {
  if (v === null) return "—";
  const n = Number(v);
  if (Number.isNaN(n)) return "—";
  const sign = n >= 0 ? "+" : "";
  return `${sign}${n.toFixed(2)}%`;
}

interface Props {
  latest: IndicatorLatest;
  currentClose: string | null;
  atrApproximation: string;
  marketType?: string; // "US" ならドル建て表示
}

export default function TechnicalIndicatorCards({
  latest,
  currentClose,
  atrApproximation,
  marketType,
}: Props) {
  const sym = marketType === "US" ? "$" : "¥";
  return (
    <Box sx={{ mt: 2 }}>
      <Typography variant="h6" sx={{ mb: 1 }}>
        テクニカル指標
      </Typography>
      <Grid container spacing={1.5}>
        {/* MA */}
        <Grid size={{ xs: 12, sm: 6, md: 4 }}>
          <Card variant="outlined">
            <CardContent sx={{ py: 1.5, "&:last-child": { pb: 1.5 } }}>
              <Box sx={{ display: "flex", alignItems: "center" }}>
                <Typography variant="caption" color="text.secondary">
                  移動平均（25 / 75 / 200日）
                </Typography>
                <IndicatorHelpTooltip title={HELP_TEXTS.ma} />
              </Box>
              <Box sx={{ display: "flex", flexDirection: "column", gap: 0.3, mt: 0.5 }}>
                <Typography variant="body2">
                  25日: {sym}{fmtNum(latest.ma_25)} ({fmtPct(latest.ma_25_deviation_pct)})
                </Typography>
                <Typography variant="body2">
                  75日: {sym}{fmtNum(latest.ma_75)} ({fmtPct(latest.ma_75_deviation_pct)})
                </Typography>
                <Typography variant="body2">
                  200日: {sym}{fmtNum(latest.ma_200)} ({fmtPct(latest.ma_200_deviation_pct)})
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Bollinger */}
        <Grid size={{ xs: 12, sm: 6, md: 4 }}>
          <Card variant="outlined">
            <CardContent sx={{ py: 1.5, "&:last-child": { pb: 1.5 } }}>
              <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <Box sx={{ display: "flex", alignItems: "center" }}>
                  <Typography variant="caption" color="text.secondary">
                    ボリンジャーバンド (20, ±2σ)
                  </Typography>
                  <IndicatorHelpTooltip title={HELP_TEXTS.bb} />
                </Box>
                {latest.bb_signal && (
                  <Chip
                    label={BB_LABELS[latest.bb_signal].label}
                    color={BB_LABELS[latest.bb_signal].color}
                    size="small"
                  />
                )}
              </Box>
              <Box sx={{ display: "flex", flexDirection: "column", gap: 0.3, mt: 0.5 }}>
                <Typography variant="body2">
                  上: {sym}{fmtNum(latest.bb_upper)} / 中: {sym}{fmtNum(latest.bb_middle)} / 下: {sym}{fmtNum(latest.bb_lower)}
                </Typography>
                {latest.bb_position !== null && (
                  <Typography variant="caption" color="text.secondary">
                    %B: {fmtNum(latest.bb_position, 3)}
                  </Typography>
                )}
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* RSI */}
        <Grid size={{ xs: 6, sm: 4, md: 2 }}>
          <Card variant="outlined">
            <CardContent sx={{ py: 1.5, "&:last-child": { pb: 1.5 } }}>
              <Box sx={{ display: "flex", alignItems: "center" }}>
                <Typography variant="caption" color="text.secondary">
                  RSI (14)
                </Typography>
                <IndicatorHelpTooltip title={HELP_TEXTS.rsi} />
              </Box>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1, mt: 0.5 }}>
                <Typography variant="h6" fontWeight="bold">
                  {fmtNum(latest.rsi_14, 1)}
                </Typography>
              </Box>
              {latest.rsi_signal && (
                <Chip
                  label={RSI_LABELS[latest.rsi_signal].label}
                  color={RSI_LABELS[latest.rsi_signal].color}
                  size="small"
                />
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* MACD */}
        <Grid size={{ xs: 6, sm: 4, md: 2 }}>
          <Card variant="outlined">
            <CardContent sx={{ py: 1.5, "&:last-child": { pb: 1.5 } }}>
              <Box sx={{ display: "flex", alignItems: "center" }}>
                <Typography variant="caption" color="text.secondary">
                  MACD (12/26/9)
                </Typography>
                <IndicatorHelpTooltip title={HELP_TEXTS.macd} />
              </Box>
              <Typography variant="body2" sx={{ mt: 0.5 }}>
                MACD: {fmtNum(latest.macd, 3)}
              </Typography>
              <Typography variant="body2">
                Sig: {fmtNum(latest.macd_signal, 3)}
              </Typography>
              {latest.macd_cross && latest.macd_cross !== "none" && (
                <Chip
                  label={MACD_LABELS[latest.macd_cross].label}
                  color={MACD_LABELS[latest.macd_cross].color}
                  size="small"
                  sx={{ mt: 0.5 }}
                />
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Stochastics */}
        <Grid size={{ xs: 6, sm: 4, md: 2 }}>
          <Card variant="outlined">
            <CardContent sx={{ py: 1.5, "&:last-child": { pb: 1.5 } }}>
              <Box sx={{ display: "flex", alignItems: "center" }}>
                <Typography variant="caption" color="text.secondary">
                  Stoch (%K/%D)
                </Typography>
                <IndicatorHelpTooltip title={HELP_TEXTS.stoch} />
              </Box>
              <Typography variant="body2" sx={{ mt: 0.5 }}>
                %K: {fmtNum(latest.stoch_k, 1)}
              </Typography>
              <Typography variant="body2">
                %D: {fmtNum(latest.stoch_d, 1)}
              </Typography>
              {latest.stoch_signal && (
                <Chip
                  label={STOCH_LABELS[latest.stoch_signal].label}
                  color={STOCH_LABELS[latest.stoch_signal].color}
                  size="small"
                />
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* ATR */}
        <Grid size={{ xs: 6, sm: 4, md: 2 }}>
          <Card variant="outlined">
            <CardContent sx={{ py: 1.5, "&:last-child": { pb: 1.5 } }}>
              <Box sx={{ display: "flex", alignItems: "center" }}>
                <Typography variant="caption" color="text.secondary">
                  ATR (14)
                </Typography>
                <IndicatorHelpTooltip title={HELP_TEXTS.atr} />
              </Box>
              <Typography variant="h6" fontWeight="bold" sx={{ mt: 0.5 }}>
                {sym}{fmtNum(latest.atr_14)}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {fmtPct(latest.atr_pct)}
              </Typography>
              {atrApproximation === "close_to_close" && (
                <Typography variant="caption" color="text.secondary" sx={{ fontSize: 10 }}>
                  ※close近似
                </Typography>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Momentum */}
        <Grid size={{ xs: 6, sm: 4, md: 2 }}>
          <Card variant="outlined">
            <CardContent sx={{ py: 1.5, "&:last-child": { pb: 1.5 } }}>
              <Box sx={{ display: "flex", alignItems: "center" }}>
                <Typography variant="caption" color="text.secondary">
                  モメンタム (25日)
                </Typography>
                <IndicatorHelpTooltip title={HELP_TEXTS.momentum} />
              </Box>
              <Typography variant="h6" fontWeight="bold" sx={{ mt: 0.5 }}>
                {fmtPct(latest.momentum_25d_pct)}
              </Typography>
              {latest.momentum_signal && (
                <Chip
                  label={MOMENTUM_LABELS[latest.momentum_signal].label}
                  color={MOMENTUM_LABELS[latest.momentum_signal].color}
                  size="small"
                />
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* 現在値 + 参考 */}
        {currentClose && (
          <Grid size={{ xs: 12, sm: 12, md: 4 }}>
            <Card variant="outlined" sx={{ bgcolor: "action.hover" }}>
              <CardContent sx={{ py: 1.5, "&:last-child": { pb: 1.5 } }}>
                <Typography variant="caption" color="text.secondary">
                  最新終値
                </Typography>
                <Typography variant="h5" fontWeight="bold">
                  {sym}{fmtNum(currentClose)}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        )}
      </Grid>
    </Box>
  );
}
