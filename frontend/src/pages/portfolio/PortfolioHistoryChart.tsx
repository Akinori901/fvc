import { useState } from "react";
import {
  Box,
  Card,
  CardContent,
  Stack,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from "@mui/material";
import {
  AreaChart,
  Area,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import LoadingSpinner from "@/components/common/LoadingSpinner";
import { usePortfolioHistory } from "@/hooks/useFamilyPortfolio";
import { formatCurrency } from "@/utils/format";

const PERIODS = [
  { value: "6m", label: "6ヶ月" },
  { value: "1y", label: "1年" },
  { value: "3y", label: "3年" },
  { value: "all", label: "全期間" },
] as const;

export default function PortfolioHistoryChart() {
  const [period, setPeriod] = useState("1y");
  const { data, isLoading } = usePortfolioHistory(period);

  if (isLoading) return <LoadingSpinner />;
  if (!data || data.history.length === 0) return null;

  const showMembers = data.members.length > 1;

  // Recharts 用データ整形
  const chartData = data.history.map((point) => {
    const row: Record<string, string | number> = {
      date: point.date,
      total: point.total,
    };
    if (showMembers) {
      for (const member of data.members) {
        row[`member_${member.id}`] = point.members[String(member.id)] ?? 0;
      }
    }
    return row;
  });

  const formatYAxis = (value: number) => {
    if (value >= 100_000_000) return `${(value / 100_000_000).toFixed(1)}億`;
    if (value >= 10_000) return `${Math.round(value / 10_000)}万`;
    return String(value);
  };

  const formatTooltipValue = (value: number | undefined) => value != null ? formatCurrency(value) : "";
  const formatLabel = (label: unknown) => String(label ?? "");

  return (
    <Card>
      <CardContent>
        <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
          <Typography variant="subtitle2">資産推移</Typography>
          <ToggleButtonGroup
            value={period}
            exclusive
            onChange={(_, v) => v && setPeriod(v)}
            size="small"
          >
            {PERIODS.map((p) => (
              <ToggleButton key={p.value} value={p.value} sx={{ fontSize: 11, px: 1 }}>
                {p.label}
              </ToggleButton>
            ))}
          </ToggleButtonGroup>
        </Stack>

        <Box sx={{ width: "100%", height: { xs: 250, md: 350 } }}>
          <ResponsiveContainer width="100%" height="100%">
            {showMembers ? (
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 11 }}
                  tickFormatter={(v: string) => v.slice(5)}
                />
                <YAxis
                  tick={{ fontSize: 11 }}
                  tickFormatter={formatYAxis}
                  width={60}
                />
                <Tooltip
                  formatter={formatTooltipValue}
                  labelFormatter={formatLabel}
                />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="total"
                  name="合計"
                  stroke="#616161"
                  strokeWidth={2}
                  dot={false}
                />
                {data.members.map((member) => (
                  <Line
                    key={member.id}
                    type="monotone"
                    dataKey={`member_${member.id}`}
                    name={member.name}
                    stroke={member.color_code}
                    strokeWidth={1.5}
                    dot={false}
                  />
                ))}
              </LineChart>
            ) : (
              <AreaChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 11 }}
                  tickFormatter={(v: string) => v.slice(5)}
                />
                <YAxis
                  tick={{ fontSize: 11 }}
                  tickFormatter={formatYAxis}
                  width={60}
                />
                <Tooltip
                  formatter={formatTooltipValue}
                  labelFormatter={formatLabel}
                />
                <Area
                  type="monotone"
                  dataKey="total"
                  name="合計"
                  stroke="#1976d2"
                  fill="#1976d2"
                  fillOpacity={0.15}
                  strokeWidth={2}
                />
              </AreaChart>
            )}
          </ResponsiveContainer>
        </Box>
      </CardContent>
    </Card>
  );
}
