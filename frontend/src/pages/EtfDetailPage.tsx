import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Box,
  Typography,
  Tab,
  Tabs,
  Card,
  CardContent,
  Stack,
  Chip,
  Button,
} from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import IndicatorHelpTooltip, { HELP_TEXTS } from "@/components/stock/IndicatorHelpTooltip";
import { useQuery } from "@tanstack/react-query";
import { useStock, useStockPrices } from "@/hooks/useStocks";
import { etfApi } from "@/api/etf";
import PriceChart from "@/components/stock/PriceChart";
import DividendHistoryPanel from "@/components/stock/DividendHistoryPanel";
import MarginTrendPanel from "@/components/stock/MarginTrendPanel";
import AiAnalysisPanel from "@/components/stock/AiAnalysisPanel";
import LoadingSpinner from "@/components/common/LoadingSpinner";
import ErrorAlert from "@/components/common/ErrorAlert";
import { formatCurrency, formatPercent } from "@/utils/format";
import type { EvaluationSignal } from "@/types/etf";

function getZoneStyle(zone: string | null) {
  switch (zone) {
    case "超割安":   return { color: "#1b5e20", bgColor: "#e8f5e9" };
    case "買い推奨": return { color: "#2e7d32", bgColor: "#c8e6c9" };
    case "レンジ中": return { color: "#f57f17", bgColor: "#fff9c4" };
    case "下落警戒": return { color: "#e65100", bgColor: "#ffe0b2" };
    case "購入危険": return { color: "#b71c1c", bgColor: "#ffcdd2" };
    default:        return { color: "#546e7a", bgColor: "#eceff1" };
  }
}

export default function EtfDetailPage() {
  const { code } = useParams<{ code: string }>();
  const navigate = useNavigate();
  const [tab, setTab] = useState(0);

  const { data: stock, isLoading, error } = useStock(code ?? "");
  const { data: prices } = useStockPrices(code ?? "", 365);
  const { data: etfList } = useQuery({
    queryKey: ["etfList"],
    queryFn: () => etfApi.list().then((r) => r.data),
  });

  if (isLoading) return <LoadingSpinner />;
  if (error || !stock) return <ErrorAlert message="銘柄が見つかりません" />;

  const etfData = etfList?.find((e) => e.code === code);
  const zoneStyle = getZoneStyle(etfData?.evaluation_zone ?? null);

  return (
    <Box>
      <Button
        startIcon={<ArrowBackIcon />}
        onClick={() => navigate("/etf")}
        sx={{ mb: 1 }}
      >
        ETF一覧に戻る
      </Button>

      <Stack direction="row" alignItems="center" spacing={2} sx={{ mb: 2 }}>
        <Typography variant="h5">
          {stock.code} - {stock.name}
        </Typography>
        {stock.sector && (
          <Chip label={stock.sector} size="small" variant="outlined" />
        )}
      </Stack>

      {/* サマリーカード */}
      <Stack direction="row" spacing={2} sx={{ mb: 3 }}>
        <Card sx={{ flex: 1 }}>
          <CardContent>
            <Typography variant="body2" color="text.secondary">最新株価</Typography>
            <Typography variant="h6">
              {etfData?.latest_price ? formatCurrency(Number(etfData.latest_price)) : "-"}
            </Typography>
            {etfData?.latest_price_date && (
              <Typography variant="caption" color="text.secondary">
                {etfData.latest_price_date}
              </Typography>
            )}
          </CardContent>
        </Card>
        <Card sx={{ flex: 1 }}>
          <CardContent>
            <Box sx={{ display: "flex", alignItems: "center" }}>
              <Typography variant="body2" color="text.secondary">分配金利回り</Typography>
              <IndicatorHelpTooltip title={HELP_TEXTS.etfDividendYield} />
            </Box>
            <Typography variant="h6" color={
              etfData?.dividend_yield && Number(etfData.dividend_yield) >= 0.03
                ? "success.main" : "text.primary"
            }>
              {etfData?.dividend_yield ? formatPercent(Number(etfData.dividend_yield)) : "-"}
            </Typography>
          </CardContent>
        </Card>
        <Card sx={{ flex: 1 }}>
          <CardContent>
            <Typography variant="body2" color="text.secondary">年間分配金</Typography>
            <Typography variant="h6">
              {etfData?.annual_dividend ? formatCurrency(Number(etfData.annual_dividend)) : "-"}
            </Typography>
          </CardContent>
        </Card>
        <Card sx={{ flex: 1 }}>
          <CardContent>
            <Box sx={{ display: "flex", alignItems: "center" }}>
              <Typography variant="body2" color="text.secondary">52週リターン</Typography>
              <IndicatorHelpTooltip title={HELP_TEXTS.etfReturn52w} />
            </Box>
            <Typography variant="h6" color={
              etfData?.return_52w
                ? Number(etfData.return_52w) >= 0 ? "success.main" : "error.main"
                : "text.primary"
            }>
              {etfData?.return_52w ? formatPercent(Number(etfData.return_52w)) : "-"}
            </Typography>
          </CardContent>
        </Card>
      </Stack>

      {/* 総合評価 */}
      {etfData?.evaluation_zone && (
        <Card variant="outlined" sx={{ mb: 3, borderColor: zoneStyle.color, borderWidth: 2 }}>
          <CardContent>
            <Box sx={{ display: "flex", alignItems: "center", mb: 1 }}>
              <Typography variant="subtitle2" color="text.secondary">
                総合評価
              </Typography>
              <IndicatorHelpTooltip title={HELP_TEXTS.etfEvaluationZone} />
            </Box>
            <Box sx={{ display: "flex", gap: 3, alignItems: "flex-start" }}>
              <Box
                sx={{
                  minWidth: 120,
                  px: 3,
                  py: 2,
                  borderRadius: 2,
                  bgcolor: zoneStyle.bgColor,
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  flexShrink: 0,
                }}
              >
                <Typography variant="h5" fontWeight="bold" color={zoneStyle.color}>
                  {etfData.evaluation_zone}
                </Typography>
                <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5 }}>
                  スコア: {(etfData.evaluation_score ?? 0) > 0 ? "+" : ""}{etfData.evaluation_score}
                </Typography>
              </Box>

              <Box sx={{ flex: 1 }}>
                <Typography variant="caption" color="text.secondary" gutterBottom display="block">
                  評価根拠
                </Typography>
                <Stack spacing={0.5}>
                  {etfData.evaluation_signals.map((sig: EvaluationSignal) => {
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
                        <Typography variant="caption" color="text.secondary" sx={{ minWidth: 90 }}>
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
      )}

      {/* タブ */}
      <Tabs value={tab} onChange={(_e, v) => setTab(v)} sx={{ mb: 2 }}>
        <Tab label="株価チャート" />
        <Tab label="分配金履歴" />
        <Tab label="信用残高" />
        <Tab label="AI分析" />
      </Tabs>

      {tab === 0 && <PriceChart prices={prices ?? []} />}
      {tab === 1 && <DividendHistoryPanel stockCode={code ?? ""} />}
      {tab === 2 && <MarginTrendPanel stockCode={code ?? ""} />}
      {tab === 3 && <AiAnalysisPanel stockCode={code ?? ""} />}
    </Box>
  );
}
