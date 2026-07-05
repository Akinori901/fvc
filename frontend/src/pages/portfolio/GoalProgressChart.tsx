import { useMemo, useState } from "react";
import { Box, Card, CardContent, Stack, ToggleButton, ToggleButtonGroup, Typography } from "@mui/material";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { formatCurrency } from "@/utils/format";
import type { GoalProgress } from "@/types/goals";

interface Props {
  progress: GoalProgress;
}

type RangeKey = "1y" | "5y" | "10y" | "past+1y" | "all";

const formatYAxis = (value: number) => {
  if (value >= 100_000_000) return `${(value / 100_000_000).toFixed(1)}億`;
  if (value >= 10_000) return `${Math.round(value / 10_000)}万`;
  return String(value);
};

const formatXLabel = (value: string) => {
  // YYYY-MM-DD → YY/MM
  const parts = value.split("-");
  const y = parts[0] ?? "";
  const m = parts[1] ?? "";
  return `${y.slice(2)}/${m}`;
};

/** YYYY-MM-DD の月初日付に nMonths を足す */
function shiftMonths(date: string, nMonths: number): string {
  const [y, m] = date.split("-").map(Number);
  if (!y || !m) return date;
  const total = y * 12 + (m - 1) + nMonths;
  const ny = Math.floor(total / 12);
  const nm = (total % 12) + 1;
  return `${String(ny).padStart(4, "0")}-${String(nm).padStart(2, "0")}-01`;
}

export default function GoalProgressChart({ progress }: Props) {
  const [range, setRange] = useState<RangeKey>("past+1y");

  const filteredChart = useMemo(() => {
    const chart = progress.chart;
    if (chart.length === 0) return chart;

    // 「今月」= actual が入っている最後の月。なければ chart の中央
    const lastActualIdx = (() => {
      for (let i = chart.length - 1; i >= 0; i--) {
        const item = chart[i];
        if (item && item.actual !== null) return i;
      }
      return -1;
    })();
    const todayDate = lastActualIdx >= 0 ? chart[lastActualIdx]!.date : chart[0]!.date;

    const earliest = chart[0]!.date;
    const latest = chart[chart.length - 1]!.date;

    let from: string;
    let to: string;
    switch (range) {
      case "1y":
        from = shiftMonths(todayDate, -12);
        to = todayDate;
        break;
      case "5y":
        from = todayDate;
        to = shiftMonths(todayDate, 60);
        break;
      case "10y":
        from = todayDate;
        to = shiftMonths(todayDate, 120);
        break;
      case "past+1y":
        from = earliest;
        to = shiftMonths(todayDate, 12);
        break;
      case "all":
      default:
        from = earliest;
        to = latest;
        break;
    }

    return chart.filter((p) => p.date >= from && p.date <= to);
  }, [progress.chart, range]);

  const handleRangeChange = (_: React.MouseEvent<HTMLElement>, value: RangeKey | null) => {
    if (value !== null) setRange(value);
  };

  return (
    <Card>
      <CardContent>
        <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" alignItems={{ xs: "flex-start", sm: "center" }} spacing={1} sx={{ mb: 1 }}>
          <Typography variant="subtitle1" fontWeight="bold">
            目標達成までの推移
          </Typography>
          <ToggleButtonGroup
            value={range}
            exclusive
            onChange={handleRangeChange}
            size="small"
            color="primary"
          >
            <ToggleButton value="1y">直近1年</ToggleButton>
            <ToggleButton value="5y">5年後</ToggleButton>
            <ToggleButton value="10y">10年後</ToggleButton>
            <ToggleButton value="past+1y">これまで+1年</ToggleButton>
            <ToggleButton value="all">全期間</ToggleButton>
          </ToggleButtonGroup>
        </Stack>
        <Box sx={{ width: "100%", height: 320 }}>
          <ResponsiveContainer>
            <LineChart data={filteredChart} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#33333322" />
              <XAxis
                dataKey="date"
                tickFormatter={formatXLabel}
                tick={{ fontSize: 11 }}
                interval="preserveStartEnd"
                minTickGap={20}
              />
              <YAxis tickFormatter={formatYAxis} tick={{ fontSize: 11 }} width={60} />
              <Tooltip
                formatter={(value, name) => {
                  const numValue = typeof value === "number" ? value : Number(value ?? 0);
                  const key = String(name);
                  const label =
                    key === "actual"
                      ? "実績"
                      : key === "ideal"
                        ? "理想"
                        : key === "projected"
                          ? "予測"
                          : key;
                  return [formatCurrency(numValue), label];
                }}
                labelFormatter={(label) => String(label ?? "")}
              />
              <Legend
                formatter={(value) =>
                  value === "actual" ? "実績" : value === "ideal" ? "理想（進捗線）" : value === "projected" ? "予測" : value
                }
                wrapperStyle={{ fontSize: 12 }}
              />
              <Line
                type="monotone"
                dataKey="actual"
                stroke="#2e7d32"
                strokeWidth={2.5}
                dot={false}
                connectNulls={false}
              />
              <Line
                type="monotone"
                dataKey="ideal"
                stroke="#1976d2"
                strokeWidth={1.5}
                strokeDasharray="6 4"
                dot={false}
              />
              <Line
                type="monotone"
                dataKey="projected"
                stroke="#ed6c02"
                strokeWidth={1.5}
                strokeDasharray="3 3"
                dot={false}
                connectNulls={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </Box>
      </CardContent>
    </Card>
  );
}
