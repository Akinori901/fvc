import { useState, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  Box,
  Typography,
  Card,
  CardContent,
  Stack,
  Chip,
  Tab,
  Tabs,
  Avatar,
  ToggleButton,
  ToggleButtonGroup,
  Pagination,
  IconButton,
  Tooltip as MuiTooltip,
} from "@mui/material";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import TrendingDownIcon from "@mui/icons-material/TrendingDown";
import ShareIcon from "@mui/icons-material/Share";
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import LoadingSpinner from "@/components/common/LoadingSpinner";
import ErrorAlert from "@/components/common/ErrorAlert";
import { useFamilyPortfolioDashboard } from "@/hooks/useFamilyPortfolio";
import { formatCurrency } from "@/utils/format";
import { ASSET_CLASS_COLORS } from "@/types/familyPortfolio";
import type { AccountType } from "@/types/portfolio";
import type { AssetClass, MemberDashboard } from "@/types/familyPortfolio";
import { ROUTES } from "@/router/routes";
import AccountsTab from "./portfolio/AccountsTab";
import PortfolioHistoryChart from "./portfolio/PortfolioHistoryChart";
import SimulationTab from "./portfolio/SimulationTab";
import GoalsTab from "./portfolio/GoalsTab";

const ACCOUNT_TYPE_COLORS: Record<AccountType, string> = {
  nisa_growth: "#1565c0",
  nisa_reserve: "#0277bd",
  specific: "#2e7d32",
  general: "#616161",
  us_securities: "#6a1b9a",
};

type ChartMode = "asset_class" | "account_type" | "top_holdings";

// 銘柄TOP10用のカラーパレット
const TOP_HOLDING_COLORS = [
  "#1565c0", "#6a1b9a", "#2e7d32", "#e65100", "#00838f",
  "#558b2f", "#4527a0", "#ad1457", "#c62828", "#827717",
  "#546e7a",
];

// -----------------------------------------------
// ダッシュボードタブ
// -----------------------------------------------

