import { Box, Typography } from "@mui/material";
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  Bar,
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

export default function MacdChart({ series, syncId, height = 140 }: Props) {
  const data = series.map((s) => ({
    date: s.date,
    macd: num(s.macd),
    macd_signal: num(s.macd_signal),
    macd_hist: num(s.macd_hist),
  }));

  const labelMap: Record<string, string> = {
    macd: "MACD",
    macd_signal: "シグナル",
    macd_hist: "ヒストグラム",
  };

  return (
    <Box sx={{ width: "100%" }}>
      <Box sx={{ display: "flex", alignItems: "center", mb: 0.5 }}>
        <Typography variant="caption" color="text.secondary" fontWeight="bold">MACD</Typography>
        <IndicatorHelpTooltip title={HELP_TEXTS.macd} />
      </Box>
      <Box sx={{ height }}>
      <ResponsiveContainer>
        <ComposedChart data={data} margin={{ top: 5, right: 20, bottom: 5, left: 10 }} syncId={syncId}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 10 }}
            tickFormatter={(v: string) => v.slice(5)}
          />
          <YAxis
            tick={{ fontSize: 10 }}
            label={{ value: "MACD", angle: -90, position: "insideLeft", fontSize: 11 }}
          />
          <Tooltip
            formatter={(value, name) => [
              Number(value).toFixed(3),
              labelMap[String(name)] ?? String(name),
            ]}
          />
          <ReferenceLine y={0} stroke="#888" />
          <Bar dataKey="macd_hist" fill="#9e9e9e" opacity={0.6} />
          <Line
            type="monotone"
            dataKey="macd"
            stroke="#1565c0"
            strokeWidth={1.5}
            dot={false}
            isAnimationActive={false}
            connectNulls
          />
          <Line
            type="monotone"
            dataKey="macd_signal"
            stroke="#fb8c00"
            strokeWidth={1.5}
            dot={false}
            isAnimationActive={false}
            connectNulls
          />
        </ComposedChart>
      </ResponsiveContainer>
      </Box>
    </Box>
  );
}
