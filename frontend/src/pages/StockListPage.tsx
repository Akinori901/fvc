import { useState, useMemo, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  Badge,
  Box,
  Typography,
  Button,
  Chip,
  Stack,
  Slider,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  IconButton,
  InputAdornment,
  Tooltip,
} from "@mui/material";
import { DataGrid, type GridColDef } from "@mui/x-data-grid";
import SyncIcon from "@mui/icons-material/Sync";
import SearchIcon from "@mui/icons-material/Search";
import ListIcon from "@mui/icons-material/List";
import TuneIcon from "@mui/icons-material/Tune";
import StarIcon from "@mui/icons-material/Star";
import StarBorderIcon from "@mui/icons-material/StarBorder";
import { useScreening } from "@/hooks/useScreening";
import { useSyncTrigger } from "@/hooks/useSync";
import { useWatchlist, useAddToWatchlist, useRemoveFromWatchlist } from "@/hooks/useWatchlist";
import { useScreeningPresets, useSaveScreeningPreset, useDeleteScreeningPreset } from "@/hooks/useScreeningPresets";
import EvaluationBadge from "@/components/common/EvaluationBadge";
import ScreeningFilterModal from "@/components/screening/ScreeningFilterModal";
import PresetSelector from "@/components/screening/PresetSelector";
import { computeOverallRating } from "@/utils/overallRating";
import { formatCurrency, formatPercent, formatMultiple } from "@/utils/format";
import type { ScreeningResult } from "@/types/screening";
import type { ScreeningFilters } from "@/types/screeningPreset";
import { DEFAULT_FILTERS } from "@/types/screeningPreset";

const REASON_LABELS: Record<string, string> = {
  growth_ge_cost: "成長率≧資本コスト（ゴードンモデル計算不可）",
  no_price: "株価データなし",
  no_financial: "財務データなし",
  bps_invalid: "BPS無効（0以下）",
  roe_not_positive: "ROE≤0（ゴードンモデル計算不可）",
  roe_le_growth: "ROE≦成長率（ゴードンモデル計算不可）",
};

