import { useState, useEffect } from "react";
import {
  Box,
  Button,
  Card,
  CardContent,
  TextField,
  Typography,
  Stack,
  Alert,
} from "@mui/material";
import CalculateIcon from "@mui/icons-material/Calculate";
import StockSearchBar from "@/components/stock/StockSearchBar";
import type { Stock } from "@/types/stock";
import type { CalculateRequest } from "@/types/valuation";
import { useStocks, useStockFinancials, useStockPrices } from "@/hooks/useStocks";
import { formatDecimal, formatPercent } from "@/utils/format";

interface Props {
  onSubmit: (data: CalculateRequest) => void;
  isLoading: boolean;
}

export default function CalculationForm({ onSubmit, isLoading }: Props) {
  const { data: stocks } = useStocks();
  const [selectedStock, setSelectedStock] = useState<Stock | null>(null);
  const [growthRate, setGrowthRate] = useState("");
  const [currentPrice, setCurrentPrice] = useState("");

  const { data: financials } = useStockFinancials(selectedStock?.code ?? "");
  const { data: prices } = useStockPrices(selectedStock?.code ?? "", 1);

  // 銘柄選択時に最新データを自動入力
  useEffect(() => {
    const latest = prices?.[0];
    if (latest) {
      setCurrentPrice(latest.close_price);
    }
  }, [prices]);

  const latestFinancial = financials
    ?.sort((a, b) => b.fiscal_year - a.fiscal_year)[0];

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedStock) return;

    onSubmit({
      stock_code: selectedStock.code,
      growth_rate: parseFloat(growthRate) / 100,
      current_price: currentPrice ? parseFloat(currentPrice) : undefined,
    });
  };

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          算出パラメータ
        </Typography>

        <form onSubmit={handleSubmit}>
          <Stack spacing={3}>
            <StockSearchBar
              stocks={stocks ?? []}
              onSelect={setSelectedStock}
              label="銘柄を選択"
            />

            {selectedStock && latestFinancial && (
              <Alert severity="info" variant="outlined">
                <Typography variant="body2">
                  {selectedStock.code} - {selectedStock.name} / {latestFinancial.fiscal_year}年度
                </Typography>
                <Typography variant="body2">
                  BPS: {formatDecimal(latestFinancial.bps)}円 /
                  ROE: {formatPercent(latestFinancial.roe)} /
                  EPS: {latestFinancial.eps ? `${formatDecimal(latestFinancial.eps)}円` : "-"}
                </Typography>
              </Alert>
            )}

            <TextField
              label="期待成長率 (%)"
              type="number"
              value={growthRate}
              onChange={(e) => setGrowthRate(e.target.value)}
              required
              helperText="例: 5 = 5%成長"
              inputProps={{ step: "0.1" }}
            />

            <TextField
              label="現在の株価（円）"
              type="number"
              value={currentPrice}
              onChange={(e) => setCurrentPrice(e.target.value)}
              helperText="空欄の場合、最新の終値を使用します"
              inputProps={{ step: "1" }}
            />

            <Box>
              <Button
                type="submit"
                variant="contained"
                size="large"
                startIcon={<CalculateIcon />}
                disabled={!selectedStock || !growthRate || isLoading}
              >
                {isLoading ? "算出中..." : "適正株価を算出"}
              </Button>
            </Box>
          </Stack>
        </form>
      </CardContent>
    </Card>
  );
}
