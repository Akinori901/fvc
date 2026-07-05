import { Box, CircularProgress, Alert, Typography } from "@mui/material";
import { useFxAnalysis } from "@/hooks/useFx";
import FxDashboard from "@/components/fx/FxDashboard";
import FxRateChart from "@/components/fx/FxRateChart";
import TechnicalIndicatorCards from "@/components/fx/TechnicalIndicatorCards";

export default function FxAnalysisPage() {
  const { data, isLoading, error } = useFxAnalysis();

  if (isLoading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", mt: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    const msg =
      error instanceof Error ? error.message : "FX分析データの取得に失敗しました";
    return (
      <Alert severity="warning" sx={{ mt: 2 }}>
        <Typography variant="body2">{msg}</Typography>
        <Typography variant="caption" color="text.secondary">
          FXデータが未同期の可能性があります。管理者に sync_fx_data コマンドの実行を依頼してください。
        </Typography>
      </Alert>
    );
  }

  if (!data) return null;

  return (
    <Box>
      <FxDashboard data={data} />
      <FxRateChart data={data.chart_data} />
      <TechnicalIndicatorCards
        technicals={data.technicals}
        currentRate={data.current_rate}
      />
    </Box>
  );
}