export default function StockListPage() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<"list" | "screening">("list");
  const [growthRate, setGrowthRate] = useState(3);
  const [searchText, setSearchText] = useState("");
  const [filters, setFilters] = useState<ScreeningFilters>(DEFAULT_FILTERS);
  const [filterModalOpen, setFilterModalOpen] = useState(false);
  const [selectedPresetId, setSelectedPresetId] = useState<number | null>(null);

  // プリセット
  const { data: presets } = useScreeningPresets();
  const savePresetMutation = useSaveScreeningPreset();
  const deletePresetMutation = useDeleteScreeningPreset();

  // 初回: 最も優先度の高いプリセットを自動適用
  useEffect(() => {
    if (presets && presets.length > 0 && selectedPresetId === null) {
      const top = presets[0];
      if (top) {
        setSelectedPresetId(top.id);
        setFilters(top.filters);
        setGrowthRate((top.filters.growth_rate ?? 0.03) * 100);
      }
    }
  }, [presets]); // eslint-disable-line react-hooks/exhaustive-deps

  // フィルターをAPIパラメータに変換
  const apiParams = useMemo(() => {
    if (mode !== "screening") {
      return { growth_rate: growthRate / 100, include_inactive: filters.include_inactive };
    }
    return {
      growth_rate: growthRate / 100,
      sector: filters.sector ?? undefined,
      include_inactive: filters.include_inactive,
      roe_trend: filters.roe_trend ?? undefined,
      min_eps_growth_yoy: filters.min_eps_growth_yoy ?? undefined,
      min_eps_cagr_3y: filters.min_eps_cagr_3y ?? undefined,
      min_roe: filters.min_roe ?? undefined,
      min_discount: filters.min_discount ?? undefined,
      max_sl_ratio: filters.max_sl_ratio ?? undefined,
      min_dividend_yield: filters.min_dividend_yield ?? undefined,
      max_payout_ratio: filters.max_payout_ratio ?? undefined,
      min_consecutive_dividend_years: filters.min_consecutive_dividend_years ?? undefined,
      min_progressive_dividend_years: filters.min_progressive_dividend_years ?? undefined,
      min_liquidity_level: filters.min_liquidity_level ?? undefined,
      min_momentum_signal: filters.min_momentum_signal ?? undefined,
      owner_managed_only: filters.owner_managed_only || undefined,
      min_fcf_yield: filters.min_fcf_yield ?? undefined,
      long_balance_trend: filters.long_balance_trend ?? undefined,
      // トレンド未指定のときは期間・閾値を送らない（不要な履歴取得を避ける）
      margin_trend_months: filters.long_balance_trend ? filters.margin_trend_months : undefined,
      margin_trend_threshold_pct: filters.long_balance_trend
        ? (filters.margin_trend_threshold_pct ?? undefined)
        : undefined,
    };
  }, [mode, growthRate, filters]);

  const { data: screeningResults, isLoading: screeningLoading } = useScreening(apiParams);
  const syncMutation = useSyncTrigger();

  const { data: watchlist } = useWatchlist();
  const addToWatchlist = useAddToWatchlist();
  const removeFromWatchlist = useRemoveFromWatchlist();

  const watchlistCodes = useMemo(
    () => new Set((watchlist ?? []).map((w) => w.stock_code)),
    [watchlist]
  );

  const sectors = screeningResults
    ? [...new Set(screeningResults.map((s) => s.sector).filter(Boolean))].sort()
    : [];

  // アクティブフィルター数（デフォルトと異なるフィールド数）
  const activeFilterCount = useMemo(() => {
    let count = 0;
    const d = DEFAULT_FILTERS;
    if (filters.sector !== d.sector) count++;
    if (filters.include_inactive !== d.include_inactive) count++;
    if (filters.min_discount !== d.min_discount) count++;
    if (filters.min_eps_growth_yoy !== d.min_eps_growth_yoy) count++;
    if (filters.min_eps_cagr_3y !== d.min_eps_cagr_3y) count++;
    if (filters.roe_trend !== d.roe_trend) count++;
    if (filters.min_roe !== d.min_roe) count++;
    if (filters.max_sl_ratio !== d.max_sl_ratio) count++;
    if (filters.min_dividend_yield !== d.min_dividend_yield) count++;
    if (filters.max_payout_ratio !== d.max_payout_ratio) count++;
    if (filters.min_consecutive_dividend_years !== d.min_consecutive_dividend_years) count++;
    if (filters.min_progressive_dividend_years !== d.min_progressive_dividend_years) count++;
    if (filters.min_liquidity_level !== d.min_liquidity_level) count++;
    if (filters.min_momentum_signal !== d.min_momentum_signal) count++;
    if (filters.owner_managed_only !== d.owner_managed_only) count++;
    if (filters.min_fcf_yield !== d.min_fcf_yield) count++;
    if (filters.min_overall_score !== d.min_overall_score) count++;
    // 期間・閾値はトレンド指定とセットで意味を持つため、トレンドのみを1件として数える
    if (filters.long_balance_trend !== d.long_balance_trend) count++;
    return count;
  }, [filters]);

  const filteredResults = useMemo(() => {
    let results = screeningResults ?? [];
    if (searchText.trim()) {
      const q = searchText.toLowerCase();
      results = results.filter(
        (r) => r.code.toLowerCase().includes(q) || r.name.toLowerCase().includes(q)
      );
    }
    // min_overall_score はフロントエンド側でフィルタリング
    if (mode === "screening" && filters.min_overall_score != null) {
      const threshold = filters.min_overall_score;
      results = results.filter((r: ScreeningResult) => {
        const rating = computeOverallRating({
          evaluationZone: r.evaluation_zone ?? null,
          growthRateLabel: r.growth_rate_label ?? null,
          roeTrend: r.roe_trend ?? null,
          epsCagr3y: r.eps_cagr_3y != null ? Number(r.eps_cagr_3y) : null,
          epsGrowthYoy: r.eps_growth_yoy != null ? Number(r.eps_growth_yoy) : null,
          slRatio: r.sl_ratio != null ? Number(r.sl_ratio) : null,
          momentumSignal: r.momentum_signal ?? null,
          dividendYield: r.dividend_yield != null ? Number(r.dividend_yield) : null,
          payoutRatio: r.payout_ratio != null ? Number(r.payout_ratio) : null,
          consecutiveDividendYears: r.consecutive_dividend_years,
          progressiveDividendYears: r.progressive_dividend_years,
          fcfYield: r.fcf_yield != null ? Number(r.fcf_yield) : null,
          fcfMargin: r.fcf_margin != null ? Number(r.fcf_margin) : null,
          fcf: r.fcf,
        });
        return rating.score >= threshold;
      });
    }
    return results;
  }, [screeningResults, searchText, mode, filters.min_overall_score]);

  const headerWithTooltip = (label: string, tooltip: string) => () => (
    <Tooltip title={tooltip} arrow placement="top">
      <span style={{ cursor: "help" }}>{label}</span>
    </Tooltip>
  );

  const columns: GridColDef<ScreeningResult>[] = [
    {
      field: "watchlist",
      headerName: "",
      width: 50,
      sortable: false,
      renderCell: (params) => {
        const isWatched = watchlistCodes.has(params.row.code);
        return (
          <IconButton
            size="small"
            onClick={(e) => {
              e.stopPropagation();
              if (isWatched) {
                removeFromWatchlist.mutate(params.row.code);
              } else {
                addToWatchlist.mutate({ stock_code: params.row.code });
              }
            }}
          >
            {isWatched ? (
              <StarIcon fontSize="small" color="warning" />
            ) : (
              <StarBorderIcon fontSize="small" />
            )}
          </IconButton>
        );
      },
    },
    { field: "code", headerName: "コード", width: 90 },
    {
      field: "overall_rating",
      headerName: "総合評価",
      width: 110,
      valueGetter: (_value: unknown, row: ScreeningResult) => {
        return computeOverallRating({
          evaluationZone: row.evaluation_zone ?? null,
          growthRateLabel: row.growth_rate_label ?? null,
          roeTrend: row.roe_trend ?? null,
          epsCagr3y: row.eps_cagr_3y != null ? Number(row.eps_cagr_3y) : null,
          epsGrowthYoy: row.eps_growth_yoy != null ? Number(row.eps_growth_yoy) : null,
          slRatio: row.sl_ratio != null ? Number(row.sl_ratio) : null,
          momentumSignal: row.momentum_signal ?? null,
          dividendYield: row.dividend_yield != null ? Number(row.dividend_yield) : null,
          payoutRatio: row.payout_ratio != null ? Number(row.payout_ratio) : null,
          consecutiveDividendYears: row.consecutive_dividend_years,
          progressiveDividendYears: row.progressive_dividend_years,
          fcfYield: row.fcf_yield != null ? Number(row.fcf_yield) : null,
          fcfMargin: row.fcf_margin != null ? Number(row.fcf_margin) : null,
          fcf: row.fcf,
        }).score;
      },
      renderHeader: headerWithTooltip(
        "総合評価",
        "バリュエーション・成長率評価・ROEトレンド・EPS成長・信売比率・モメンタム・配当評価を合算したスコアから5段階評価。" +
          "配当評価: 高配当+健全性向+累進配当で加点、高配当+高性向で減点、無配で減点。"
      ),
      renderCell: (params) => {
        const row = params.row;
        const result = computeOverallRating({
          evaluationZone: row.evaluation_zone ?? null,
          growthRateLabel: row.growth_rate_label ?? null,
          roeTrend: row.roe_trend ?? null,
          epsCagr3y: row.eps_cagr_3y != null ? Number(row.eps_cagr_3y) : null,
          epsGrowthYoy: row.eps_growth_yoy != null ? Number(row.eps_growth_yoy) : null,
          slRatio: row.sl_ratio != null ? Number(row.sl_ratio) : null,
          momentumSignal: row.momentum_signal ?? null,
          dividendYield: row.dividend_yield != null ? Number(row.dividend_yield) : null,
          payoutRatio: row.payout_ratio != null ? Number(row.payout_ratio) : null,
          consecutiveDividendYears: row.consecutive_dividend_years,
          progressiveDividendYears: row.progressive_dividend_years,
          fcfYield: row.fcf_yield != null ? Number(row.fcf_yield) : null,
          fcfMargin: row.fcf_margin != null ? Number(row.fcf_margin) : null,
          fcf: row.fcf,
        });
        return (
          <Chip
            label={result.label}
            size="small"
            sx={{ color: result.color, bgcolor: result.bgColor, fontWeight: "bold", fontSize: "0.7rem" }}
          />
        );
      },
    },
    {
      field: "name",
      headerName: "銘柄名",
      flex: 1,
      minWidth: 160,
      renderCell: (params) => (
        <Stack direction="row" spacing={0.5} alignItems="center">
          <span>{params.value}</span>
          {!params.row.is_active && (
            <Chip label="上場廃止" size="small" color="default" sx={{ fontSize: "0.65rem", height: 18 }} />
          )}
        </Stack>
      ),
    },
    { field: "sector", headerName: "セクター", width: 150 },
    {
      field: "latest_price",
      headerName: "株価",
      width: 110,
      renderHeader: headerWithTooltip("株価", "直近の終値（権利落ち調整後）"),
      renderCell: (params) =>
        params.value != null ? formatCurrency(Number(params.value)) : "-",
    },
    {
      field: "fair_value",
      headerName: "適正株価",
      width: 110,
      renderHeader: headerWithTooltip(
        "適正株価",
        "ゴードン成長モデルによる理論株価 = BPS × 適正PBR。負値の場合、いかなる正の価格でも割高を意味する"
      ),
      renderCell: (params) => {
        if (params.value != null) return formatCurrency(Number(params.value));
        const reason = REASON_LABELS[params.row.not_calculable_reason as string] ?? "計算不可";
        return (
          <Tooltip title={reason} arrow>
            <Typography variant="body2" color="text.disabled" sx={{ cursor: "help" }}>
              -
            </Typography>
          </Tooltip>
        );
      },
    },
    {
      field: "discount_rate",
      headerName: "乖離率",
      width: 100,
      renderHeader: headerWithTooltip(
        "乖離率",
        "(適正株価 − 現在株価) ÷ 適正株価。正値＝割安、負値＝割高"
      ),
      renderCell: (params) => {
        if (params.value == null) return "-";
        const val = Number(params.value);
        return (
          <Typography
            variant="body2"
            color={val >= 0 ? "success.main" : "error.main"}
            fontWeight="bold"
          >
            {formatPercent(val)}
          </Typography>
        );
      },
    },
    {
      field: "evaluation_zone",
      headerName: "評価",
      width: 100,
      renderHeader: headerWithTooltip(
        "評価",
        "乖離率に基づく評価ゾーン（超割安 / 割安 / 適正 / 割高 / 危険）。適正株価が負の場合は「危険」固定"
      ),
      renderCell: (params) =>
        params.row.evaluation_zone != null ? (
          <EvaluationBadge zone={params.row.evaluation_zone} />
        ) : (
          "-"
        ),
    },
    {
      field: "current_pbr",
      headerName: "現在PBR",
      width: 100,
      renderHeader: headerWithTooltip(
        "現在PBR",
        "現在株価 ÷ BPS（1株純資産）。株式分割調整済み"
      ),
      renderCell: (params) =>
        params.value != null ? formatMultiple(Number(params.value)) : "-",
    },
    {
      field: "implied_growth_rate",
      headerName: "市場折込成長率",
      width: 130,
      renderHeader: headerWithTooltip(
        "市場折込成長率",
        "現在のPBRが織り込む永続成長率。計算式：(PBR × 資本コスト − ROE) ÷ (PBR − 1)。" +
          "高いほど「市場が高い成長を期待している＝期待外れ時の下落リスクが大きい」。" +
          "低い・マイナスは「市場の期待が低い＝好業績で株価上昇余地がある」ことを示す。" +
          "PBR ≈ 1 の銘柄や計算値が資本コスト（8%）以上となる銘柄（PBR < 1 かつ高ROE等）はゴードンモデルの適用外のため「-」表示。"
      ),
      renderCell: (params) =>
        params.value != null ? formatPercent(Number(params.value)) : "-",
    },
    {
      field: "growth_rate_label",
      headerName: "成長率評価",
      width: 110,
      renderHeader: headerWithTooltip(
        "成長率評価",
        "市場が株価に織り込んでいる永続成長率の評価。" +
          "「かなり強気（≥7%）」は市場が高成長を期待しており期待を裏切ると大幅下落リスク。" +
          "「非常に優秀（5〜7%）」も高い期待値で注意が必要。" +
          "「優秀（3〜5%）」は標準的な成長株評価。" +
          "「普通（2〜3%）」はGDP成長並みの期待で安定評価。" +
          "「低成長（0〜2%）」は市場が低成長しか期待しておらず割安の可能性。" +
          "「マイナス成長（<0%）」は市場が縮小を織り込んでいる。" +
          "ラベルが強気ほど「すでに期待が高すぎる」リスクを示す。" +
          "「ROE持続性に疑念」はPBR < 1 かつ計算値 ≥ 資本コスト（8%）の場合で、" +
          "市場が現在の高ROEは維持されないと見ていることを示す（割安でも慎重な検証が必要）。"
      ),
      renderCell: (params) =>
        params.value ? (
          <Chip label={params.value} size="small" variant="outlined" />
        ) : (
          "-"
        ),
    },
    {
      field: "company_forecast_growth_rate",
      headerName: "会社予想成長率",
      width: 130,
      renderHeader: headerWithTooltip(
        "会社予想成長率",
        "(会社予想EPS − 実績EPS) ÷ |実績EPS|。会社が開示した翌期EPS予想に基づく"
      ),
      renderCell: (params) =>
        params.value != null ? formatPercent(Number(params.value)) : "-",
    },
    {
      field: "roe",
      headerName: "ROE",
      width: 80,
      renderHeader: headerWithTooltip(
        "ROE",
        "自己資本利益率 = EPS ÷ BPS。ゴードン成長モデルの中心指標。正値の企業のみ適正株価を計算"
      ),
      renderCell: (params) =>
        params.value ? formatPercent(Number(params.value)) : "-",
    },
    {
      field: "eps_growth_yoy",
      headerName: "EPS成長(前年比)",
      width: 120,
      renderHeader: headerWithTooltip(
        "EPS成長(前年比)",
        "1株利益（EPS）の前年比成長率"
      ),
      renderCell: (params) => {
        if (params.value == null) return "-";
        const val = Number(params.value);
        return (
          <Typography variant="body2" color={val >= 0 ? "success.main" : "error.main"}>
            {formatPercent(val)}
          </Typography>
        );
      },
    },
    {
      field: "eps_cagr_3y",
      headerName: "EPS CAGR(3年)",
      width: 120,
      renderHeader: headerWithTooltip(
        "EPS CAGR(3年)",
        "3年間のEPS年平均成長率（Compound Annual Growth Rate）"
      ),
      renderCell: (params) => {
        if (params.value == null) return "-";
        const val = Number(params.value);
        return (
          <Typography variant="body2" color={val >= 0 ? "success.main" : "error.main"}>
            {formatPercent(val)}
          </Typography>
        );
      },
    },
    {
      field: "roe_trend",
      headerName: "ROEトレンド",
      width: 100,
      renderHeader: headerWithTooltip(
        "ROEトレンド",
        "直近3期のROE推移（↑改善 / →横ばい / ↓悪化）"
      ),
      renderCell: (params) => {
        const trend = params.value as string | null;
        if (!trend) return "-";
        const map: Record<string, { label: string; color: "success" | "default" | "error" }> = {
          improving: { label: "↑改善", color: "success" },
          stable: { label: "→横ばい", color: "default" },
          declining: { label: "↓悪化", color: "error" },
        };
        const { label, color } = map[trend] ?? { label: trend, color: "default" };
        return <Chip label={label} size="small" color={color} />;
      },
    },
    {
      field: "revenue_growth_yoy",
      headerName: "売上高成長率",
      width: 110,
      renderHeader: headerWithTooltip("売上高成長率", "売上高の前年比成長率"),
      renderCell: (params) => {
        if (params.value == null) return "-";
        const val = Number(params.value);
        return (
          <Typography variant="body2" color={val >= 0 ? "success.main" : "error.main"}>
            {formatPercent(val)}
          </Typography>
        );
      },
    },
    {
      field: "sl_ratio",
      headerName: "信売比率",
      width: 90,
      renderHeader: headerWithTooltip(
        "信売比率",
        "信用売残 ÷ 信用買残。2倍以上は空売り圧力が強い目安"
      ),
      renderCell: (params) => {
        if (params.value == null) return "-";
        const val = Number(params.value);
        const color = val >= 2.0 ? "error.main" : val >= 1.0 ? "warning.main" : "text.primary";
        return (
          <Tooltip title={`信用売残 ÷ 信用買残 = ${val.toFixed(2)}倍`} arrow>
            <Typography variant="body2" color={color} fontWeight={val >= 2.0 ? "bold" : "normal"}>
              {val.toFixed(2)}
            </Typography>
          </Tooltip>
        );
      },
    },
    {
      field: "short_balance",
      headerName: "信用売残(万株)",
      width: 120,
      renderHeader: headerWithTooltip(
        "信用売残(万株)",
        "空売り（信用売り）残高（万株）。増加傾向は売り圧力↑"
      ),
      renderCell: (params) => {
        if (params.value == null) return "-";
        const val = Number(params.value);
        return (
          <Stack direction="row" spacing={0.5} alignItems="center">
            <Typography variant="body2">{(val / 10000).toFixed(1)}</Typography>
          </Stack>
        );
      },
    },
    {
      field: "long_balance",
      headerName: "信用買残(万株)",
      width: 120,
      renderHeader: headerWithTooltip(
        "信用買残(万株)",
        "信用買い残高（万株）。増加傾向は買い需要↑"
      ),
      renderCell: (params) => {
        if (params.value == null) return "-";
        const val = Number(params.value);
        return (
          <Typography variant="body2">{(val / 10000).toFixed(1)}</Typography>
        );
      },
    },
    {
      field: "momentum_signal",
      headerName: "モメンタム",
      width: 110,
      renderHeader: headerWithTooltip(
        "モメンタム",
        "52週高値効果に基づく総合シグナル。52週レンジ内位置・出来高比率・25日MA乖離率から判定。" +
          "strong_buy=高値圏+出来高急増、buy=上昇トレンド確認、neutral=中間、caution=下落トレンド、sell=底値圏"
      ),
      renderCell: (params) => {
        const signal = params.value as string | null;
        if (!signal) return "-";
        const map: Record<string, { label: string; color: "success" | "info" | "default" | "warning" | "error" }> = {
          strong_buy: { label: "強買い", color: "success" },
          buy: { label: "買い", color: "info" },
          neutral: { label: "中立", color: "default" },
          caution: { label: "注意", color: "warning" },
          sell: { label: "売り", color: "error" },
        };
        const { label, color } = map[signal] ?? { label: signal, color: "default" as const };
        return <Chip label={label} size="small" color={color} />;
      },
    },
    {
      field: "price_position_52w",
      headerName: "52w位置",
      width: 90,
      renderHeader: headerWithTooltip(
        "52w位置",
        "52週レンジ内の位置（0%=安値、100%=高値）。95%以上で52週高値近接"
      ),
      renderCell: (params) => {
        if (params.value == null) return "-";
        const val = Number(params.value);
        const pct = (val * 100).toFixed(0);
        const color = val >= 0.95 ? "success.main" : val >= 0.80 ? "info.main" : val <= 0.20 ? "error.main" : "text.primary";
        return (
          <Typography variant="body2" color={color} fontWeight={val >= 0.95 ? "bold" : "normal"}>
            {pct}%
          </Typography>
        );
      },
    },
    {
      field: "ma_25_deviation",
      headerName: "25日MA乖離",
      width: 100,
      renderHeader: headerWithTooltip(
        "25日MA乖離",
        "25日移動平均線からの乖離率。正=上方乖離（上昇トレンド）、負=下方乖離（下落トレンド）"
      ),
      renderCell: (params) => {
        if (params.value == null) return "-";
        const val = Number(params.value);
        return (
          <Typography variant="body2" color={val >= 0 ? "success.main" : "error.main"}>
            {formatPercent(val)}
          </Typography>
        );
      },
    },
    {
      field: "liquidity_level",
      headerName: "流動性",
      width: 80,
      renderHeader: headerWithTooltip(
        "流動性",
        "売買代金（出来高×株価）の20日平均。高(≥10億), 中(≥1億), 低(≥1千万), 極低(<1千万)"
      ),
      renderCell: (params) => {
        const level = params.value as string | null;
        if (!level) return "-";
        const map: Record<string, { label: string; color: "success" | "info" | "warning" | "error" }> = {
          high: { label: "高", color: "success" },
          medium: { label: "中", color: "info" },
          low: { label: "低", color: "warning" },
          very_low: { label: "極低", color: "error" },
        };
        const { label, color } = map[level] ?? { label: level, color: "warning" as const };
        return <Chip label={label} size="small" color={color} />;
      },
    },
    {
      field: "avg_turnover_20d",
      headerName: "売買代金",
      width: 100,
      renderHeader: headerWithTooltip(
        "売買代金",
        "売買代金（出来高×株価）の20日平均。流動性の目安"
      ),
      renderCell: (params) => {
        if (params.value == null) return "-";
        const val = Number(params.value);
        const text = val >= 100_000_000
          ? `${(val / 100_000_000).toFixed(1)}億`
          : `${(val / 10_000).toFixed(0)}万`;
        return <Typography variant="body2">{text}</Typography>;
      },
    },
    {
      field: "dividend_yield",
      headerName: "配当利回り",
      width: 90,
      renderHeader: headerWithTooltip("配当利回り", "直近12ヶ月の年間配当 ÷ 株価 × 100"),
      renderCell: (params) => {
        if (params.value == null) return "-";
        return <Typography variant="body2">{Number(params.value).toFixed(1)}%</Typography>;
      },
    },
    {
      field: "payout_ratio",
      headerName: "配当性向",
      width: 90,
      renderHeader: headerWithTooltip("配当性向", "年間配当 ÷ EPS × 100。30-60%が健全、70%超は減配リスク"),
      renderCell: (params) => {
        if (params.value == null) return "-";
        const val = Number(params.value);
        const color = val > 70 ? "error.main" : val > 60 ? "warning.main" : "text.primary";
        return <Typography variant="body2" color={color}>{val.toFixed(0)}%</Typography>;
      },
    },
    {
      field: "consecutive_dividend_years",
      headerName: "連続配当",
      width: 80,
      renderHeader: headerWithTooltip("連続配当", "何年連続で配当を出しているか"),
      renderCell: (params) => {
        if (params.value == null) return "-";
        return <Typography variant="body2">{params.value}年</Typography>;
      },
    },
    {
      field: "progressive_dividend_years",
      headerName: "累進配当",
      width: 80,
      renderHeader: headerWithTooltip("累進配当", "何年連続で減配していないか（維持or増配）"),
      renderCell: (params) => {
        if (params.value == null) return "-";
        return <Typography variant="body2">{params.value}年</Typography>;
      },
    },
    {
      field: "fcf_yield",
      headerName: "FCF利回り",
      width: 90,
      renderHeader: headerWithTooltip("FCF利回り", "FCF ÷ 時価総額 × 100。PERより実態に近い割安度指標"),
      renderCell: (params) => {
        if (params.value == null) return "-";
        const val = Number(params.value);
        const color = val >= 8 ? "success.main" : val >= 5 ? "info.main" : val < 0 ? "error.main" : "text.primary";
        return <Typography variant="body2" color={color}>{val.toFixed(1)}%</Typography>;
      },
    },
    {
      field: "fcf_margin",
      headerName: "FCFマージン",
      width: 100,
      renderHeader: headerWithTooltip("FCFマージン", "FCF ÷ 売上高 × 100。収益の質を示す"),
      renderCell: (params) => {
        if (params.value == null) return "-";
        const val = Number(params.value);
        return <Typography variant="body2">{val.toFixed(1)}%</Typography>;
      },
    },
    {
      field: "long_balance_change_pct",
      headerName: "買残増減",
      width: 100,
      renderHeader: headerWithTooltip(
        "買残増減",
        "指定期間の信用買残の変化率。買残の減少は将来の売り圧力の低下を意味する"
      ),
      renderCell: (params) => {
        if (params.value == null) return "-";
        const val = Number(params.value);
        // 買残の減少（マイナス）は需給改善なので good 扱い
        const color = val < 0 ? "success.main" : val > 0 ? "error.main" : "text.secondary";
        return (
          <Typography variant="body2" color={color}>
            {val > 0 ? "+" : ""}
            {val.toFixed(1)}%
          </Typography>
        );
      },
    },
    {
      field: "owner_match_type",
      headerName: "オーナー",
      width: 85,
      renderHeader: headerWithTooltip(
        "オーナー",
        "EDINET有報から代表者が大株主に含まれるかを判定。代表=完全一致、親族=同姓、関連=資産管理会社候補"
      ),
      renderCell: (params) => {
        const row = params.row;
        if (!row.is_owner_managed) return "-";
        const map: Record<string, { label: string; color: "success" | "info" | "warning" }> = {
          exact: { label: "代表", color: "success" },
          family: { label: "親族", color: "info" },
          company: { label: "関連", color: "warning" },
        };
        const mt = row.owner_match_type ?? "company";
        const { label, color } = map[mt] ?? { label: mt, color: "warning" as const };
        return <Chip label={label} size="small" color={color} />;
      },
    },
    {
      field: "owner_ratio",
      headerName: "代表持株",
      width: 85,
      renderHeader: headerWithTooltip("代表持株", "代表者関連の持ち株比率合計 (%)"),
      renderCell: (params) => {
        if (params.value == null) return "-";
        return <Typography variant="body2">{Number(params.value).toFixed(1)}%</Typography>;
      },
    },
  ];

  return (
    <Box>
      <Stack
        direction="row"
        justifyContent="space-between"
        alignItems="center"
        sx={{ mb: 2 }}
      >
        <Typography variant="h5">銘柄一覧</Typography>
        <Stack direction="row" spacing={1}>
          <ToggleButtonGroup
            value={mode}
            exclusive
            onChange={(_, v) => v && setMode(v)}
            size="small"
          >
            <ToggleButton value="list">
              <ListIcon sx={{ mr: 0.5 }} fontSize="small" />
              一覧
            </ToggleButton>
            <ToggleButton value="screening">
              <SearchIcon sx={{ mr: 0.5 }} fontSize="small" />
              スクリーニング
            </ToggleButton>
          </ToggleButtonGroup>
          <Button
            variant="outlined"
            startIcon={<SyncIcon />}
            onClick={() => syncMutation.mutate({ sync_type: "financials" })}
            disabled={syncMutation.isPending}
          >
            {syncMutation.isPending ? "同期中..." : "財務データ同期"}
          </Button>
          <Button
            variant="outlined"
            startIcon={<SyncIcon />}
            onClick={() => syncMutation.mutate({ sync_type: "stocks" })}
            disabled={syncMutation.isPending}
          >
            {syncMutation.isPending ? "同期中..." : "銘柄同期"}
          </Button>
        </Stack>
      </Stack>

      <Stack direction="row" spacing={2} alignItems="center" sx={{ mb: 2 }} flexWrap="wrap" useFlexGap>
        <TextField
          size="small"
          placeholder="コード・銘柄名で検索"
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          sx={{ width: 240 }}
          slotProps={{
            input: {
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon fontSize="small" sx={{ color: "text.secondary" }} />
                </InputAdornment>
              ),
            },
          }}
        />
        <Box sx={{ width: 280 }}>
          <Typography variant="body2" gutterBottom>
            名目GDP見込み成長率: {growthRate}%
          </Typography>
          <Slider
            value={growthRate}
            onChange={(_, v) => setGrowthRate(v as number)}
            min={0}
            max={7}
            step={0.5}
            marks={[
              { value: 0, label: "0%" },
              { value: 2, label: "2%" },
              { value: 5, label: "5%" },
              { value: 7, label: "7%" },
            ]}
            valueLabelDisplay="auto"
            valueLabelFormat={(v) => `${v}%`}
          />
        </Box>
        {mode === "screening" && (
          <>
            <PresetSelector
              presets={presets ?? []}
              selectedPresetId={selectedPresetId}
              onSelect={(id, f) => {
                setSelectedPresetId(id);
                if (f) {
                  setFilters(f);
                  setGrowthRate((f.growth_rate ?? 0.03) * 100);
                } else {
                  setFilters(DEFAULT_FILTERS);
                  setGrowthRate(3);
                }
              }}
              onSave={(name, priority) => {
                savePresetMutation.mutate({
                  name,
                  priority,
                  filters: { ...filters, growth_rate: growthRate / 100 },
                });
              }}
              onDelete={(id) => {
                deletePresetMutation.mutate(id);
                if (selectedPresetId === id) {
                  setSelectedPresetId(null);
                  setFilters(DEFAULT_FILTERS);
                }
              }}
            />
            <Badge badgeContent={activeFilterCount} color="primary">
              <Button
                variant="outlined"
                startIcon={<TuneIcon />}
                onClick={() => setFilterModalOpen(true)}
                size="small"
              >
                フィルター設定
              </Button>
            </Badge>
          </>
        )}
        {filteredResults.length > 0 && (
          <Typography variant="body2" color="text.secondary">
            {filteredResults.length} 銘柄
            {searchText.trim() && screeningResults && filteredResults.length !== screeningResults.length
              ? ` / ${screeningResults.length} 件中`
              : ""}
          </Typography>
        )}
      </Stack>

      <ScreeningFilterModal
        open={filterModalOpen}
        onClose={() => setFilterModalOpen(false)}
        filters={filters}
        onApply={setFilters}
        sectors={sectors}
      />

      <DataGrid
        rows={filteredResults}
        columns={columns}
        getRowId={(row) => row.code}
        loading={screeningLoading}
        initialState={{
          pagination: { paginationModel: { pageSize: 25 } },
          sorting: { sortModel: [{ field: "overall_rating", sort: "desc" }] },
        }}
        pageSizeOptions={[25, 50, 100]}
        disableRowSelectionOnClick
        onRowClick={(params) => navigate(`/stocks/${params.row.code}`)}
        sx={{
          bgcolor: "background.paper",
          cursor: "pointer",
          "& .MuiDataGrid-row:hover": { bgcolor: "action.hover" },
        }}
        autoHeight
      />
    </Box>
  );
}
