import { useState } from "react";
import { Box, Typography, ToggleButton, ToggleButtonGroup, Alert } from "@mui/material";
import LoadingSpinner from "@/components/common/LoadingSpinner";
import StockTechnicalChart from "./StockTechnicalChart";
import RsiChart from "./RsiChart";
import MacdChart from "./MacdChart";
import StochasticsChart from "./StochasticsChart";
import TechnicalIndicatorCards from "./TechnicalIndicatorCards";
import { useStockTechnicals } from "@/hooks/useStocks";
import type { TechnicalPeriod } from "@/types/technical";

interface Props {
  code: string;
  marketType?: string; // "US" ならドル建て表示
}

const PERIOD_OPTIONS: { value: TechnicalPeriod; label: string }[] = [
  { value: "1m", label: "1ヶ月" },
  { value: "3m", label: "3ヶ月" },
  { value: "6m", label: "6ヶ月" },
  { value: "1y", label: "1年" },
  { value: "all", label: "全期間" },
];

export default function TechnicalChartGroup({ code, marketType }: Props) {
  const [period, setPeriod] = useState<TechnicalPeriod>("1y");
  const { data, isLoading, isError } = useStockTechnicals(code, period);

  if (isLoading) {
    return (
      <Box sx={{ py: 4, display: "flex", justifyContent: "center" }}>
        <LoadingSpinner />
      </Box>
    );
  }

  if (isError || !data) {
    return (
      <Alert severity="error" sx={{ my: 2 }}>
        テクニカル指標の取得に失敗しました
      </Alert>
    );
  }

  if (data.series.length === 0) {
    return (
      <Typography color="text.secondary" sx={{ py: 4, textAlign: "center" }}>
        株価データがありません
      </Typography>
    );
  }

  const syncId = `stock-tech-${code}`;
  const latestClose = data.series[data.series.length - 1]?.close ?? null;

  return (
    <Box>
      {/* 期間切替 */}
      <Box sx={{ display: "flex", justifyContent: "flex-end", mb: 1 }}>
        <ToggleButtonGroup
          value={period}
          exclusive
          size="small"
          onChange={(_, v: TechnicalPeriod | null) => {
            if (v !== null) setPeriod(v);
          }}
        >
          {PERIOD_OPTIONS.map((opt) => (
            <ToggleButton key={opt.value} value={opt.value}>
              {opt.label}
            </ToggleButton>
          ))}
        </ToggleButtonGroup>
      </Box>

      {data.insufficient_data && (
        <Alert severity="info" sx={{ mb: 2 }}>
          200日移動平均の計算には 200日以上の株価データが必要です（現在 {data.data_points} 日分）。
          一部の指標が表示されない場合があります。
        </Alert>
      )}

      {/* カード */}
      {data.latest && (
        <TechnicalIndicatorCards
          latest={data.latest}
          currentClose={latestClose}
          atrApproximation={data.atr_approximation}
          marketType={marketType}
        />
      )}

      {/* チャート群（縦並び、syncId で X軸同期） */}
      <Box sx={{ mt: 3, display: "flex", flexDirection: "column", gap: 2 }}>
        <StockTechnicalChart series={data.series} syncId={syncId} height={320} />
        <RsiChart series={data.series} syncId={syncId} height={140} />
        <MacdChart series={data.series} syncId={syncId} height={140} />
        <StochasticsChart series={data.series} syncId={syncId} height={140} />
      </Box>
    </Box>
  );
}
