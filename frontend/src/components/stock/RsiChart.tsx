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

export default function RsiChart({ series, syncId, height = 140 }: Props) {
  const data = series.map((s) => ({
    date: s.date,
    rsi_14: s.rsi_14 !== null ? parseFloat(s.rsi_14) : null,
  }));

  return (
    <Box sx={{ width: "100%" }}>
      <Box sx={{ display: "flex", alignItems: "center", mb: 0.5 }}>
        <Typography variant="caption" color="text.secondary" fontWeight="bold">RSI</Typography>
        <IndicatorHelpTooltip title={HELP_TEXTS.rsi} />
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
            ticks={[0, 30, 50, 70, 100]}
            label={{ value: "RSI(14)", angle: -90, position: "insideLeft", fontSize: 11 }}
          />
          <Tooltip
            formatter={(value) => [Number(value).toFixed(1), "RSI"]}
          />
          <ReferenceLine y={70} stroke="#e57373" strokeDasharray="3 3" />
          <ReferenceLine y={30} stroke="#81c784" strokeDasharray="3 3" />
          <Line
            type="monotone"
            dataKey="rsi_14"
            stroke="#7b1fa2"
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
