import { Box } from "@mui/material";
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";
import type { IndicatorSeriesPoint } from "@/types/technical";

interface Props {
  series: IndicatorSeriesPoint[];
  syncId?: string;
  height?: number;
}

interface ChartPoint {
  date: string;
  close: number;
  ma_25: number | null;
  ma_75: number | null;
  ma_200: number | null;
  bb_upper: number | null;
  bb_middle: number | null;
  bb_lower: number | null;
}

function num(v: string | null): number | null {
  if (v === null) return null;
  const n = parseFloat(v);
  return Number.isNaN(n) ? null : n;
}

const labelMap: Record<string, string> = {
  close: "終値",
  ma_25: "25日MA",
  ma_75: "75日MA",
  ma_200: "200日MA",
  bb_upper: "BB上限",
  bb_middle: "BB中央",
  bb_lower: "BB下限",
};

export default function StockTechnicalChart({ series, syncId, height = 320 }: Props) {
  const data: ChartPoint[] = series.map((s) => ({
    date: s.date,
    close: parseFloat(s.close),
    ma_25: num(s.ma_25),
    ma_75: num(s.ma_75),
    ma_200: num(s.ma_200),
    bb_upper: num(s.bb_upper),
    bb_middle: num(s.bb_middle),
    bb_lower: num(s.bb_lower),
  }));

  return (
    <Box sx={{ width: "100%", height }}>
      <ResponsiveContainer>
        <ComposedChart data={data} margin={{ top: 5, right: 20, bottom: 5, left: 10 }} syncId={syncId}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 11 }}
            tickFormatter={(v: string) => v.slice(5)}
          />
          <YAxis
            tick={{ fontSize: 11 }}
            tickFormatter={(v: number) => v.toLocaleString()}
            domain={["auto", "auto"]}
          />
          <Tooltip
            formatter={(value, name) => {
              const numValue = Number(value);
              const label = labelMap[String(name)] ?? String(name);
              return [`${numValue.toLocaleString()}円`, label];
            }}
          />
          <Legend
            verticalAlign="top"
            height={28}
            formatter={(value) => labelMap[String(value)] ?? String(value)}
          />

          <Area
            type="monotone"
            dataKey="bb_upper"
            stroke="#90caf9"
            strokeDasharray="3 3"
            fill="transparent"
            dot={false}
            isAnimationActive={false}
            connectNulls
          />
          <Area
            type="monotone"
            dataKey="bb_lower"
            stroke="#90caf9"
            strokeDasharray="3 3"
            fill="#e3f2fd"
            fillOpacity={0.3}
            dot={false}
            isAnimationActive={false}
            connectNulls
          />

          <Line
            type="monotone"
            dataKey="ma_25"
            stroke="#fb8c00"
            strokeWidth={1.5}
            dot={false}
            isAnimationActive={false}
            connectNulls
          />
          <Line
            type="monotone"
            dataKey="ma_75"
            stroke="#43a047"
            strokeWidth={1.5}
            dot={false}
            isAnimationActive={false}
            connectNulls
          />
          <Line
            type="monotone"
            dataKey="ma_200"
            stroke="#8e24aa"
            strokeWidth={1.5}
            strokeDasharray="6 3"
            dot={false}
            isAnimationActive={false}
            connectNulls
          />

          <Line
            type="monotone"
            dataKey="close"
            stroke="#1565c0"
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </Box>
  );
}
