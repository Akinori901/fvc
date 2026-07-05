import { useState } from "react";
import {
  Box,
  Typography,
  Alert,
  Stack,
  Card,
  CardContent,
  Button,
  Divider,
  Chip,
} from "@mui/material";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import CalculationForm from "@/components/valuation/CalculationForm";
import ResultSummary from "@/components/valuation/ResultSummary";
import PriceRangeBar from "@/components/valuation/PriceRangeBar";
import StockSearchBar from "@/components/stock/StockSearchBar";
import { useCalculateFairValue, useReverseCalculate } from "@/hooks/useValuations";
import { useStocks } from "@/hooks/useStocks";
import { formatPercent, formatMultiple } from "@/utils/format";
import type { ValuationResult, ImpliedGrowthResult } from "@/types/valuation";
import type { Stock } from "@/types/stock";

export default function CalculatePage() {
  const mutation = useCalculateFairValue();
  const reverseMutation = useReverseCalculate();
  const { data: stocks = [] } = useStocks();

  const [result, setResult] = useState<ValuationResult | null>(null);
  const [reverseStock, setReverseStock] = useState<Stock | null>(null);
  const [reverseResult, setReverseResult] = useState<ImpliedGrowthResult | null>(null);

  const handleReverseCalculate = () => {
    if (!reverseStock) return;
    reverseMutation.mutate(
      { stock_code: reverseStock.code },
      { onSuccess: (res) => setReverseResult(res) }
    );
  };

  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        適正株価算出
      </Typography>

      <Stack spacing={3}>
        <CalculationForm
          onSubmit={(data) => {
            mutation.mutate(data, {
              onSuccess: (res) => setResult(res),
            });
          }}
          isLoading={mutation.isPending}
        />

        {mutation.isError && (
          <Alert severity="error">
            {(mutation.error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
              "算出に失敗しました。パラメータを確認してください。"}
          </Alert>
        )}

        {result && (
          <>
            <ResultSummary result={result} />
            <PriceRangeBar
              fairValue={parseFloat(result.fair_value)}
              currentPrice={parseFloat(result.current_price)}
            />
          </>
        )}

        <Divider />

        {/* 市場織り込み成長率 逆算パネル */}
        <Card variant="outlined">
          <CardContent>
            <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 2 }}>
              <TrendingUpIcon color="primary" />
              <Typography variant="h6">市場織り込み成長率を逆算</Typography>
            </Stack>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              現在の株価から、市場が期待している永続成長率を逆算します。
              成長率を入力せず「市場は何%を織り込んでいるか」を知りたい場合に使います。
            </Typography>

            <Stack direction="row" spacing={2} alignItems="center">
              <StockSearchBar
                stocks={stocks}
                onSelect={(s) => {
                  setReverseStock(s);
                  setReverseResult(null);
                }}
                label="銘柄を選択"
              />
              <Button
                variant="contained"
                onClick={handleReverseCalculate}
                disabled={!reverseStock || reverseMutation.isPending}
              >
                逆算する
              </Button>
            </Stack>

            {reverseMutation.isError && (
              <Alert severity="error" sx={{ mt: 2 }}>
                {(reverseMutation.error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
                  "逆算に失敗しました。財務・株価データを同期してください。"}
              </Alert>
            )}

            {reverseResult && (
              <Stack spacing={1} sx={{ mt: 3 }}>
                <Typography variant="subtitle1" fontWeight="bold">
                  {reverseResult.stock_name}（{reverseResult.stock_code}）
                </Typography>

                <Stack direction="row" spacing={3} flexWrap="wrap">
                  <Box>
                    <Typography variant="body2" color="text.secondary">
                      市場が織り込む成長率
                    </Typography>
                    <Stack direction="row" spacing={1} alignItems="center">
                      <Typography variant="h5" fontWeight="bold" color="primary">
                        {formatPercent(reverseResult.implied_growth_rate)}
                      </Typography>
                      <Chip
                        label={reverseResult.growth_rate_label}
                        size="small"
                        color="primary"
                        variant="outlined"
                      />
                    </Stack>
                  </Box>
                  <Box>
                    <Typography variant="body2" color="text.secondary">
                      現在PBR
                    </Typography>
                    <Typography variant="body1">
                      {formatMultiple(reverseResult.current_pbr)}
                    </Typography>
                  </Box>
                  <Box>
                    <Typography variant="body2" color="text.secondary">
                      ROE
                    </Typography>
                    <Typography variant="body1">
                      {formatPercent(reverseResult.roe)}
                    </Typography>
                  </Box>
                  <Box>
                    <Typography variant="body2" color="text.secondary">
                      資本コスト
                    </Typography>
                    <Typography variant="body1">
                      {formatPercent(reverseResult.cost_of_capital)}
                    </Typography>
                  </Box>
                </Stack>
              </Stack>
            )}
          </CardContent>
        </Card>
      </Stack>
    </Box>
  );
}
