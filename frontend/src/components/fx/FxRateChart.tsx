import { Box, Typography } from "@mui/material";
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
} from "recharts";
import type { FxChartDataPoint } from "@/types/fx";

interface Props {
  data: FxChartDataPoint[];
}

export default function FxRateChart({ data }: Props) {
  if (!data.length) return null;

  // 直近1年分にフィルタ
  const oneYearAgo = new Date();
  oneYearAgo.setFullYear(oneYearAgo.getFullYear() - 1);
  const filtered = data.filter((d) => new Date(d.date) >= oneYearAgo);

  const chartData = filtered.map((d) => ({
    date: d.date,
    rate: Number(d.rate),
    fair_value: d.fair_value ? Number(d.fair_value) : undefined,
    upper_1s: d.upper_1s ? Number(d.upper_1s) : undefined,
    lower_1s: d.lower_1s ? Number(d.lower_1s) : undefined,
    upper_2s: d.upper_2s ? Number(d.upper_2s) : undefined,
    lower_2s: d.lower_2s ? Number(d.lower_2s) : undefined,
  }));

  // Y軸の範囲を自動計算
  const allValues = chartData.flatMap((d) =>
    [d.rate, d.upper_2s, d.lower_2s].filter(
      (v): v is number => v !== undefined
    )
  );
  const yMin = Math.floor(Math.min(...allValues) - 2);
  const yMax = Math.ceil(Math.max(...allValues) + 2);

  return (
    <Box sx={{ mt: 3 }}>
      <Typography variant="h6" sx={{ mb: 2 }}>
        USD/JPY チャート（直近1年）
      </Typography>
      <Box sx={{ width: "100%", height: 400 }}>
        <ResponsiveContainer>
          <ComposedChart
            data={chartData}
            margin={{ top: 5, right: 30, left: 10, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 11 }}
              tickFormatter={(v: string) => v.slice(5)} // MM-DD
              interval={Math.floor(filtered.length / 8)}
            />
            <YAxis domain={[yMin, yMax]} tick={{ fontSize: 11 }} />
            <Tooltip
              formatter={(value, name) => [
                typeof value === "number" ? `¥${value.toFixed(2)}` : "-",
                String(name ?? ""),
              ]}
              labelFormatter={(label) => String(label)}
            />
            <Legend />

            {/* ±2σ バンド */}
            <Area
              dataKey="upper_2s"
              stroke="#90caf9"
              strokeWidth={1}
              strokeDasharray="4 3"
              fill="transparent"
              name="上限2σ"
              dot={false}
            />
            <Area
              dataKey="lower_2s"
              stroke="#90caf9"
              strokeWidth={1}
              strokeDasharray="4 3"
              fill="#e3f2fd"
              name="下限2σ"
              dot={false}
              fillOpacity={0.25}
            />

            {/* ±1σ バンド */}
            <Area
              dataKey="upper_1s"
              stroke="#42a5f5"
              strokeWidth={1.5}
              fill="transparent"
              name="上限1σ"
              dot={false}
            />
            <Area
              dataKey="lower_1s"
              stroke="#42a5f5"
              strokeWidth={1.5}
              fill="#bbdefb"
              name="下限1σ"
              dot={false}
              fillOpacity={0.3}
            />

            {/* 適正値ライン */}
            <Line
              type="monotone"
              dataKey="fair_value"
              stroke="#1976d2"
              strokeWidth={2}
              dot={false}
              name="適正値"
              strokeDasharray="5 5"
            />

            {/* 実際のレート */}
            <Line
              type="monotone"
              dataKey="rate"
              stroke="#d32f2f"
              strokeWidth={2}
              dot={false}
              name="USD/JPY"
            />
          </ComposedChart>
        </ResponsiveContainer>
      </Box>
    </Box>
  );
}
