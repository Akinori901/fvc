import { useRef, useCallback } from "react";
import {
  Box,
  Button,
  Card,
  CardContent,
  CssBaseline,
  Stack,
  Typography,
  createTheme,
  ThemeProvider,
} from "@mui/material";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import TrendingDownIcon from "@mui/icons-material/TrendingDown";
import SaveAltIcon from "@mui/icons-material/SaveAlt";
import IosShareIcon from "@mui/icons-material/IosShare";
import {
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import { toPng } from "html-to-image";
import { useSearchParams } from "react-router-dom";
import LoadingSpinner from "@/components/common/LoadingSpinner";
import { useShareDashboard } from "@/hooks/useFamilyPortfolio";
import { formatCurrency } from "@/utils/format";
import { ASSET_CLASS_COLORS } from "@/types/familyPortfolio";
import type { AssetClass } from "@/types/familyPortfolio";

const darkTheme = createTheme({
  palette: {
    mode: "dark",
    background: {
      default: "#1a1a2e",
      paper: "#16213e",
    },
    primary: { main: "#00d4aa" },
    text: {
      primary: "#e0e0e0",
      secondary: "#8892b0",
    },
  },
  typography: {
    fontFamily: '"Noto Sans JP", "Roboto", sans-serif',
  },
});

const CHART_GREEN = "#00d4aa";

const INDEX_LINES = [
  { key: "nikkei225", label: "日経平均", color: "#ff6b6b" },
  { key: "topix", label: "TOPIX", color: "#ffa94d" },
  { key: "nasdaq100", label: "NASDAQ100", color: "#74c0fc" },
  { key: "sp500", label: "S&P500", color: "#b197fc" },
] as const;

export default function ShareDashboardPage() {
  const [searchParams] = useSearchParams();
  const memberParam = searchParams.get("member") ?? undefined;
  const { data, isLoading } = useShareDashboard(memberParam);
  const captureRef = useRef<HTMLDivElement>(null);

  const handleShareOrSave = useCallback(async () => {
    if (!captureRef.current) return;
    const dataUrl = await toPng(captureRef.current, {
      backgroundColor: "#1a1a2e",
      pixelRatio: 2,
    });
    const now = new Date();
    const y = String(now.getFullYear()).slice(2);
    const m = String(now.getMonth() + 1).padStart(2, "0");
    const filename = `portfolio-${y}${m}.png`;

    // Web Share API が files をサポートしていれば共有シート
    try {
      const blob = await (await fetch(dataUrl)).blob();
      const file = new File([blob], filename, { type: "image/png" });
      if (navigator.canShare && navigator.canShare({ files: [file] })) {
        await navigator.share({
          files: [file],
          title: "ポートフォリオ",
          text: "資産推移",
        });
        return;
      }
    } catch (e) {
      // ユーザーキャンセル(AbortError)は無音で終了
      if ((e as Error).name === "AbortError") return;
      // それ以外はDLにフォールバック
    }

    // フォールバック: ダウンロード
    const link = document.createElement("a");
    link.download = filename;
    link.href = dataUrl;
    link.click();
  }, []);

  // 表示用: 共有可能なら「共有」、それ以外は「画像として保存」
  const canShareFiles =
    typeof navigator !== "undefined" &&
    typeof navigator.canShare === "function" &&
    // ダミーFileで判定（モバイルSafari/Chromeでtrue）
    (() => {
      try {
        const dummy = new File([new Blob()], "x.png", { type: "image/png" });
        return navigator.canShare({ files: [dummy] });
      } catch {
        return false;
      }
    })();

  if (isLoading) {
    return (
      <ThemeProvider theme={darkTheme}>
        <CssBaseline />
        <Box
          sx={{
            minHeight: "100vh",
            bgcolor: "background.default",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <LoadingSpinner />
        </Box>
      </ThemeProvider>
    );
  }

  if (!data) return null;

  const total = Number(data.total_value_jpy);
  const chart = data.monthly_chart;
  const now = new Date();
  const yearShort = String(now.getFullYear()).slice(2);
  const month = now.getMonth() + 1;

  // 月初来損益: dynamic_valuation の「月初時点総資産」と「現在総資産」で算出する。
  // monthly_chart.value は non_stock_value 集計の取りこぼし (投信 proxy 未紐付け等) で
  // 実資産より極端に小さくなるため、MTD 計算には使えない。
  // 詳細: docs/reports/2026-05-29_mtd_remediation_plan.md (Step 1.5)
  const baselineTotal = data.monthly_chart_total_baseline != null
    ? Number(data.monthly_chart_total_baseline)
    : null;
  const currentTotal = data.monthly_chart_total_current != null
    ? Number(data.monthly_chart_total_current)
    : Number(data.total_value_jpy);
  const mtdChange = baselineTotal !== null && !Number.isNaN(currentTotal)
    ? currentTotal - baselineTotal
    : null;
  const mtdBase = baselineTotal !== null && baselineTotal > 0
    ? baselineTotal
    : null;
  const mtdPct = mtdChange !== null && mtdBase !== null
    ? (mtdChange / mtdBase) * 100
    : null;

  const yoyJpy = data.yoy_change_jpy != null ? Number(data.yoy_change_jpy) : null;
  const yoyPct = data.yoy_change_pct != null ? Number(data.yoy_change_pct) : null;
  const dodJpy = data.dod_change_jpy != null ? Number(data.dod_change_jpy) : null;
  const dodPct = data.dod_change_pct != null ? Number(data.dod_change_pct) : null;
  const unrealizedGain = data.unrealized_gain_jpy != null ? Number(data.unrealized_gain_jpy) : null;
  const totalCost = data.total_cost_jpy != null ? Number(data.total_cost_jpy) : null;
  const unrealizedPct = unrealizedGain !== null && totalCost !== null && totalCost > 0
    ? (unrealizedGain / totalCost) * 100
    : null;
  // 年率: 累積CAGR。1年未満は非表示
  const annualizedPct = (() => {
    if (unrealizedPct === null) return null;
    if (!data.earliest_snapshot_date) return null;
    const earliestMs = Date.parse(data.earliest_snapshot_date);
    if (Number.isNaN(earliestMs)) return null;
    const years = (Date.now() - earliestMs) / (365.25 * 24 * 60 * 60 * 1000);
    if (years < 1) return null;
    return (Math.pow(1 + unrealizedPct / 100, 1 / years) - 1) * 100;
  })();

  const formatYAxis = (value: number) => {
    if (value >= 100_000_000) return `${(value / 100_000_000).toFixed(1)}億`;
    if (value >= 10_000) return `${Math.round(value / 10_000)}万`;
    return String(value);
  };

  const pieData = data.by_asset_class.map((a) => ({
    name: a.label,
    value: Number(a.value_jpy),
    key: a.asset_class,
  }));

  return (
    <ThemeProvider theme={darkTheme}>
      <CssBaseline />
      <Box
        sx={{
          minHeight: "100vh",
          bgcolor: "background.default",
          display: "flex",
          justifyContent: "center",
          py: 3,
          px: 2,
        }}
      >
        <Box sx={{ maxWidth: 480, width: "100%" }}>
          <Box ref={captureRef} sx={{ px: 1, pb: 2 }}>
          {/* ヘッダー */}
          <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
            <Typography variant="subtitle1" fontWeight="bold" color="primary.main">
              月間成績
            </Typography>
            <Typography variant="subtitle1" color="text.secondary">
              {yearShort}年{month}月
            </Typography>
          </Stack>

          {/* 資産総額 */}
          <Box sx={{ textAlign: "center", mb: 1 }}>
            <Typography variant="body2" color="text.secondary">
              資産総額
            </Typography>
            <Typography
              variant="h3"
              fontWeight="bold"
              sx={{ letterSpacing: 1, my: 0.5 }}
            >
              {formatCurrency(total)}
            </Typography>
            {mtdChange !== null && mtdPct !== null && (
              <Typography
                variant="h6"
                color={mtdChange >= 0 ? "primary.main" : "error.main"}
              >
                月初来損益{" "}
                <strong>
                  {mtdChange >= 0 ? "+" : ""}
                  {formatCurrency(mtdChange)}
                </strong>
                {" "}
                ({mtdChange >= 0 ? "+" : ""}{mtdPct.toFixed(1)}%)
              </Typography>
            )}
            {unrealizedGain !== null && unrealizedPct !== null && (
              <Typography
                variant="body2"
                color={unrealizedGain >= 0 ? "primary.main" : "error.main"}
                sx={{ mt: 0.5, opacity: 0.85 }}
              >
                評価損益{" "}
                {unrealizedGain >= 0 ? "+" : ""}
                {formatCurrency(unrealizedGain)}
                {" "}
                ({unrealizedGain >= 0 ? "+" : ""}{unrealizedPct.toFixed(1)}%
                {annualizedPct !== null && (
                  <>
                    {" / 年率"}{annualizedPct >= 0 ? "+" : ""}{annualizedPct.toFixed(1)}%
                  </>
                )}
                )
              </Typography>
            )}
          </Box>

          {/* 当月推移グラフ */}
          {chart.length > 0 && (
            <Card sx={{ mb: 2 }}>
              <CardContent sx={{ pb: "12px !important" }}>
                <Box sx={{ width: "100%", height: 220 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={chart}>
                      <defs>
                        <linearGradient id="shareGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor={CHART_GREEN} stopOpacity={0.3} />
                          <stop offset="95%" stopColor={CHART_GREEN} stopOpacity={0.02} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#2a2a4a" />
                      <XAxis
                        dataKey="date"
                        tick={{ fontSize: 11, fill: "#8892b0" }}
                        tickFormatter={(v: string) => {
                          const day = v.slice(8, 10);
                          const mon = v.slice(5, 7);
                          return day === "31" || day === "30" || day === "29" || day === "28"
                            ? `${Number(mon)}/${Number(day)}`
                            : String(Number(day));
                        }}
                        stroke="#2a2a4a"
                      />
                      <YAxis
                        tick={{ fontSize: 10, fill: "#8892b0" }}
                        tickFormatter={formatYAxis}
                        width={55}
                        stroke="#2a2a4a"
                        domain={["dataMin - auto", "dataMax + auto"]}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "#16213e",
                          border: "1px solid #2a2a4a",
                          borderRadius: 8,
                          fontSize: 12,
                        }}
                        formatter={(
                          value: number | string | undefined,
                          name: string | number | undefined,
                        ): [string, string] => {
                          const numValue = typeof value === "number" ? value : Number(value ?? 0);
                          const strName = String(name ?? "");
                          const idx = INDEX_LINES.find((l) => l.key === strName);
                          if (idx) return [formatCurrency(numValue), idx.label];
                          if (strName === "value") return [formatCurrency(numValue), "資産額"];
                          return [formatCurrency(numValue), strName];
                        }}
                        labelFormatter={(label: unknown) => String(label ?? "")}
                      />
                      {INDEX_LINES.map((idx) => (
                        <Line
                          key={idx.key}
                          type="monotone"
                          dataKey={idx.key}
                          stroke={idx.color}
                          strokeWidth={1}
                          strokeOpacity={0.5}
                          strokeDasharray="4 3"
                          dot={false}
                          connectNulls
                        />
                      ))}
                      <Area
                        type="monotone"
                        dataKey="value"
                        stroke={CHART_GREEN}
                        strokeWidth={2.5}
                        fill="url(#shareGrad)"
                        dot={{ r: 3, fill: CHART_GREEN, strokeWidth: 0 }}
                        activeDot={{ r: 5, fill: "#fff", stroke: CHART_GREEN, strokeWidth: 2 }}
                      />
                    </ComposedChart>
                  </ResponsiveContainer>
                </Box>
                {/* 指数凡例 */}
                <Stack
                  direction="row"
                  justifyContent="center"
                  flexWrap="wrap"
                  gap={1}
                  sx={{ mt: 1 }}
                >
                  <Box sx={{ display: "flex", alignItems: "center", gap: 0.3 }}>
                    <Box sx={{ width: 16, height: 0, borderTop: `2px solid ${CHART_GREEN}` }} />
                    <Typography variant="caption" sx={{ fontSize: 10, color: "text.secondary" }}>資産額</Typography>
                  </Box>
                  {INDEX_LINES.map((idx) => (
                    <Box key={idx.key} sx={{ display: "flex", alignItems: "center", gap: 0.3 }}>
                      <Box sx={{ width: 16, height: 0, borderTop: `2px dashed ${idx.color}`, opacity: 0.7 }} />
                      <Typography variant="caption" sx={{ fontSize: 10, color: "text.secondary" }}>{idx.label}</Typography>
                    </Box>
                  ))}
                </Stack>
              </CardContent>
            </Card>
          )}

          {/* 前月対比・前日対比 */}
          <Stack direction="row" spacing={1.5} sx={{ mb: 2 }}>
            {yoyJpy !== null && yoyPct !== null && (
              <ChangeCard label="前年対比" value={yoyJpy} pct={yoyPct} />
            )}
            {dodJpy !== null && dodPct !== null && (
              <ChangeCard label="前日対比" value={dodJpy} pct={dodPct} />
            )}
          </Stack>

          {/* アロケーション */}
          {pieData.length > 0 && (
            <Card sx={{ mb: 2 }}>
              <CardContent>
                <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1 }}>
                  アロケーション
                </Typography>
                <Stack direction="row" alignItems="center" spacing={1}>
                  <Box sx={{ width: 160, height: 160, flexShrink: 0 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={pieData}
                          cx="50%"
                          cy="50%"
                          innerRadius={40}
                          outerRadius={70}
                          paddingAngle={2}
                          dataKey="value"
                        >
                          {pieData.map((entry, index) => (
                            <Cell
                              key={`cell-${index}`}
                              fill={ASSET_CLASS_COLORS[entry.key as AssetClass] ?? "#546e7a"}
                            />
                          ))}
                        </Pie>
                        <Tooltip
                          contentStyle={{
                            backgroundColor: "#16213e",
                            border: "1px solid #2a2a4a",
                            borderRadius: 8,
                            fontSize: 11,
                          }}
                          formatter={(value: number | undefined) => value != null ? formatCurrency(value) : ""}
                        />
                      </PieChart>
                    </ResponsiveContainer>
                  </Box>
                  <Box sx={{ flex: 1 }}>
                    {pieData.map((entry) => {
                      const pct = total > 0 ? ((entry.value / total) * 100).toFixed(1) : "0";
                      return (
                        <Stack
                          key={entry.key}
                          direction="row"
                          alignItems="center"
                          spacing={0.5}
                          sx={{ mb: 0.3 }}
                        >
                          <Box
                            sx={{
                              width: 8,
                              height: 8,
                              borderRadius: "50%",
                              bgcolor: ASSET_CLASS_COLORS[entry.key as AssetClass] ?? "#546e7a",
                              flexShrink: 0,
                            }}
                          />
                          <Typography variant="caption" sx={{ fontSize: 11, color: "text.secondary" }}>
                            {entry.name}
                          </Typography>
                          <Typography
                            variant="caption"
                            sx={{ fontSize: 11, color: "text.primary", ml: "auto !important" }}
                          >
                            {pct}%
                          </Typography>
                        </Stack>
                      );
                    })}
                  </Box>
                </Stack>
              </CardContent>
            </Card>
          )}

          {/* フッター */}
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{ display: "block", textAlign: "center", opacity: 0.5, mt: 2 }}
          >
            Fair Value Calculator
          </Typography>
          </Box>{/* captureRef end */}

          <Button
            variant="contained"
            startIcon={canShareFiles ? <IosShareIcon /> : <SaveAltIcon />}
            onClick={handleShareOrSave}
            fullWidth
            sx={{ mt: 2 }}
          >
            {canShareFiles ? "共有" : "画像として保存"}
          </Button>
        </Box>
      </Box>
    </ThemeProvider>
  );
}

function ChangeCard({ label, value, pct }: { label: string; value: number; pct: number }) {
  const isPositive = value >= 0;
  return (
    <Card sx={{ flex: 1 }}>
      <CardContent sx={{ py: 1.5, "&:last-child": { pb: 1.5 } }}>
        <Typography variant="caption" color="text.secondary">
          {label}
        </Typography>
        <Stack direction="row" alignItems="center" spacing={0.5}>
          {isPositive ? (
            <TrendingUpIcon sx={{ fontSize: 18, color: "primary.main" }} />
          ) : (
            <TrendingDownIcon sx={{ fontSize: 18, color: "error.main" }} />
          )}
          <Typography
            variant="body1"
            fontWeight="bold"
            color={isPositive ? "primary.main" : "error.main"}
          >
            {isPositive ? "+" : ""}
            {formatCurrency(value)}
          </Typography>
        </Stack>
        <Typography
          variant="caption"
          color={isPositive ? "primary.main" : "error.main"}
          sx={{ fontSize: 11 }}
        >
          ({isPositive ? "+" : ""}{pct.toFixed(2)}%)
        </Typography>
      </CardContent>
    </Card>
  );
}
