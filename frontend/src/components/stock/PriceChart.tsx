import { Box, Typography } from "@mui/material";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";
import type { StockPrice } from "@/types/stock";

interface Props {
  prices: StockPrice[];
}

export default function PriceChart({ prices }: Props) {
  if (prices.length === 0) {
    return (
      <Typography color="text.secondary" sx={{ py: 4, textAlign: "center" }}>
        株価データがありません
      </Typography>
    );
  }

  const data = [...prices]
    .sort((a, b) => a.date.localeCompare(b.date))
    .map((p) => ({
      date: p.date,
      price: parseFloat(p.close_price),
    }));

  return (
    <Box sx={{ width: "100%", height: 350 }}>
      <ResponsiveContainer>
        <LineChart data={data} margin={{ top: 5, right: 20, bottom: 5, left: 10 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 12 }}
            tickFormatter={(v: string) => v.slice(5)}
          />
          <YAxis
            tick={{ fontSize: 12 }}
            tickFormatter={(v: number) => v.toLocaleString()}
            domain={["auto", "auto"]}
          />
          <Tooltip
            formatter={(value) => [
              `${Number(value).toLocaleString()}円`,
              "終値",
            ]}
          />
          <Line
            type="monotone"
            dataKey="price"
            stroke="#1565c0"
            dot={false}
            strokeWidth={1.5}
          />
        </LineChart>
      </ResponsiveContainer>
    </Box>
  );
}
