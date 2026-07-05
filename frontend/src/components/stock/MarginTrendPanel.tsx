import { Box, Card, CardContent, Stack, Typography, Alert } from "@mui/material";
import FinancialTermHelp from "@/components/common/FinancialTermHelp";
import {
  ResponsiveContainer,
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";
import { useQuery } from "@tanstack/react-query";
import { marginApi, type MarginBalanceRecord } from "@/api/margin";

interface Props {
  stockCode: string;
}

function detectSignals(history: MarginBalanceRecord[]) {
  if (history.length < 4) return [];

  const signals: { type: "positive" | "negative" | "neutral"; message: string }[] = [];
  const latest = history[0] as MarginBalanceRecord;
  const fourWeeksAgo = history[3] as MarginBalanceRecord;

  if (latest.short_balance != null && fourWeeksAgo.short_balance != null && fourWeeksAgo.short_balance > 0) {
    const changeRate = (latest.short_balance - fourWeeksAgo.short_balance) / fourWeeksAgo.short_balance;
    if (changeRate <= -0.2) {
      signals.push({ type: "positive", message: `売残が4週で${Math.abs(changeRate * 100).toFixed(0)}%減少（ショートカバーの兆候）` });
    } else if (changeRate >= 0.2) {
      signals.push({ type: "negative", message: `売残が4週で${(changeRate * 100).toFixed(0)}%増加（空売り増加）` });
    }
  }

  if (latest.long_balance != null && fourWeeksAgo.long_balance != null && fourWeeksAgo.long_balance > 0) {
    const changeRate = (latest.long_balance - fourWeeksAgo.long_balance) / fourWeeksAgo.long_balance;
    if (changeRate <= -0.2) {
      signals.push({ type: "negative", message: `買残が4週で${Math.abs(changeRate * 100).toFixed(0)}%減少（売り圧力）` });
    } else if (changeRate >= 0.2) {
      signals.push({ type: "positive", message: `買残が4週で${(changeRate * 100).toFixed(0)}%増加（新規買い参入）` });
    }
  }

  // 売残の連続減少
  let consecutiveDecrease = 0;
  for (let i = 0; i < history.length - 1; i++) {
    const cur = history[i]?.short_balance;
    const prev = history[i + 1]?.short_balance;
    if (cur != null && prev != null && cur < prev) {
      consecutiveDecrease++;
    } else {
      break;
    }
  }
  if (consecutiveDecrease >= 4) {
    signals.push({ type: "positive", message: `売残が${consecutiveDecrease}週連続で減少中` });
  }

  // SL比率の転換
  if (history.length >= 2) {
    const currentSl = latest.sl_ratio != null ? Number(latest.sl_ratio) : null;
    const prev = history[1];
    const prevSl = prev?.sl_ratio != null ? Number(prev.sl_ratio) : null;
    if (currentSl != null && prevSl != null) {
      if (prevSl >= 1.0 && currentSl < 1.0) {
        signals.push({ type: "positive", message: "SL比率が1.0未満に転換（需給改善）" });
      } else if (prevSl < 1.0 && currentSl >= 1.0) {
        signals.push({ type: "negative", message: "SL比率が1.0以上に転換（需給悪化）" });
      }
    }
  }

  return signals;
}

export default function MarginTrendPanel({ stockCode }: Props) {
  const { data: marginData, isLoading } = useQuery({
    queryKey: ["stockMargin", stockCode],
    queryFn: () => marginApi.getStockMargin(stockCode).then((r) => r.data),
    enabled: !!stockCode,
  });

  if (isLoading) return null;

  if (!marginData?.latest) {
    return (
      <Typography color="text.secondary" sx={{ py: 4, textAlign: "center" }}>
        信用残高データがありません
      </Typography>
    );
  }

  const { latest, history } = marginData;
  const signals = detectSignals(history);

  const chartData = [...history]
    .reverse()
    .map((r) => ({
      date: r.date,
      long: r.long_balance,
      short: r.short_balance,
      slRatio: r.sl_ratio != null ? Number(r.sl_ratio) : null,
    }));

  const formatUnit = (val: number) => {
    if (Math.abs(val) >= 10000) return `${(val / 10000).toFixed(1)}万`;
    return val.toLocaleString();
  };

  return (
    <Stack spacing={2}>
      {/* チャート */}
      {chartData.length > 1 && (
        <Box sx={{ width: "100%", height: 350 }}>
          <ResponsiveContainer>
            <ComposedChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 10 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 11 }}
                tickFormatter={(v: string) => v.slice(5)}
              />
              <YAxis
                yAxisId="balance"
                tick={{ fontSize: 11 }}
                tickFormatter={(v: number) => formatUnit(v)}
              />
              <YAxis
                yAxisId="ratio"
                orientation="right"
                tick={{ fontSize: 11 }}
                tickFormatter={(v: number) => `${v.toFixed(1)}`}
                domain={[0, "auto"]}
              />
              <Tooltip
                /* eslint-disable @typescript-eslint/no-explicit-any */
                formatter={((value: number, name: string) => {
                  if (name === "slRatio") return [`${value.toFixed(2)}倍`, "SL比率"];
                  const label = name === "long" ? "買残" : "売残";
                  return [`${formatUnit(value)}株`, label];
                }) as any}
                /* eslint-enable @typescript-eslint/no-explicit-any */
                labelFormatter={(label) => String(label)}
              />
              <Legend
                formatter={(value: string) =>
                  value === "long" ? "信用買残" : value === "short" ? "信用売残" : "SL比率"
                }
              />
              <Bar yAxisId="balance" dataKey="long" fill="#42a5f5" opacity={0.7} name="long" />
              <Bar yAxisId="balance" dataKey="short" fill="#ef5350" opacity={0.7} name="short" />
              <Line
                yAxisId="ratio"
                type="monotone"
                dataKey="slRatio"
                stroke="#ff9800"
                strokeWidth={2}
                dot={{ r: 3 }}
                name="slRatio"
                connectNulls
              />
            </ComposedChart>
          </ResponsiveContainer>
        </Box>
      )}

      {/* 最新値サマリー */}
      <Card variant="outlined">
        <CardContent>
          <Typography variant="subtitle2" color="text.secondary" gutterBottom>
            最新データ ({latest.date})
          </Typography>
          <Box sx={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 2 }}>
            <Box>
              <Stack direction="row" alignItems="center" spacing={0.25}>
                <Typography variant="caption" color="text.secondary">信用買残</Typography>
                <FinancialTermHelp termKey="long_balance" />
              </Stack>
              <Typography variant="body1" fontWeight="bold">
                {latest.long_balance != null
                  ? `${formatUnit(latest.long_balance)}株`
                  : "-"}
                {latest.long_balance_change != null && (
                  <Typography
                    component="span"
                    variant="caption"
                    color={latest.long_balance_change >= 0 ? "success.main" : "error.main"}
                    sx={{ ml: 0.5 }}
                  >
                    ({latest.long_balance_change >= 0 ? "+" : ""}
                    {formatUnit(latest.long_balance_change)}株)
                  </Typography>
                )}
              </Typography>
            </Box>
            <Box>
              <Stack direction="row" alignItems="center" spacing={0.25}>
                <Typography variant="caption" color="text.secondary">信用売残</Typography>
                <FinancialTermHelp termKey="short_balance" />
              </Stack>
              <Typography variant="body1" fontWeight="bold">
                {latest.short_balance != null
                  ? `${formatUnit(latest.short_balance)}株`
                  : "-"}
                {latest.short_balance_change != null && (
                  <Typography
                    component="span"
                    variant="caption"
                    color={latest.short_balance_change <= 0 ? "success.main" : "error.main"}
                    sx={{ ml: 0.5 }}
                  >
                    ({latest.short_balance_change >= 0 ? "+" : ""}
                    {formatUnit(latest.short_balance_change)}株)
                  </Typography>
                )}
              </Typography>
            </Box>
            <Box>
              <Stack direction="row" alignItems="center" spacing={0.25}>
                <Typography variant="caption" color="text.secondary">信売比率</Typography>
                <FinancialTermHelp termKey="margin_sl_ratio" />
              </Stack>
              {(() => {
                const ratio = latest.sl_ratio != null ? Number(latest.sl_ratio) : null;
                const color = ratio == null ? "text.primary"
                  : ratio >= 2.0 ? "error.main"
                  : ratio >= 1.0 ? "warning.main"
                  : "success.main";
                const label = ratio == null ? "-"
                  : ratio >= 2.0 ? `${ratio.toFixed(2)}倍 空売り超過`
                  : ratio >= 1.0 ? `${ratio.toFixed(2)}倍 やや売り優勢`
                  : `${ratio.toFixed(2)}倍 買い優勢`;
                return (
                  <Typography variant="body1" fontWeight="bold" color={color}>
                    {label}
                  </Typography>
                );
              })()}
            </Box>
          </Box>
        </CardContent>
      </Card>

      {/* シグナル */}
      {signals.length > 0 && (
        <Stack spacing={1}>
          {signals.map((sig, i) => (
            <Alert
              key={i}
              severity={sig.type === "positive" ? "success" : sig.type === "negative" ? "warning" : "info"}
              variant="outlined"
              sx={{ py: 0 }}
            >
              {sig.message}
            </Alert>
          ))}
          <Typography variant="caption" color="text.secondary">
            ※ シグナルは参考情報です。投資判断はご自身の責任で行ってください。
          </Typography>
        </Stack>
      )}
    </Stack>
  );
}