function DashboardTab() {
  const { data, isLoading } = useFamilyPortfolioDashboard("family");
  const [selectedMemberId, setSelectedMemberId] = useState<number | "all">("all");
  const [chartMode, setChartMode] = useState<ChartMode>("asset_class");

  if (isLoading) return <LoadingSpinner />;

  if (!data || ((data.by_member?.length ?? 0) === 0 && (data.accounts?.length ?? 0) === 0)) {
    return (
      <Card>
        <CardContent>
          <Typography color="text.secondary" align="center" sx={{ py: 2 }}>
            「口座管理」タブでメンバーと口座を登録し、残高を入力してください。
          </Typography>
        </CardContent>
      </Card>
    );
  }

  const totalValue = Number(data.total_value_jpy);
  const unrealized = data.unrealized_gain_jpy != null ? Number(data.unrealized_gain_jpy) : null;

  // 表示対象データを選択（合計 or メンバー別）
  const activeMember: MemberDashboard | undefined =
    selectedMemberId !== "all"
      ? (data.by_member ?? []).find((m) => m.member_id === selectedMemberId)
      : undefined;

  // 円グラフデータ
  const getPieData = () => {
    if (chartMode === "asset_class") {
      const source = activeMember
        ? activeMember.by_asset_class
        : data.by_asset_class;
      return (source ?? []).map((a) => ({
        name: a.label,
        value: Number(a.value_jpy),
        key: a.asset_class,
      }));
    }
    if (chartMode === "account_type") {
      return (data.by_account_type ?? []).map((a) => ({
        name: a.label,
        value: Number(a.value_jpy),
        key: a.account_type,
      }));
    }
    // top_holdings
    return (data.by_top_holdings ?? []).map((h) => ({
      name: h.name,
      value: Number(h.value_jpy),
      key: h.name,
    }));
  };

  const pieData = getPieData();

  const getColor = (entry: { key: string }, index: number) => {
    if (chartMode === "asset_class") {
      return ASSET_CLASS_COLORS[entry.key as AssetClass] ?? "#888";
    }
    if (chartMode === "account_type") {
      return ACCOUNT_TYPE_COLORS[entry.key as AccountType] ?? Object.values(ASSET_CLASS_COLORS)[index % 10];
    }
    return TOP_HOLDING_COLORS[index % TOP_HOLDING_COLORS.length];
  };

  const displayTotal =
    activeMember ? Number(activeMember.total_value_jpy) : totalValue;
  const displayGain =
    activeMember
      ? (activeMember.unrealized_gain_jpy != null ? Number(activeMember.unrealized_gain_jpy) : null)
      : unrealized;
  const displayCost =
    activeMember
      ? (activeMember.total_cost_jpy != null ? Number(activeMember.total_cost_jpy) : null)
      : (data.total_cost_jpy != null ? Number(data.total_cost_jpy) : null);
  const cumulativeReturnPct =
    displayGain !== null && displayCost !== null && displayCost > 0
      ? (displayGain / displayCost) * 100
      : null;
  // 年率: 累積CAGR ((1 + r) ^ (1/years)) - 1。1年未満は非表示
  const annualizedReturnPct = (() => {
    if (cumulativeReturnPct === null || displayCost === null || displayCost <= 0) return null;
    if (!data.earliest_snapshot_date) return null;
    const earliestMs = Date.parse(data.earliest_snapshot_date);
    if (Number.isNaN(earliestMs)) return null;
    const years = (Date.now() - earliestMs) / (365.25 * 24 * 60 * 60 * 1000);
    if (years < 1) return null;
    return (Math.pow(1 + cumulativeReturnPct / 100, 1 / years) - 1) * 100;
  })();

  // 表示口座フィルタ
  const visibleAccounts =
    selectedMemberId === "all"
      ? (data.accounts ?? [])
      : (data.accounts ?? []).filter((a) => a.member_id === selectedMemberId);

  // メンバーチップを表示するか（2人以上）
  const showMemberChips = (data.by_member?.length ?? 0) > 1;

  return (
    <Stack spacing={3}>
      {/* サマリーカード */}
      <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
        <Card sx={{ flex: 1 }}>
          <CardContent>
            <Stack direction="row" justifyContent="space-between" alignItems="center">
              <Typography variant="body2" color="text.secondary">
                {selectedMemberId === "all"
                  ? "家族総資産"
                  : (activeMember?.name ?? "") + " の総資産"}
              </Typography>
              <MuiTooltip title="X共有用を開く">
                <IconButton
                  size="small"
                  onClick={() => {
                    const params = selectedMemberId !== "all" ? `?member=${selectedMemberId}` : "";
                    window.open(`${ROUTES.PORTFOLIO_SHARE}${params}`, "_blank");
                  }}
                >
                  <ShareIcon fontSize="small" />
                </IconButton>
              </MuiTooltip>
            </Stack>
            <Typography variant="h4" fontWeight="bold">
              {formatCurrency(displayTotal)}
            </Typography>
            {data.latest_snapshot_date && (
              <Typography variant="caption" color="text.secondary">
                最終更新: {data.latest_snapshot_date}
              </Typography>
            )}
          </CardContent>
        </Card>
        {displayGain !== null && (
          <Card sx={{ flex: 1 }}>
            <CardContent>
              <Typography variant="body2" color="text.secondary">評価損益</Typography>
              <Stack direction="row" alignItems="center" spacing={0.5}>
                {displayGain >= 0 ? (
                  <TrendingUpIcon color="success" />
                ) : (
                  <TrendingDownIcon color="error" />
                )}
                <Typography
                  variant="h4"
                  fontWeight="bold"
                  color={displayGain >= 0 ? "success.main" : "error.main"}
                >
                  {displayGain >= 0 ? "+" : ""}{formatCurrency(displayGain)}
                </Typography>
              </Stack>
              {cumulativeReturnPct !== null && (
                <Typography
                  variant="body2"
                  color={displayGain >= 0 ? "success.main" : "error.main"}
                  sx={{ mt: 0.5 }}
                >
                  累積 {cumulativeReturnPct >= 0 ? "+" : ""}{cumulativeReturnPct.toFixed(2)}%
                  {annualizedReturnPct !== null && (
                    <>
                      {" / "}
                      年率 {annualizedReturnPct >= 0 ? "+" : ""}{annualizedReturnPct.toFixed(2)}%
                    </>
                  )}
                </Typography>
              )}
            </CardContent>
          </Card>
        )}
      </Stack>

      {/* メンバー切り替えチップ */}
      {showMemberChips && (
        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
          <Chip
            label="合計"
            variant={selectedMemberId === "all" ? "filled" : "outlined"}
            onClick={() => setSelectedMemberId("all")}
            color={selectedMemberId === "all" ? "primary" : "default"}
          />
          {(data.by_member ?? []).map((m) => (
            <Chip
              key={m.member_id}
              avatar={<Avatar sx={{ bgcolor: m.color_code }}>{m.name[0]}</Avatar>}
              label={`${m.name} ${formatCurrency(Number(m.total_value_jpy))}`}
              variant={selectedMemberId === m.member_id ? "filled" : "outlined"}
              onClick={() => setSelectedMemberId(m.member_id)}
              sx={selectedMemberId === m.member_id ? { bgcolor: m.color_code, color: "white" } : {}}
            />
          ))}
        </Stack>
      )}

      {/* 資産推移グラフ */}
      <PortfolioHistoryChart />

      {/* グラフ + 口座リスト */}
      <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
        {/* ドーナツグラフ */}
        {pieData.length > 0 && (
          <Card sx={{ flex: "0 0 auto", width: { xs: "100%", md: 400 } }}>
            <CardContent>
              <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
                <Typography variant="subtitle2">アロケーション</Typography>
                <ToggleButtonGroup
                  value={chartMode}
                  exclusive
                  onChange={(_, v) => v && setChartMode(v as ChartMode)}
                  size="small"
                >
                  <ToggleButton value="asset_class" sx={{ fontSize: 11, px: 1 }}>資産クラス</ToggleButton>
                  <ToggleButton value="account_type" sx={{ fontSize: 11, px: 1 }}>口座種別</ToggleButton>
                  <ToggleButton value="top_holdings" sx={{ fontSize: 11, px: 1 }}>銘柄TOP</ToggleButton>
                </ToggleButtonGroup>
              </Stack>
              {/* チャート中央に総額表示 */}
              <Box sx={{ position: "relative" }}>
                <ResponsiveContainer width="100%" height={220}>
                  <PieChart>
                    <Pie
                      data={pieData}
                      cx="50%"
                      cy="50%"
                      innerRadius={55}
                      outerRadius={95}
                      paddingAngle={2}
                      dataKey="value"
                    >
                      {pieData.map((entry, index) => (
                        <Cell
                          key={`cell-${index}`}
                          fill={getColor(entry, index)}
                        />
                      ))}
                    </Pie>
                    <Tooltip
                      formatter={(value) => formatCurrency(value as number)}
                    />
                  </PieChart>
                </ResponsiveContainer>
                {/* ドーナツ中央テキスト */}
                <Box
                  sx={{
                    position: "absolute",
                    top: "50%",
                    left: "50%",
                    transform: "translate(-50%, -50%)",
                    textAlign: "center",
                    pointerEvents: "none",
                  }}
                >
                  <Typography variant="caption" color="text.secondary" lineHeight={1}>
                    総額
                  </Typography>
                  <Typography variant="body2" fontWeight="bold" lineHeight={1.2} sx={{ fontSize: 13 }}>
                    {formatCurrency(displayTotal)}
                  </Typography>
                  {displayGain !== null && (
                    <Typography
                      variant="caption"
                      color={displayGain >= 0 ? "success.main" : "error.main"}
                      lineHeight={1}
                      sx={{ fontSize: 10 }}
                    >
                      {displayGain >= 0 ? "+" : ""}{formatCurrency(displayGain)}
                    </Typography>
                  )}
                </Box>
              </Box>
              {/* カスタム凡例（スクロール可能） */}
              <Box
                sx={{
                  maxHeight: 140,
                  overflowY: "auto",
                  mt: 1,
                  display: "flex",
                  flexWrap: "wrap",
                  gap: 0.5,
                  px: 0.5,
                }}
              >
                {pieData.map((entry, index) => {
                  const pct = displayTotal > 0 ? ((entry.value / displayTotal) * 100).toFixed(1) : "0";
                  return (
                    <Box
                      key={entry.key}
                      sx={{
                        display: "flex",
                        alignItems: "center",
                        gap: 0.5,
                        minWidth: 0,
                        mr: 1,
                      }}
                    >
                      <Box
                        sx={{
                          width: 10,
                          height: 10,
                          borderRadius: "50%",
                          bgcolor: getColor(entry, index),
                          flexShrink: 0,
                        }}
                      />
                      <Typography
                        variant="caption"
                        sx={{ fontSize: 10, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", maxWidth: 150 }}
                      >
                        {entry.name}
                      </Typography>
                      <Typography variant="caption" sx={{ fontSize: 10, color: "text.secondary", flexShrink: 0 }}>
                        {pct}%
                      </Typography>
                    </Box>
                  );
                })}
              </Box>
            </CardContent>
          </Card>
        )}

        {/* 口座別残高リスト */}
        <Box sx={{ flex: 1 }}>
          <Typography variant="subtitle2" gutterBottom>口座別残高</Typography>
          <Stack spacing={1}>
            {visibleAccounts.map((acc) => (
              <Card key={acc.id} variant="outlined">
                <CardContent sx={{ py: 1.5, "&:last-child": { pb: 1.5 } }}>
                  <Stack direction="row" justifyContent="space-between" alignItems="center">
                    <Box>
                      <Stack direction="row" spacing={1} alignItems="center">
                        <Typography variant="body2" fontWeight="bold">
                          {acc.nickname || acc.institution}
                        </Typography>
                        <Chip
                          label={acc.asset_class_display}
                          size="small"
                          sx={{
                            bgcolor: ASSET_CLASS_COLORS[acc.asset_class as AssetClass] ?? "#888",
                            color: "white",
                            fontSize: 10,
                          }}
                        />
                        {acc.trading_type === "margin" && (
                          <Chip label="信用" size="small" color="warning" variant="outlined" sx={{ fontSize: 10 }} />
                        )}
                        {selectedMemberId === "all" && (
                          <Typography variant="caption" color="text.secondary">
                            {acc.member_name}
                          </Typography>
                        )}
                      </Stack>
                    </Box>
                    <Box textAlign="right">
                      {acc.trading_type === "margin" && acc.latest_value_jpy != null && acc.latest_cost_jpy != null ? (
                        <>
                          <Typography
                            variant="body2"
                            fontWeight="bold"
                            color={Number(acc.latest_value_jpy) - Number(acc.latest_cost_jpy) >= 0 ? "success.main" : "error.main"}
                          >
                            {Number(acc.latest_value_jpy) - Number(acc.latest_cost_jpy) >= 0 ? "+" : ""}
                            {formatCurrency(Number(acc.latest_value_jpy) - Number(acc.latest_cost_jpy))}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            評価損益（時価: {formatCurrency(Number(acc.latest_value_jpy))}）
                          </Typography>
                        </>
                      ) : (
                        <Typography variant="body2" fontWeight="bold">
                          {acc.latest_value_jpy != null
                            ? formatCurrency(Number(acc.latest_value_jpy))
                            : "未入力"}
                        </Typography>
                      )}
                      {acc.latest_date && (
                        <Typography variant="caption" color="text.secondary">
                          {acc.latest_date}
                        </Typography>
                      )}
                    </Box>
                  </Stack>
                </CardContent>
              </Card>
            ))}
          </Stack>

        </Box>
      </Stack>
    </Stack>
  );
}

// -----------------------------------------------
// 保有株式タブ（スナップショットベース）
// -----------------------------------------------

const ITEMS_PER_PAGE = 30;

function StocksTab() {
  const navigate = useNavigate();
  const { data: dashboard, isLoading, error } = useFamilyPortfolioDashboard("family");
  const [filterMember, setFilterMember] = useState<string>("all");
  const [filterAccount, setFilterAccount] = useState<string>("all");
  const [page, setPage] = useState(1);

  const holdings = dashboard?.stock_holdings_v2 ?? [];

  // メンバー名の一覧を抽出（フィルター用）
  const memberNames = [...new Set(holdings.map((h) => h.member_name))].filter(Boolean);

  // 口座名の一覧を抽出（フィルター用 — メンバーフィルター適用後）
  const memberFiltered = filterMember === "all"
    ? holdings
    : holdings.filter((h) => h.member_name === filterMember);
  const accountNames = [...new Set(memberFiltered.map((h) => h.account_name))].filter(Boolean);

  const filtered = filterAccount === "all"
    ? memberFiltered
    : memberFiltered.filter((h) => h.account_name === filterAccount);

  // サマリー計算
  const totalValue = filtered.reduce((sum, h) => sum + Number(h.value_jpy), 0);
  const totalCost = filtered.reduce((sum, h) => sum + (h.cost_jpy != null ? Number(h.cost_jpy) : 0), 0);
  const hasCost = filtered.some((h) => h.cost_jpy != null);
  const totalGain = hasCost ? totalValue - totalCost : null;

  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorAlert />;

  return (
    <Box>
      {/* サマリー */}
      {filtered.length > 0 && (
        <Stack direction="row" spacing={3} sx={{ mb: 2 }}>
          {hasCost && (
            <Typography variant="body2" color="text.secondary">
              取得総額: <strong>{formatCurrency(totalCost)}</strong>
            </Typography>
          )}
          <Typography variant="body2" color="text.secondary">
            時価総額: <strong>{formatCurrency(totalValue)}</strong>
          </Typography>
          {totalGain !== null && (
            <Typography
              variant="body2"
              color={totalGain >= 0 ? "success.main" : "error.main"}
              fontWeight="bold"
            >
              {totalGain >= 0 ? "+" : ""}{formatCurrency(totalGain)}
            </Typography>
          )}
        </Stack>
      )}

      {/* メンバーフィルター */}
      {memberNames.length > 1 && (
        <Stack direction="row" spacing={1} sx={{ mb: 1 }} flexWrap="wrap">
          <Chip label="全員" variant={filterMember === "all" ? "filled" : "outlined"} onClick={() => { setFilterMember("all"); setFilterAccount("all"); setPage(1); }} />
          {memberNames.map((name) => (
            <Chip key={name} label={name} variant={filterMember === name ? "filled" : "outlined"} onClick={() => { setFilterMember(name); setFilterAccount("all"); setPage(1); }} />
          ))}
        </Stack>
      )}

      {/* 口座フィルター */}
      {accountNames.length > 1 && (
        <Stack direction="row" spacing={1} sx={{ mb: 2 }} flexWrap="wrap">
          <Chip label="全口座" variant={filterAccount === "all" ? "filled" : "outlined"} onClick={() => { setFilterAccount("all"); setPage(1); }} size="small" />
          {accountNames.map((name) => (
            <Chip key={name} label={name} variant={filterAccount === name ? "filled" : "outlined"} onClick={() => { setFilterAccount(name); setPage(1); }} size="small" />
          ))}
        </Stack>
      )}

      {/* 件数表示 */}
      <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
        {filtered.length}件{filtered.length !== holdings.length ? ` / 全${holdings.length}件` : ""}
      </Typography>

      {filtered.length > 0 ? (
        <>
        <Stack spacing={1}>
          {filtered.slice((page - 1) * ITEMS_PER_PAGE, page * ITEMS_PER_PAGE).map((h, idx) => {
            const gain = h.unrealized_gain_jpy != null ? Number(h.unrealized_gain_jpy) : null;
            const canNavigate = h.stock_code && h.stock_id != null;
            const unit = h.asset_type === "fund" ? "口" : "株";
            return (
              <Card key={`${h.ticker_code || h.asset_name}-${h.account_id}-${idx}`}>
                <CardContent sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", py: 1.5, "&:last-child": { pb: 1.5 } }}>
                  <Box
                    sx={{ flex: 1, ...(canNavigate && { cursor: "pointer" }) }}
                    onClick={() => canNavigate && navigate(`/stocks/${h.stock_code}`)}
                  >
                    <Stack direction="row" alignItems="center" spacing={1} flexWrap="wrap">
                      <Typography variant="body1" fontWeight="bold">
                        {h.ticker_code ? `${h.ticker_code} - ` : ""}{h.asset_name}
                      </Typography>
                      {h.member_name && (
                        <Chip label={h.member_name} size="small" color="primary" variant="outlined" />
                      )}
                      {h.account_name && (
                        <Chip label={h.account_name} size="small" variant="outlined" />
                      )}
                    </Stack>
                    <Stack direction="row" spacing={2} sx={{ mt: 0.5 }}>
                      {h.quantity != null && (
                        <Typography variant="body2" color="text.secondary">{Number(h.quantity).toLocaleString()}{unit}</Typography>
                      )}
                      {h.unit_price != null && (
                        <Typography variant="body2" color="text.secondary">取得: {formatCurrency(Number(h.unit_price))}</Typography>
                      )}
                      {h.latest_price != null && (
                        <Typography variant="body2" color="text.secondary">現在値: {formatCurrency(Number(h.latest_price))}</Typography>
                      )}
                      <Typography variant="body2" color="text.secondary">時価: {formatCurrency(Number(h.value_jpy))}</Typography>
                      {gain !== null && (
                        <Typography
                          variant="body2"
                          fontWeight="bold"
                          color={gain >= 0 ? "success.main" : "error.main"}
                        >
                          {gain >= 0 ? "+" : ""}{formatCurrency(gain)}
                        </Typography>
                      )}
                    </Stack>
                  </Box>
                </CardContent>
              </Card>
            );
          })}
        </Stack>
        {Math.ceil(filtered.length / ITEMS_PER_PAGE) > 1 && (
          <Box sx={{ display: "flex", justifyContent: "center", mt: 2 }}>
            <Pagination
              count={Math.ceil(filtered.length / ITEMS_PER_PAGE)}
              page={page}
              onChange={(_, v) => setPage(v)}
              color="primary"
            />
          </Box>
        )}
        </>
      ) : (
        <Card>
          <CardContent>
            <Typography color="text.secondary" align="center">
              スナップショットに株式データがありません。口座管理タブからCSVを取り込むか、スナップショットを登録してください。
            </Typography>
          </CardContent>
        </Card>
      )}
    </Box>
  );
}

// -----------------------------------------------
// メインコンポーネント
// -----------------------------------------------

const TAB_KEYS = ["dashboard", "accounts", "stocks", "simulation", "goals"] as const;

export default function PortfolioPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const tabParam = searchParams.get("tab");
  const initialTab = TAB_KEYS.indexOf(tabParam as typeof TAB_KEYS[number]);
  const [tab, setTab] = useState(initialTab >= 0 ? initialTab : 0);
  const { data: dashboard } = useFamilyPortfolioDashboard("family");

  // URL ?tab= パラメータとの同期
  useEffect(() => {
    const idx = TAB_KEYS.indexOf(tabParam as typeof TAB_KEYS[number]);
    if (idx >= 0 && idx !== tab) {
      setTab(idx);
    }
  }, [tabParam]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleTabChange = (_: React.SyntheticEvent, newValue: number) => {
    setTab(newValue);
    setSearchParams({ tab: TAB_KEYS[newValue] ?? "dashboard" });
  };

  return (
    <Box>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
        <Typography variant="h5">ポートフォリオ</Typography>
        {dashboard && (
          <Typography variant="body2" color="text.secondary">
            総資産: <strong>{formatCurrency(Number(dashboard.total_value_jpy))}</strong>
          </Typography>
        )}
      </Stack>

      <Tabs value={tab} onChange={handleTabChange} sx={{ mb: 2 }}>
        <Tab label="資産合計" />
        <Tab label="口座管理" />
        <Tab label="保有株式" />
        <Tab label="複利シミュレーション" />
        <Tab label="目標管理" />
      </Tabs>

      {tab === 0 && <DashboardTab />}
      {tab === 1 && (
        <AccountsTab accountRows={dashboard?.accounts ?? []} />
      )}
      {tab === 2 && <StocksTab />}
      {tab === 3 && <SimulationTab />}
      {tab === 4 && <GoalsTab />}
    </Box>
  );
}
