import { Box, Typography } from "@mui/material";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
} from "recharts";
import type { IndicatorSeriesPoint } from "@/types/technical";
import IndicatorHelpTooltip, { HELP_TEXTS } from "./IndicatorHelpTooltip";

interface Props {
  series: IndicatorSeriesPoint[];
  syncId?: string;
  height?: number;
}

function num(v: string | null): number | null {
  if (v === null) return null;
  const n = parseFloat(v);
  return Number.isNaN(n) ? null : n;
}

export default function StochasticsChart({ series, syncId, height = 140 }: Props) {
  const data = series.map((s) => ({
    date: s.date,
    stoch_k: num(s.stoch_k),
    stoch_d: num(s.stoch_d),
  }));

  const labelMap: Record<string, string> = {
    stoch_k: "%K",
    stoch_d: "%D",
  };

  return (
    <Box sx={{ width: "100%" }}>
      <Box sx={{ display: "flex", alignItems: "center", mb: 0.5 }}>
        <Typography variant="caption" color="text.secondary" fontWeight="bold">ストキャスティクス</Typography>
        <IndicatorHelpTooltip title={HELP_TEXTS.stoch} />
      </Box>
      <Box sx={{ height }}>
      <ResponsiveContainer>
        <LineChart data={data} margin={{ top: 5, right: 20, bottom: 5, left: 10 }} syncId={syncId}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 10 }}
            tickFormatter={(v: string) => v.slice(5)}
          />
          <YAxis
            tick={{ fontSize: 10 }}
            domain={[0, 100]}
            ticks={[0, 20, 50, 80, 100]}
            label={{ value: "Stoch", angle: -90, position: "insideLeft", fontSize: 11 }}
          />
          <Tooltip
            formatter={(value, name) => [
              Number(value).toFixed(1),
              labelMap[String(name)] ?? String(name),
            ]}
          />
          <ReferenceLine y={80} stroke="#e57373" strokeDasharray="3 3" />
          <ReferenceLine y={20} stroke="#81c784" strokeDasharray="3 3" />
          <Line
            type="monotone"
            dataKey="stoch_k"
            stroke="#1565c0"
            strokeWidth={1.5}
            dot={false}
            isAnimationActive={false}
            connectNulls
          />
          <Line
            type="monotone"
            dataKey="stoch_d"
            stroke="#fb8c00"
            strokeWidth={1.5}
            dot={false}
            isAnimationActive={false}
            connectNulls
          />
        </LineChart>
      </ResponsiveContainer>
      </Box>
    </Box>
  );
}
