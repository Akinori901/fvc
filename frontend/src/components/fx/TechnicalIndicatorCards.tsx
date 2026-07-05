import { Card, CardContent, Grid, Typography, Box, Chip } from "@mui/material";
import type { FxTechnicals } from "@/types/fx";
import IndicatorHelpTooltip, { HELP_TEXTS } from "@/components/stock/IndicatorHelpTooltip";

function getRsiColor(rsi: number): "error" | "warning" | "success" | "default" {
  if (rsi >= 70) return "error"; // 買われすぎ
  if (rsi >= 60) return "warning";
  if (rsi <= 30) return "success"; // 売られすぎ
  if (rsi <= 40) return "warning";
  return "default";
}

function getRsiLabel(rsi: number): string {
  if (rsi >= 70) return "買われすぎ";
  if (rsi <= 30) return "売られすぎ";
  return "中立";
}

interface Props {
  technicals: FxTechnicals;
  currentRate: string;
}

export default function TechnicalIndicatorCards({
  technicals,
  currentRate,
}: Props) {
  const rate = Number(currentRate);

  return (
    <Box sx={{ mt: 3 }}>
      <Typography variant="h6" sx={{ mb: 2 }}>
        テクニカル指標
      </Typography>
      <Grid container spacing={2}>
        {/* RSI */}
        {technicals.rsi_14 && (
          <Grid size={{ xs: 6, sm: 4, md: 3 }}>
            <Card variant="outlined">
              <CardContent sx={{ py: 1.5, "&:last-child": { pb: 1.5 } }}>
                <Box sx={{ display: "flex", alignItems: "center" }}>
                  <Typography variant="caption" color="text.secondary">
                    RSI (14)
                  </Typography>
                  <IndicatorHelpTooltip title={HELP_TEXTS.rsi} />
                </Box>
                <Box
                  sx={{ display: "flex", alignItems: "center", gap: 1, mt: 0.5 }}
                >
                  <Typography variant="h6" fontWeight="bold">
                    {Number(technicals.rsi_14).toFixed(1)}
                  </Typography>
                  <Chip
                    label={getRsiLabel(Number(technicals.rsi_14))}
                    color={getRsiColor(Number(technicals.rsi_14))}
                    size="small"
                  />
                </Box>
              </CardContent>
            </Card>
          </Grid>
        )}

        {/* ボリンジャーバンド */}
        {technicals.bb_upper && technicals.bb_lower && (
          <Grid size={{ xs: 6, sm: 4, md: 3 }}>
            <Card variant="outlined">
              <CardContent sx={{ py: 1.5, "&:last-child": { pb: 1.5 } }}>
                <Box sx={{ display: "flex", alignItems: "center" }}>
                  <Typography variant="caption" color="text.secondary">
                    ボリンジャーバンド (20,2σ)
                  </Typography>
                  <IndicatorHelpTooltip title={HELP_TEXTS.bb} />
                </Box>
                <Typography variant="body2">
                  上限: ¥{Number(technicals.bb_upper).toFixed(2)}
                </Typography>
                <Typography variant="body2">
                  中央: ¥{Number(technicals.bb_middle).toFixed(2)}
                </Typography>
                <Typography variant="body2">
                  下限: ¥{Number(technicals.bb_lower).toFixed(2)}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        )}

        {/* 200日移動平均 */}
        {technicals.ma_200 && (
          <Grid size={{ xs: 6, sm: 4, md: 3 }}>
            <Card variant="outlined">
              <CardContent sx={{ py: 1.5, "&:last-child": { pb: 1.5 } }}>
                <Box sx={{ display: "flex", alignItems: "center" }}>
                  <Typography variant="caption" color="text.secondary">
                    200日移動平均
                  </Typography>
                  <IndicatorHelpTooltip title={HELP_TEXTS.ma} />
                </Box>
                <Typography variant="h6" fontWeight="bold">
                  ¥{Number(technicals.ma_200).toFixed(2)}
                </Typography>
                {technicals.ma_200_deviation && (
                  <Typography
                    variant="body2"
                    color={
                      rate > Number(technicals.ma_200)
                        ? "error.main"
                        : "success.main"
                    }
                  >
                    乖離率:{" "}
                    {Number(technicals.ma_200_deviation) >= 0 ? "+" : ""}
                    {Number(technicals.ma_200_deviation).toFixed(1)}%
                  </Typography>
                )}
              </CardContent>
            </Card>
          </Grid>
        )}
      </Grid>
    </Box>
  );
}
