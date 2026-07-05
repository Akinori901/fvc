import { useState, useMemo } from "react";
import {
  Box,
  Card,
  CardContent,
  Slider,
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
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import LoadingSpinner from "@/components/common/LoadingSpinner";
import ErrorAlert from "@/components/common/ErrorAlert";
import { usePortfolioSimulation } from "@/hooks/usePortfolioSimulation";
import { formatCurrency } from "@/utils/format";
import {
  ASSET_CLASS_COLORS,
  ASSET_CLASS_LABELS,
  GROWTH_RATE_SOURCE_LABELS,
} from "@/types/familyPortfolio";
import type { AssetClass, GrowthRateSource } from "@/types/familyPortfolio";

export default function SimulationTab() {
  const [years, setYears] = useState(10);
  const [fundRate, setFundRate] = useState(3);
  const { data, isLoading, error } = usePortfolioSimulation(
    years,
    "family",
    fundRate,
    true,
  );

  const chartData = useMemo(() => {
    if (!data) return [];
    return Array.from({ length: data.years + 1 }, (_, i) => {
      const point: Record<string, number | string> = { year: `${i}年後` };
      for (const [key, cat] of Object.entries(data.yearly_by_category)) {
        point[key] = Number(cat.values[i]);
      }
      return point;
    });
  }, [data]);

  const categories = useMemo(() => {
    if (!data) return [];
    return Object.entries(data.yearly_by_category).map(([key, cat]) => ({
      key,
      label: cat.label,
      color: ASSET_CLASS_COLORS[key as AssetClass] ?? "#546e7a",
    }));
  }, [data]);

  const totalCurrent = useMemo(
    () => (data ? Number(data.yearly_totals[0]) : 0),
    [data],
  );
  const totalProjected = useMemo(
    () => (data ? Number(data.yearly_totals[data.yearly_totals.length - 1]) : 0),
    [data],
  );
  const totalGain = totalProjected - totalCurrent;
  const totalGainPct =
    totalCurrent > 0 ? ((totalGain / totalCurrent) * 100).toFixed(1) : "0.0";

  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorAlert message={error.message} />;
  if (!data) return null;

  return (
    <Box>
      {/* 操作パネル */}
      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Stack direction={{ xs: "column", sm: "row" }} spacing={3} alignItems="center">
            <Box sx={{ minWidth: 120 }}>
              <TextField
                label="シミュレーション年数"
                type="number"
                size="small"
                value={years}
                onChange={(e) => {
                  const v = Math.min(Math.max(Number(e.target.value), 1), 30);
                  setYears(v);
                }}
                slotProps={{ htmlInput: { min: 1, max: 30 } }}
                sx={{ width: 160 }}
              />
            </Box>
            <Box sx={{ minWidth: 250, flex: 1 }}>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                投資信託 成長率: {fundRate.toFixed(1)}%
              </Typography>
              <Slider
                value={fundRate}
                onChange={(_, v) => setFundRate(v as number)}
                min={0}
                max={10}
                step={0.5}
                marks={[
                  { value: 0, label: "0%" },
                  { value: 5, label: "5%" },
                  { value: 10, label: "10%" },
                ]}
                valueLabelDisplay="auto"
                valueLabelFormat={(v) => `${v}%`}
              />
            </Box>
          </Stack>
        </CardContent>
      </Card>

      {/* サマリーカード */}
      <Stack direction="row" spacing={2} sx={{ mb: 2 }}>
        <Card sx={{ flex: 1 }}>
          <CardContent sx={{ py: 1.5, "&:last-child": { pb: 1.5 } }}>
            <Typography variant="body2" color="text.secondary">現在の総資産</Typography>
            <Typography variant="h6">{formatCurrency(totalCurrent)}</Typography>
          </CardContent>
        </Card>
        <Card sx={{ flex: 1 }}>
          <CardContent sx={{ py: 1.5, "&:last-child": { pb: 1.5 } }}>
            <Typography variant="body2" color="text.secondary">{years}年後の総資産</Typography>
            <Typography variant="h6">{formatCurrency(totalProjected)}</Typography>
          </CardContent>
        </Card>
        <Card sx={{ flex: 1 }}>
          <CardContent sx={{ py: 1.5, "&:last-child": { pb: 1.5 } }}>
            <Typography variant="body2" color="text.secondary">増加額（増加率）</Typography>
            <Typography
              variant="h6"
              color={totalGain >= 0 ? "success.main" : "error.main"}
            >
              {totalGain >= 0 ? "+" : ""}{formatCurrency(totalGain)}
              <Typography component="span" variant="body2" sx={{ ml: 0.5 }}>
                ({totalGainPct}%)
              </Typography>
            </Typography>
          </CardContent>
        </Card>
      </Stack>

      {/* 積み上げ面グラフ */}
      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="subtitle2" gutterBottom>
            資産推移シミュレーション
          </Typography>
          <ResponsiveContainer width="100%" height={350}>
            <AreaChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="year" />
              <YAxis
                tickFormatter={(v: number) =>
                  v >= 10_000_000 ? `${(v / 10_000_000).toFixed(0)}千万` :
                  v >= 10_000 ? `${(v / 10_000).toFixed(0)}万` :
                  String(v)
                }
              />
              <Tooltip
                formatter={(
                  value: number | string | undefined,
                  name: string | number | undefined,
                ): [string, string] => {
                  const numValue = typeof value === "number" ? value : Number(value ?? 0);
                  const strName = String(name ?? "");
                  const label = ASSET_CLASS_LABELS[strName as AssetClass] ?? strName;
                  return [formatCurrency(numValue), label];
                }}
              />
              <Legend
                formatter={(value: string) =>
                  ASSET_CLASS_LABELS[value as AssetClass] ?? value
                }
              />
              {categories.map((cat) => (
                <Area
                  key={cat.key}
                  type="monotone"
                  dataKey={cat.key}
                  stackId="1"
                  fill={cat.color}
                  stroke={cat.color}
                  fillOpacity={0.7}
                />
              ))}
            </AreaChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* 保有銘柄テーブル */}
      <Card>
        <CardContent>
          <Typography variant="subtitle2" gutterBottom>
            銘柄別シミュレーション
          </Typography>
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>銘柄</TableCell>
                  <TableCell>カテゴリ</TableCell>
                  <TableCell align="right">現在評価額</TableCell>
                  <TableCell align="right">成長率</TableCell>
                  <TableCell>ソース</TableCell>
                  <TableCell align="right">{years}年後評価額</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {data.holdings.map((h, i) => (
                  <TableRow key={`${h.ticker_code}-${h.asset_name}-${i}`}>
                    <TableCell>
                      {h.asset_name}
                      {h.ticker_code && (
                        <Typography
                          component="span"
                          variant="caption"
                          color="text.secondary"
                          sx={{ ml: 0.5 }}
                        >
                          ({h.ticker_code})
                        </Typography>
                      )}
                    </TableCell>
                    <TableCell>
                      {ASSET_CLASS_LABELS[h.category] ?? h.category_label}
                    </TableCell>
                    <TableCell align="right">
                      {formatCurrency(Number(h.current_value))}
                    </TableCell>
                    <TableCell align="right">
                      {Number(h.growth_rate_percent).toFixed(1)}%
                    </TableCell>
                    <TableCell>
                      {GROWTH_RATE_SOURCE_LABELS[h.growth_rate_source as GrowthRateSource] ??
                        h.growth_rate_source}
                    </TableCell>
                    <TableCell align="right">
                      {formatCurrency(Number(h.projected_value))}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>
    </Box>
  );
}
