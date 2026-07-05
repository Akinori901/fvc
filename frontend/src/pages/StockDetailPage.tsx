import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Alert,
  Box,
  Typography,
  Tab,
  Tabs,
  Card,
  CardContent,
  Stack,
  Chip,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  FormControlLabel,
  Checkbox,
  TextField,
  Divider,
} from "@mui/material";
import CalculateIcon from "@mui/icons-material/Calculate";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import SyncIcon from "@mui/icons-material/Sync";
import EditIcon from "@mui/icons-material/Edit";
import DeleteSweepIcon from "@mui/icons-material/DeleteSweep";
import { useStock, useStockFinancials, useStockPrices } from "@/hooks/useStocks";
import { useStockValuations, useCalculateFairValue } from "@/hooks/useValuations";
import ResultSummary from "@/components/valuation/ResultSummary";
import { useSyncTrigger } from "@/hooks/useSync";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { stocksApi } from "@/api/stocks";

import { marginApi } from "@/api/margin";
import { manualFinancialApi } from "@/api/manualFinancial";
import FinancialTable from "@/components/stock/FinancialTable";
import TechnicalChartGroup from "@/components/stock/TechnicalChartGroup";
import ManualFinancialInputModal from "@/components/stock/ManualFinancialInputModal";
import AiAnalysisPanel from "@/components/stock/AiAnalysisPanel";
import PaperTradePanel from "@/components/stock/PaperTradePanel";
import MarginTrendPanel from "@/components/stock/MarginTrendPanel";
import StockNewsTab from "@/components/news/StockNewsTab";
import LoadingSpinner from "@/components/common/LoadingSpinner";
import ErrorAlert from "@/components/common/ErrorAlert";
import EvaluationBadge from "@/components/common/EvaluationBadge";
import FinancialTermHelp from "@/components/common/FinancialTermHelp";
import { getEvaluationZone, getZoneInfoByZone, type EvaluationZone } from "@/utils/evaluation";
import { computeOverallRating } from "@/utils/overallRating";
import StockAttributeBadges from "@/components/common/StockAttributeBadges";
import { formatCurrency, formatPercent, formatMultiple } from "@/utils/format";

export default function StockDetailPage() {
  const { code } = useParams<{ code: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [tab, setTab] = useState(0);
  const [manualModalOpen, setManualModalOpen] = useState(false);
  const [resetDialogOpen, setResetDialogOpen] = useState(false);
  const [clearManual, setClearManual] = useState(false);
  const [resetResult, setResetResult] = useState<string | null>(null);
  const [calcGrowthRate, setCalcGrowthRate] = useState("2");
  const [calcError, setCalcError] = useState<string | null>(null);
  const syncMutation = useSyncTrigger();
  const calculateMutation = useCalculateFairValue();

  const resetMutation = useMutation({
    mutationFn: () =>
      stocksApi.resetFinancials(code ?? "", { keep_manual: !clearManual, resync: true }),
    onSuccess: (res) => {
      setResetResult(res.data.message + (res.data.sync_error ? ` (エラー: ${res.data.sync_error})` : ""));
      setResetDialogOpen(false);
      queryClient.invalidateQueries({ queryKey: ["stockFinancials", code] });
      queryClient.invalidateQueries({ queryKey: ["stock", code] });
    },
    onError: () => {
      setResetResult("リセットに失敗しました。");
      setResetDialogOpen(false);
    },
  });

  const { data: stock, isLoading, error } = useStock(code ?? "");
  const { data: financials } = useStockFinancials(code ?? "");
  const { data: prices } = useStockPrices(code ?? "", 365);
  const { data: valuations } = useStockValuations(code ?? "");
  const { data: marginData } = useQuery({
    queryKey: ["stockMargin", code],
    queryFn: () => marginApi.getStockMargin(code ?? "").then((r) => r.data),
    enabled: !!code,
  });
  const { data: manualFinancials } = useQuery({
    queryKey: ["stocks", code, "financials", "manual"],
    queryFn: () => manualFinancialApi.list(code ?? "").then((r) => r.data),
    enabled: !!code,
  });

  if (isLoading) return <LoadingSpinner />;
  if (error || !stock) return <ErrorAlert message="銘柄が見つかりません" />;

  const latestFinancial = financials
    ?.sort((a, b) => b.fiscal_year - a.fiscal_year)[0];
  const latestManual = manualFinancials?.sort((a, b) => b.fiscal_year - a.fiscal_year)[0];
  const effectiveBps = (() => {
    if (!latestFinancial && !latestManual) return null;
    // adj_factor: 株式分割調整係数（BPS・EPSに乗じてスクリーニングと一致させる）
    const applyAdj = (bps: string, eps: string | null, adjFactor: string) => {
      const adj = Number(adjFactor);
      return {
        bps: String(Number(bps) * adj),
        eps: eps != null ? String(Number(eps) * adj) : null,
      };
    };
    if (!latestFinancial) return { bps: latestManual!.bps, eps: latestManual!.eps, fiscal_year: latestManual!.fiscal_year, isManual: true };
    if (!latestManual) {
      const adj = applyAdj(latestFinancial.bps, latestFinancial.eps, latestFinancial.adj_factor);
      return { ...adj, fiscal_year: latestFinancial.fiscal_year, isManual: false };
    }
    if (latestManual.fiscal_year > latestFinancial.fiscal_year)
      return { bps: latestManual.bps, eps: latestManual.eps, fiscal_year: latestManual.fiscal_year, isManual: true };
    const adj = applyAdj(latestFinancial.bps, latestFinancial.eps, latestFinancial.adj_factor);
    return { ...adj, fiscal_year: latestFinancial.fiscal_year, isManual: false };
  })();
  const latestPrice = prices
    ?.sort((a, b) => b.date.localeCompare(a.date))[0];

  // スクリーニング指標の計算
  const COST_OF_CAPITAL = 0.08;
  const sortedFinancials = [...(financials ?? [])].sort((a, b) => b.fiscal_year - a.fiscal_year);

  const pbr =
    latestPrice && effectiveBps?.bps
      ? Number(latestPrice.close_price) / Number(effectiveBps.bps)
      : null;
  const roe =
    effectiveBps?.eps && effectiveBps?.bps
      ? Number(effectiveBps.eps) / Number(effectiveBps.bps)
      : null;

  const impliedGrowthRate = (() => {
    if (pbr == null || roe == null) return null;
    if (Math.abs(pbr - 1) < 0.05) return null;
    return (pbr * COST_OF_CAPITAL - roe) / (pbr - 1);
  })();

  const computedGrowthRateLabel = (() => {
    if (impliedGrowthRate == null) return null;
    if (pbr != null && pbr < 1 && impliedGrowthRate >= COST_OF_CAPITAL) return "ROE持続性に疑念";
    if (impliedGrowthRate < COST_OF_CAPITAL) {
      if (impliedGrowthRate >= 0.07) return "かなり強気";
      if (impliedGrowthRate >= 0.05) return "非常に優秀";
      if (impliedGrowthRate >= 0.03) return "優秀";
      if (impliedGrowthRate >= 0.02) return "普通";
      if (impliedGrowthRate >= 0.00) return "低成長";
      return "マイナス成長";
    }
    return null;
  })();

  const companyForecastGrowthRate = (() => {
    const f = sortedFinancials[0];
    if (!f?.eps_forecast || !f?.eps || Number(f.eps) === 0) return null;
    return (Number(f.eps_forecast) - Number(f.eps)) / Math.abs(Number(f.eps));
  })();

  const epsGrowthYoy = (() => {
    const eps0 = sortedFinancials[0]?.eps ? Number(sortedFinancials[0].eps) : null;
    const eps1 = sortedFinancials[1]?.eps ? Number(sortedFinancials[1].eps) : null;
    if (eps0 == null || eps1 == null || eps1 === 0) return null;
    return (eps0 - eps1) / Math.abs(eps1);
  })();

  const epsCagr3y = (() => {
    const eps0 = sortedFinancials[0]?.eps ? Number(sortedFinancials[0].eps) : null;
    const eps3 = sortedFinancials[3]?.eps ? Number(sortedFinancials[3].eps) : null;
    if (eps0 == null || eps3 == null || eps3 === 0) return null;
    const ratio = eps0 / eps3;
    if (ratio <= 0) return null;
    return Math.pow(ratio, 1 / 3) - 1;
  })();

  const roeTrend = (() => {
    const roes = sortedFinancials
      .slice(0, 3)
      .map((f) => (f.eps && f.bps ? Number(f.eps) / Number(f.bps) : null))
      .filter((r): r is number => r !== null);
    if (roes.length < 3) return null;
    const diff1 = roes[0]! - roes[1]!;
    const diff2 = roes[1]! - roes[2]!;
    if (diff1 > 0.005 && diff2 > 0.005) return "improving";
    if (diff1 < -0.005 && diff2 < -0.005) return "declining";
    return "stable";
  })();

  const revenueGrowthYoy = (() => {
    const rev0 = sortedFinancials[0]?.revenue ?? null;
    const rev1 = sortedFinancials[1]?.revenue ?? null;
    if (rev0 == null || rev1 == null || rev1 === 0) return null;
    return (rev0 - rev1) / Math.abs(rev1);
  })();

  // 評価ゾーン（デフォルト成長率 2% でのゴードンモデル）
  const DEFAULT_GROWTH_RATE = 0.02;
  const fairPbr =
    roe != null && roe > 0
      ? (roe - DEFAULT_GROWTH_RATE) / (COST_OF_CAPITAL - DEFAULT_GROWTH_RATE)
      : null;
  const fairValue =
    fairPbr != null && effectiveBps?.bps
      ? fairPbr * Number(effectiveBps.bps)
      : null;
  const discountRate =
    fairValue != null && fairValue > 0 && latestPrice
      ? (fairValue - Number(latestPrice.close_price)) / fairValue
      : null;
  const evaluationZoneInfo = (() => {
    if (fairValue == null || !latestPrice) return null;
    if (fairValue <= 0) return getEvaluationZone(-1);
    return getEvaluationZone(discountRate!);
  })();


  // テクニカル指標（52週高値効果）— 365日分の株価データからクライアント側で計算
  const technicalMetrics = (() => {
    if (!prices || prices.length < 25 || !latestPrice) return null;
    const sortedPrices = [...prices].sort((a, b) => b.date.localeCompare(a.date));
    const closes = sortedPrices.map((p) => Number(p.close_price));
    const currentPrice = closes[0]!;
    const high52w = Math.max(...closes);
    const low52w = Math.min(...closes);
    const range = high52w - low52w;
    const position = range > 0 ? (currentPrice - low52w) / range : 1.0;
    const distance = high52w > 0 ? (currentPrice - high52w) / high52w : null;
    const ma25 = closes.slice(0, 25).reduce((a, b) => a + b, 0) / 25;
    const ma25Dev = ma25 > 0 ? (currentPrice - ma25) / ma25 : null;

    // momentum_signal（volume なしの簡易版: position + ma25 で判定）
    let signal: "strong_buy" | "buy" | "neutral" | "caution" | "sell";
    if (position >= 0.95 && ma25Dev != null && ma25Dev > 0.05) signal = "strong_buy";
    else if (position >= 0.80 && (ma25Dev == null || ma25Dev > 0)) signal = "buy";
    else if (position >= 0.50) signal = "neutral";
    else if (position >= 0.30) signal = "caution";
    else signal = "sell";

    // 売買代金20日平均（流動性指標）
    const turnovers = sortedPrices
      .filter((p) => p.volume != null && p.volume > 0)
      .slice(0, 20)
      .map((p) => p.volume! * Number(p.close_price));
    const avgTurnover = turnovers.length >= 20
      ? turnovers.reduce((a, b) => a + b, 0) / 20
      : null;
    const liquidityLevel = avgTurnover == null ? null
      : avgTurnover >= 1_000_000_000 ? "高"
      : avgTurnover >= 100_000_000 ? "中"
      : avgTurnover >= 10_000_000 ? "低"
      : "極低";

    return { position, nearHigh: position >= 0.95, distance, ma25Dev, signal, avgTurnover, liquidityLevel };
  })();

  // 総合評価スコア
  const slRatioNum = marginData?.latest?.sl_ratio != null ? Number(marginData.latest.sl_ratio) : null;
  const overallRating = computeOverallRating({
    evaluationZone: evaluationZoneInfo?.zone ?? null,
    growthRateLabel: computedGrowthRateLabel,
    roeTrend,
    epsCagr3y,
    epsGrowthYoy,
    slRatio: slRatioNum,
    momentumSignal: technicalMetrics?.signal ?? null,
    dividendYield: stock?.dividend_yield != null ? Number(stock.dividend_yield) : null,
    payoutRatio: stock?.payout_ratio != null ? Number(stock.payout_ratio) : null,
    consecutiveDividendYears: stock?.consecutive_dividend_years ?? null,
    progressiveDividendYears: stock?.progressive_dividend_years ?? null,
    fcfYield: stock?.fcf_yield != null ? Number(stock.fcf_yield) : null,
    fcfMargin: stock?.fcf_margin != null ? Number(stock.fcf_margin) : null,
    fcf: stock?.fcf ?? null,
  });

  return (
    <Box>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
        <Button
          startIcon={<ArrowBackIcon />}
          onClick={() => navigate("/stocks")}
        >
          銘柄一覧に戻る
        </Button>
        <Stack direction="row" spacing={1}>
          <Button
            variant="outlined"
            size="small"
            startIcon={<EditIcon />}
            onClick={() => setManualModalOpen(true)}
            disabled={!code}
          >
            財務データ手動入力
          </Button>
          <Button
            variant="outlined"
            size="small"
            startIcon={<SyncIcon />}
            onClick={() => syncMutation.mutate({ sync_type: "financials", codes: [code ?? ""] })}
            disabled={syncMutation.isPending || !code}
          >
            {syncMutation.isPending ? "同期中..." : "財務データ同期"}
          </Button>
          <Button
            variant="outlined"
            size="small"
            color="warning"
            startIcon={<DeleteSweepIcon />}
            onClick={() => setResetDialogOpen(true)}
            disabled={!code}
          >
            財務データリセット
          </Button>
        </Stack>
      </Stack>

      {!stock.is_active && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          この銘柄は上場廃止されています。表示されているデータは上場当時のものです。
        </Alert>
      )}

      {resetResult && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setResetResult(null)}>
          {resetResult}
        </Alert>
      )}

      <Stack direction="row" alignItems="center" spacing={1} flexWrap="wrap" sx={{ mb: 2, rowGap: 1 }}>
        <Typography variant="h5" sx={{ mr: 1 }}>
          {stock.code} - {stock.name}
        </Typography>
        {stock.market && <Chip label={stock.market} size="small" />}
        {stock.sector && (
          <Chip label={stock.sector} size="small" variant="outlined" />
        )}
        {stock.evaluation_zone && (() => {
          const zoneInfo = getZoneInfoByZone(stock.evaluation_zone as EvaluationZone);
          return (
            <Chip
              label={zoneInfo.label}
              size="small"
              sx={{
                backgroundColor: zoneInfo.bgColor,
                color: zoneInfo.color,
                fontWeight: "bold",
                fontSize: "0.7rem",
                height: 22,
              }}
            />
          );
        })()}
        <Chip
          label={overallRating.label}
          size="small"
          sx={{
            backgroundColor: overallRating.bgColor,
            color: overallRating.color,
            fontWeight: "bold",
            fontSize: "0.7rem",
            height: 22,
          }}
        />
        <StockAttributeBadges input={stock} />
      </Stack>

      {/* サマリーカード */}
      <Box sx={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 2, mb: 3 }}>
        <Card>
          <CardContent>
            <Typography variant="body2" color="text.secondary">最新株価</Typography>
            <Typography variant="h6">
              {latestPrice ? formatCurrency(latestPrice.close_price) : "-"}
            </Typography>
            {latestPrice?.date && (
              <Typography variant="caption" color="text.secondary">{latestPrice.date}</Typography>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardContent>
            <Stack direction="row" alignItems="center" spacing={0.5}>
              <Typography variant="body2" color="text.secondary">適正株価</Typography>
              <FinancialTermHelp
                termKey="fair_value"
                extra={
                  <Box sx={{ mt: 1 }}>
                    <Typography variant="subtitle2" gutterBottom>算出できない場合</Typography>
                    <Typography variant="body2" component="div">
                      <ul style={{ margin: 0, paddingLeft: 16 }}>
                        {!effectiveBps?.bps && <li>BPS（1株純資産）データがありません</li>}
                        {!effectiveBps?.eps && <li>EPS（1株利益）データがありません</li>}
                        {roe != null && roe <= 0 && <li>ROEが0以下のため算出不可（ROE = EPS / BPS）</li>}
                        {!latestPrice && <li>最新株価データがありません</li>}
                        {fairValue != null && <li style={{ color: "green" }}>現在算出可能です</li>}
                      </ul>
                    </Typography>
                  </Box>
                }
              />
            </Stack>
            <Typography variant="h6">
              {fairValue != null ? formatCurrency(fairValue) : "-"}
            </Typography>
            <Typography variant="caption" color="text.secondary">成長率2%想定</Typography>
          </CardContent>
        </Card>
        <Card>
          <CardContent>
            <Stack direction="row" alignItems="center" spacing={0.5}>
              <Typography variant="body2" color="text.secondary">乖離率</Typography>
              <FinancialTermHelp termKey="discount_rate" />
            </Stack>
            <Typography
              variant="h6"
              color={discountRate != null ? (discountRate >= 0 ? "success.main" : "error.main") : undefined}
            >
              {discountRate != null ? `${discountRate >= 0 ? "+" : ""}${formatPercent(discountRate)}` : "-"}
            </Typography>
            {discountRate != null && (
              <Typography variant="caption" color="text.secondary">
                {discountRate > 0.2 ? "割安" : discountRate > 0 ? "やや割安" : discountRate > -0.2 ? "やや割高" : "割高"}
              </Typography>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardContent>
            <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
              <Stack direction="row" alignItems="center" spacing={0.5}>
                <Typography variant="body2" color="text.secondary">BPS</Typography>
                <FinancialTermHelp termKey="bps" />
              </Stack>
              {effectiveBps?.isManual && (
                <Chip label="手動データ" size="small" color="warning" variant="outlined" sx={{ fontSize: "0.65rem", height: 18 }} />
              )}
            </Stack>
            <Typography variant="h6">
              {effectiveBps ? formatCurrency(Number(effectiveBps.bps)) : "-"}
            </Typography>
            {effectiveBps && (
              <Typography variant="caption" color="text.secondary">{effectiveBps.fiscal_year}年度</Typography>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardContent>
            <Stack direction="row" alignItems="center" spacing={0.5}>
              <Typography variant="body2" color="text.secondary">ROE</Typography>
              <FinancialTermHelp termKey="roe" />
            </Stack>
            <Typography variant="h6">
              {effectiveBps?.eps && effectiveBps?.bps
                ? formatPercent(Number(effectiveBps.eps) / Number(effectiveBps.bps))
                : "-"}
            </Typography>
          </CardContent>
        </Card>
        <Card>
          <CardContent>
            <Stack direction="row" alignItems="center" spacing={0.5}>
              <Typography variant="body2" color="text.secondary">PBR / 適正PBR</Typography>
              <FinancialTermHelp termKey="pbr" />
            </Stack>
            <Typography variant="h6">
              {pbr != null ? formatMultiple(pbr) : "-"}
              {fairPbr != null && (
                <Typography component="span" variant="body2" color="text.secondary"> / {formatMultiple(fairPbr)}</Typography>
              )}
            </Typography>
          </CardContent>
        </Card>
      </Box>

      {/* 業界平均推計 */}
      {stock.industry_metrics && (
        <>
          <Divider sx={{ my: 3 }} />
          <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1 }}>
            業界平均推計
          </Typography>
          <Box sx={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 2, mb: 3 }}>
            <Card>
              <CardContent>
                <Stack direction="row" alignItems="center" spacing={0.5}>
                  <Typography variant="body2" color="text.secondary">業界平均ROE</Typography>
                  <FinancialTermHelp termKey="industry_avg_roe" />
                </Stack>
                <Typography variant="h6">
                  {formatPercent(Number(stock.industry_metrics.min_roe))}
                  {" 〜 "}
                  {formatPercent(Number(stock.industry_metrics.max_roe))}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {stock.industry_metrics.sector}
                </Typography>
              </CardContent>
            </Card>
            <Card>
              <CardContent>
                <Stack direction="row" alignItems="center" spacing={0.5}>
                  <Typography variant="body2" color="text.secondary">業界下限ROE時の適正株価</Typography>
                  <FinancialTermHelp termKey="industry_min_fair_value" />
                </Stack>
                <Typography variant="h6">
                  {formatCurrency(Number(stock.industry_metrics.min_roe_fair_value))}
                </Typography>
                <Typography variant="caption" color="text.secondary">成長率2%想定</Typography>
              </CardContent>
            </Card>
            <Card>
              <CardContent>
                <Stack direction="row" alignItems="center" spacing={0.5}>
                  <Typography variant="body2" color="text.secondary">業界下限ROE時のPBR</Typography>
                  <FinancialTermHelp termKey="industry_min_fair_pbr" />
                </Stack>
                <Typography variant="h6">
                  {formatMultiple(Number(stock.industry_metrics.min_roe_fair_pbr))}
                  {fairPbr != null && (
                    <Typography component="span" variant="body2" color="text.secondary">
                      {" / "}{formatMultiple(fairPbr)}
                    </Typography>
                  )}
                </Typography>
              </CardContent>
            </Card>
          </Box>
        </>
      )}

      {/* 総合評価 */}
      <Card variant="outlined" sx={{ mb: 3, borderColor: overallRating.color, borderWidth: 2 }}>
        <CardContent>
          <Typography variant="subtitle2" color="text.secondary" gutterBottom>
            総合評価
          </Typography>
          <Box sx={{ display: "flex", gap: 3, alignItems: "flex-start" }}>
            {/* ラベルバッジ */}
            <Box
              sx={{
                minWidth: 120,
                px: 3,
                py: 2,
                borderRadius: 2,
                bgcolor: overallRating.bgColor,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
              }}
            >
              <Typography variant="h5" fontWeight="bold" color={overallRating.color}>
                {overallRating.label}
              </Typography>
              <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5 }}>
                スコア: {overallRating.score > 0 ? "+" : ""}{overallRating.score}
              </Typography>
            </Box>

            {/* 評価根拠 */}
            <Box sx={{ flex: 1 }}>
              <Typography variant="caption" color="text.secondary" gutterBottom display="block">
                評価根拠
              </Typography>
              <Stack spacing={0.5}>
                {overallRating.signals.map((sig) => {
                  const impactColor =
                    sig.impact > 0 ? "success.main" : sig.impact < 0 ? "error.main" : "text.secondary";
                  const impactBg =
                    sig.impact > 0 ? "#f1f8e9" : sig.impact < 0 ? "#fff3e0" : "transparent";
                  const icon = sig.impact > 0 ? "✓" : sig.impact < 0 ? "✗" : "○";
                  return (
                    <Box
                      key={sig.category}
                      sx={{
                        display: "flex",
                        alignItems: "center",
                        gap: 1,
                        px: 1,
                        py: 0.25,
                        borderRadius: 1,
                        bgcolor: impactBg,
                      }}
                    >
                      <Typography variant="caption" color={impactColor} sx={{ fontWeight: "bold", minWidth: 12 }}>
                        {icon}
                      </Typography>
                      <Typography variant="caption" color="text.secondary" sx={{ minWidth: 70 }}>
                        {sig.category}:
                      </Typography>
                      <Typography variant="caption" sx={{ flex: 1 }}>
                        {sig.label}
                      </Typography>
                      <Typography
                        variant="caption"
                        color={impactColor}
                        fontWeight="bold"
                        sx={{ minWidth: 30, textAlign: "right" }}
                      >
                        {sig.impact > 0 ? `+${sig.impact}` : sig.impact !== 0 ? sig.impact : "±0"}
                      </Typography>
                    </Box>
                  );
                })}
              </Stack>
            </Box>
          </Box>
        </CardContent>
      </Card>

      {/* スクリーニング指標 */}
      <Card variant="outlined" sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="subtitle2" color="text.secondary" gutterBottom>
            スクリーニング指標
          </Typography>
          <Box sx={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 2 }}>
            <Box>
              <Stack direction="row" alignItems="center" spacing={0.25}>
                <Typography variant="caption" color="text.secondary">評価（成長率2%想定）</Typography>
                <FinancialTermHelp termKey="evaluation" />
              </Stack>
              <Box sx={{ mt: 0.5 }}>
                {evaluationZoneInfo
                  ? <EvaluationBadge zone={evaluationZoneInfo.zone} />
                  : <Typography variant="body1" fontWeight="bold">-</Typography>}
              </Box>
            </Box>
            <Box>
              <Stack direction="row" alignItems="center" spacing={0.25}>
                <Typography variant="caption" color="text.secondary">市場折込成長率</Typography>
                <FinancialTermHelp termKey="implied_growth_rate" />
              </Stack>
              <Typography variant="body1" fontWeight="bold">
                {impliedGrowthRate != null ? formatPercent(impliedGrowthRate) : "-"}
              </Typography>
            </Box>
            <Box>
              <Stack direction="row" alignItems="center" spacing={0.25}>
                <Typography variant="caption" color="text.secondary">成長率評価</Typography>
                <FinancialTermHelp termKey="growth_rate_label" />
              </Stack>
              <Typography variant="body1" fontWeight="bold">
                {computedGrowthRateLabel ?? "-"}
              </Typography>
            </Box>
            <Box>
              <Stack direction="row" alignItems="center" spacing={0.25}>
                <Typography variant="caption" color="text.secondary">会社予想成長率</Typography>
                <FinancialTermHelp termKey="company_forecast_growth" />
              </Stack>
              <Typography variant="body1" fontWeight="bold">
                {companyForecastGrowthRate != null ? formatPercent(companyForecastGrowthRate) : "-"}
              </Typography>
            </Box>
            <Box>
              <Stack direction="row" alignItems="center" spacing={0.25}>
                <Typography variant="caption" color="text.secondary">EPS成長(前年比)</Typography>
                <FinancialTermHelp termKey="eps_growth_yoy" />
              </Stack>
              <Typography variant="body1" fontWeight="bold">
                {epsGrowthYoy != null ? formatPercent(epsGrowthYoy) : "-"}
              </Typography>
            </Box>
            <Box>
              <Stack direction="row" alignItems="center" spacing={0.25}>
                <Typography variant="caption" color="text.secondary">EPS CAGR(3年)</Typography>
                <FinancialTermHelp termKey="eps_cagr_3y" />
              </Stack>
              <Typography variant="body1" fontWeight="bold">
                {epsCagr3y != null ? formatPercent(epsCagr3y) : "-"}
              </Typography>
            </Box>
            <Box>
              <Stack direction="row" alignItems="center" spacing={0.25}>
                <Typography variant="caption" color="text.secondary">ROEトレンド</Typography>
                <FinancialTermHelp termKey="roe_trend" />
              </Stack>
              <Typography variant="body1" fontWeight="bold">
                {roeTrend === "improving"
                  ? "↑改善"
                  : roeTrend === "declining"
                    ? "↓悪化"
                    : roeTrend === "stable"
                      ? "→横ばい"
                      : "-"}
              </Typography>
            </Box>
            <Box>
              <Stack direction="row" alignItems="center" spacing={0.25}>
                <Typography variant="caption" color="text.secondary">売上高成長率</Typography>
                <FinancialTermHelp termKey="revenue_growth" />
              </Stack>
              <Typography variant="body1" fontWeight="bold">
                {revenueGrowthYoy != null ? formatPercent(revenueGrowthYoy) : "-"}
              </Typography>
            </Box>
            <Box>
              <Stack direction="row" alignItems="center" spacing={0.25}>
                <Typography variant="caption" color="text.secondary">EPS</Typography>
                <FinancialTermHelp termKey="eps" />
              </Stack>
              <Typography variant="body1" fontWeight="bold">
                {effectiveBps?.eps != null ? formatCurrency(Number(effectiveBps.eps)) : "-"}
              </Typography>
            </Box>
            <Box>
              <Stack direction="row" alignItems="center" spacing={0.25}>
                <Typography variant="caption" color="text.secondary">信用倍率</Typography>
                <FinancialTermHelp termKey="sl_ratio" />
              </Stack>
              <Typography variant="body1" fontWeight="bold">
                {slRatioNum != null ? `${slRatioNum.toFixed(2)}倍` : "-"}
              </Typography>
            </Box>
            <Box>
              <Stack direction="row" alignItems="center" spacing={0.25}>
                <Typography variant="caption" color="text.secondary">モメンタム</Typography>
                <FinancialTermHelp termKey="momentum" />
              </Stack>
              <Typography variant="body1" fontWeight="bold">
                {technicalMetrics ? ({
                  strong_buy: "強買い",
                  buy: "買い",
                  neutral: "中立",
                  caution: "注意",
                  sell: "売り",
                }[technicalMetrics.signal]) : "-"}
              </Typography>
            </Box>
            <Box>
              <Stack direction="row" alignItems="center" spacing={0.25}>
                <Typography variant="caption" color="text.secondary">52w位置</Typography>
                <FinancialTermHelp termKey="52w_position" />
              </Stack>
              <Typography variant="body1" fontWeight="bold">
                {technicalMetrics ? `${(technicalMetrics.position * 100).toFixed(0)}%` : "-"}
              </Typography>
            </Box>
            <Box>
              <Stack direction="row" alignItems="center" spacing={0.25}>
                <Typography variant="caption" color="text.secondary">25日MA乖離</Typography>
                <FinancialTermHelp termKey="ma25_deviation" />
              </Stack>
              <Typography variant="body1" fontWeight="bold">
                {technicalMetrics?.ma25Dev != null ? formatPercent(technicalMetrics.ma25Dev) : "-"}
              </Typography>
            </Box>
            <Box>
              <Stack direction="row" alignItems="center" spacing={0.25}>
                <Typography variant="caption" color="text.secondary">流動性(売買代金)</Typography>
                <FinancialTermHelp termKey="liquidity" />
              </Stack>
              <Typography
                variant="body1"
                fontWeight="bold"
                color={
                  technicalMetrics?.liquidityLevel === "極低" ? "error.main"
                  : technicalMetrics?.liquidityLevel === "低" ? "warning.main"
                  : "text.primary"
                }
              >
                {technicalMetrics?.liquidityLevel
                  ? `${technicalMetrics.liquidityLevel}${technicalMetrics.avgTurnover != null
                      ? ` (${technicalMetrics.avgTurnover >= 100_000_000
                          ? `${(technicalMetrics.avgTurnover / 100_000_000).toFixed(1)}億`
                          : `${(technicalMetrics.avgTurnover / 10_000).toFixed(0)}万`})`
                      : ""}`
                  : "-"}
              </Typography>
            </Box>
            <Box>
              <Stack direction="row" alignItems="center" spacing={0.25}>
                <Typography variant="caption" color="text.secondary">配当利回り</Typography>
                <FinancialTermHelp termKey="dividend_yield" />
              </Stack>
              <Typography variant="body1" fontWeight="bold">
                {stock?.dividend_yield != null ? `${Number(stock.dividend_yield).toFixed(1)}%` : "-"}
              </Typography>
            </Box>
            <Box>
              <Stack direction="row" alignItems="center" spacing={0.25}>
                <Typography variant="caption" color="text.secondary">配当性向</Typography>
                <FinancialTermHelp termKey="payout_ratio" />
              </Stack>
              <Typography
                variant="body1"
                fontWeight="bold"
                color={
                  stock?.payout_ratio != null && Number(stock.payout_ratio) > 70 ? "error.main"
                  : stock?.payout_ratio != null && Number(stock.payout_ratio) > 60 ? "warning.main"
                  : "text.primary"
                }
              >
                {stock?.payout_ratio != null ? `${Number(stock.payout_ratio).toFixed(0)}%` : "-"}
              </Typography>
            </Box>
            <Box>
              <Stack direction="row" alignItems="center" spacing={0.25}>
                <Typography variant="caption" color="text.secondary">連続配当</Typography>
                <FinancialTermHelp termKey="consecutive_dividend" />
              </Stack>
              <Typography variant="body1" fontWeight="bold">
                {stock?.consecutive_dividend_years != null ? `${stock.consecutive_dividend_years}年` : "-"}
              </Typography>
            </Box>
            <Box>
              <Stack direction="row" alignItems="center" spacing={0.25}>
                <Typography variant="caption" color="text.secondary">累進配当</Typography>
                <FinancialTermHelp termKey="progressive_dividend" />
              </Stack>
              <Typography variant="body1" fontWeight="bold">
                {stock?.progressive_dividend_years != null ? `${stock.progressive_dividend_years}年` : "-"}
              </Typography>
            </Box>
            <Box>
              <Stack direction="row" alignItems="center" spacing={0.25}>
                <Typography variant="caption" color="text.secondary">オーナー経営</Typography>
                <FinancialTermHelp termKey="owner_managed" />
              </Stack>
              <Typography variant="body1" fontWeight="bold">
                {stock?.is_owner_managed ? (
                  <Chip
                    label={
                      stock.owner_match_type === "exact" ? "代表"
                      : stock.owner_match_type === "family" ? "親族"
                      : "関連"
                    }
                    size="small"
                    color={
                      stock.owner_match_type === "exact" ? "success"
                      : stock.owner_match_type === "family" ? "info"
                      : "warning"
                    }
                  />
                ) : "-"}
              </Typography>
            </Box>
            {stock?.is_owner_managed && stock.owner_ratio && (
              <Box>
                <Typography variant="caption" color="text.secondary">代表持株比率</Typography>
                <Typography variant="body1" fontWeight="bold">
                  {Number(stock.owner_ratio).toFixed(1)}%
                </Typography>
              </Box>
            )}
            <Box>
              <Stack direction="row" alignItems="center" spacing={0.25}>
                <Typography variant="caption" color="text.secondary">FCF利回り</Typography>
                <FinancialTermHelp termKey="fcf_yield" />
              </Stack>
              <Typography
                variant="body1"
                fontWeight="bold"
                color={
                  stock?.fcf_yield != null && Number(stock.fcf_yield) >= 8 ? "success.main"
                  : stock?.fcf_yield != null && Number(stock.fcf_yield) < 0 ? "error.main"
                  : "text.primary"
                }
              >
                {stock?.fcf_yield != null ? `${Number(stock.fcf_yield).toFixed(1)}%` : "-"}
              </Typography>
            </Box>
            <Box>
              <Stack direction="row" alignItems="center" spacing={0.25}>
                <Typography variant="caption" color="text.secondary">FCFマージン</Typography>
                <FinancialTermHelp termKey="fcf_margin" />
              </Stack>
              <Typography variant="body1" fontWeight="bold">
                {stock?.fcf_margin != null ? `${Number(stock.fcf_margin).toFixed(1)}%` : "-"}
              </Typography>
            </Box>
          </Box>
        </CardContent>
      </Card>

      {/* タブ */}
      <Tabs value={tab} onChange={(_e, v) => setTab(v)} variant="scrollable" scrollButtons="auto" sx={{ mb: 2 }}>
        <Tab label="財務データ" />
        <Tab label="株価チャート" />
        <Tab label="信用残高" />
        <Tab label="バリュエーション" />
        <Tab label="AI分析" />
        <Tab label="仮想売買" />
        <Tab label="ニュース" />
      </Tabs>

      {tab === 0 && (
        <>
          <FinancialTable financials={financials ?? []} />
          {manualFinancials && manualFinancials.length > 0 && (
            <Card variant="outlined" sx={{ mt: 2 }}>
              <CardContent>
                <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                  手動入力済み財務データ
                </Typography>
                <Stack spacing={1}>
                  {manualFinancials.map((m) => (
                    <Box
                      key={m.fiscal_year}
                      sx={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        p: 1,
                        borderRadius: 1,
                        bgcolor: m.is_overridden_by_auto ? "action.disabledBackground" : "warning.light",
                        opacity: m.is_overridden_by_auto ? 0.6 : 1,
                      }}
                    >
                      <Stack direction="row" spacing={2} flexWrap="wrap">
                        <Typography variant="body2" fontWeight="bold">{m.fiscal_year}年度</Typography>
                        {m.bps && <Typography variant="body2">BPS: {formatCurrency(Number(m.bps))}</Typography>}
                        {m.eps && <Typography variant="body2">EPS: {formatCurrency(Number(m.eps))}</Typography>}
                        {m.eps_forecast && <Typography variant="body2">予想EPS: {formatCurrency(Number(m.eps_forecast))}</Typography>}
                        <Typography variant="caption" color="text.secondary">{m.source_label} • {m.updated_at.slice(0, 10)}</Typography>
                        {m.is_overridden_by_auto && <Chip label="J-Quants自動データあり" size="small" color="default" />}
                      </Stack>
                      <Button
                        size="small"
                        color="error"
                        onClick={() => {
                          manualFinancialApi.delete(code ?? "", m.fiscal_year).then(() => {
                            queryClient.invalidateQueries({ queryKey: ["stocks", code, "financials", "manual"] });
                          });
                        }}
                      >
                        削除
                      </Button>
                    </Box>
                  ))}
                </Stack>
              </CardContent>
            </Card>
          )}
        </>
      )}

      {tab === 1 && <TechnicalChartGroup code={code ?? ""} />}

      {tab === 2 && <MarginTrendPanel stockCode={code ?? ""} />}

      {tab === 4 && <AiAnalysisPanel stockCode={code ?? ""} />}

      {tab === 5 && (
        <PaperTradePanel
          stockCode={code ?? ""}
          latestPrice={stock?.latest_price ? String(stock.latest_price) : null}
        />
      )}

      {tab === 6 && <StockNewsTab stockCode={code ?? ""} />}

      {tab === 3 && (
        <Stack spacing={2}>
          {/* 簡易計算フォーム */}
          <Card variant="outlined">
            <CardContent>
              <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
                適正株価を算出
              </Typography>
              <Stack direction="row" spacing={2} alignItems="flex-start">
                <Box>
                  <Stack direction="row" alignItems="center" spacing={0.25} sx={{ mb: 0.5 }}>
                    <Typography variant="caption" color="text.secondary">永続成長率</Typography>
                    <FinancialTermHelp termKey="expected_growth_rate" />
                  </Stack>
                  <TextField
                    label="永続成長率 (%)"
                    type="number"
                    size="small"
                    value={calcGrowthRate}
                    onChange={(e) => { setCalcGrowthRate(e.target.value); setCalcError(null); }}
                    helperText="市場折込成長率と同じ概念。日本株は8%未満（目安: 1〜5%）"
                    inputProps={{ step: "0.5", min: "-10", max: "7.9" }}
                    sx={{ width: 280 }}
                  />
                </Box>
                <Button
                  variant="contained"
                  startIcon={<CalculateIcon />}
                  disabled={!calcGrowthRate || calculateMutation.isPending}
                  onClick={() => {
                    if (!code) return;
                    setCalcError(null);
                    calculateMutation.mutate(
                      {
                        stock_code: code,
                        growth_rate: parseFloat(calcGrowthRate) / 100,
                        current_price: latestPrice ? Number(latestPrice.close_price) : undefined,
                      },
                      {
                        onSuccess: () => {
                          queryClient.invalidateQueries({ queryKey: ["stocks", code, "valuations"] });
                        },
                        onError: (err) => {
                          const msg = (err as { response?: { data?: { detail?: string } } })
                            ?.response?.data?.detail ?? "算出に失敗しました";
                          setCalcError(msg);
                        },
                      }
                    );
                  }}
                  sx={{ mt: 0.5 }}
                >
                  {calculateMutation.isPending ? "算出中..." : "算出"}
                </Button>
              </Stack>
              {calcError && (
                <Alert severity="error" sx={{ mt: 1 }}>{calcError}</Alert>
              )}
            </CardContent>
          </Card>

          {/* 最新の計算結果 */}
          {calculateMutation.data && (
            <ResultSummary result={calculateMutation.data} />
          )}

          {/* 計算履歴 */}
          <Card variant="outlined">
            <CardContent>
              <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                算出履歴
              </Typography>
              {valuations && valuations.length > 0 ? (
                <Stack spacing={0}>
                  {valuations.map((v) => (
                    <Box
                      key={v.id}
                      sx={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        p: 1,
                        borderBottom: "1px solid",
                        borderColor: "divider",
                        cursor: "pointer",
                        "&:hover": { bgcolor: "action.hover" },
                      }}
                      onClick={() => navigate(`/valuations/${v.id}`)}
                    >
                      <Stack direction="row" spacing={2}>
                        <Typography variant="body2">
                          成長率: {formatPercent(v.growth_rate)}
                        </Typography>
                        <Typography variant="body2">
                          適正PBR: {formatMultiple(v.fair_pbr)}
                        </Typography>
                        <Typography variant="body2">
                          適正株価: {formatCurrency(v.fair_value)}
                        </Typography>
                      </Stack>
                      <Chip
                        label={v.is_undervalued ? "割安" : "割高"}
                        color={v.is_undervalued ? "success" : "error"}
                        size="small"
                      />
                    </Box>
                  ))}
                </Stack>
              ) : (
                <Typography variant="body2" color="text.secondary" align="center">
                  まだ算出結果がありません。上のフォームから算出してください。
                </Typography>
              )}
            </CardContent>
          </Card>
        </Stack>
      )}

      <ManualFinancialInputModal
        open={manualModalOpen}
        onClose={() => setManualModalOpen(false)}
        stockCode={code ?? ""}
        stockName={stock.name}
      />

      {/* 財務データリセット確認ダイアログ */}
      <Dialog open={resetDialogOpen} onClose={() => setResetDialogOpen(false)}>
        <DialogTitle>財務データのリセット</DialogTitle>
        <DialogContent>
          <DialogContentText>
            <strong>{stock.code} {stock.name}</strong> の財務データ（BPS・EPS等）をすべて削除し、
            J-Quants から再取得します。
          </DialogContentText>
          <DialogContentText sx={{ mt: 1, color: "warning.main" }}>
            ⚠ 再上場・コード再利用時など、旧会社のデータが混在している場合に使用してください。
          </DialogContentText>
          <FormControlLabel
            control={
              <Checkbox
                checked={clearManual}
                onChange={(e) => setClearManual(e.target.checked)}
              />
            }
            label="手動入力データも削除する"
            sx={{ mt: 1 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setResetDialogOpen(false)}>キャンセル</Button>
          <Button
            color="warning"
            variant="contained"
            onClick={() => resetMutation.mutate()}
            disabled={resetMutation.isPending}
          >
            {resetMutation.isPending ? "リセット中..." : "リセットして再取得"}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
