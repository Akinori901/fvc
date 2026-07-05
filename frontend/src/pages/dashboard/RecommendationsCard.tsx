import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Box,
  Card,
  CardContent,
  Chip,
  Skeleton,
  Stack,
  Tab,
  Tabs,
  Typography,
} from "@mui/material";
import RecommendIcon from "@mui/icons-material/Recommend";

import { useRecommendations } from "@/hooks/useRecommendations";
import { formatCurrency } from "@/utils/format";
import type { RecommendedStock } from "@/types/recommendations";

type CategoryKey = "long_term" | "day_trade" | "range_bound";

const CATEGORY_LABELS: Record<CategoryKey, string> = {
  long_term: "長期保有",
  day_trade: "デイトレ",
  range_bound: "1〜2年レンジ",
};

const METRIC_LABELS: Record<string, string> = {
  dividend_yield: "配当利回り",
  consecutive_dividend_years: "連続配当",
  discount_rate: "割安度",
  eps_cagr_3y: "EPS成長",
  roe: "ROE",
  volatility_20d: "ボラ20日",
  avg_turnover_20d_oku: "売買代金(億)",
  liquidity: "流動性",
  range_high: "高値",
  range_low: "安値",
  range_width: "値幅",
  drift_pct: "1年変化",
};

const METRIC_SUFFIX: Record<string, string> = {
  dividend_yield: "%",
  consecutive_dividend_years: "年",
  discount_rate: "%",
  eps_cagr_3y: "%",
  roe: "%",
  volatility_20d: "%",
  avg_turnover_20d_oku: "億",
  range_high: "円",
  range_low: "円",
  range_width: "円",
  drift_pct: "%",
};

function formatMetric(key: string, value: string): string {
  const suffix = METRIC_SUFFIX[key] ?? "";
  return `${value}${suffix}`;
}

function StockRow({ stock }: { stock: RecommendedStock }) {
  const navigate = useNavigate();
  return (
    <Box
      onClick={() => navigate(`/stocks/${stock.code}`)}
      sx={{
        p: 1.5,
        cursor: "pointer",
        borderRadius: 1,
        "&:hover": { bgcolor: "action.hover" },
        borderBottom: "1px solid",
        borderColor: "divider",
      }}
    >
      <Stack direction="row" justifyContent="space-between" alignItems="flex-start" spacing={1}>
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Typography variant="body2" fontWeight="bold" noWrap>
            {stock.code} {stock.name}
          </Typography>
          <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap sx={{ mt: 0.5 }}>
            {Object.entries(stock.metrics).map(([k, v]) => (
              <Chip
                key={k}
                size="small"
                label={`${METRIC_LABELS[k] ?? k}: ${formatMetric(k, v)}`}
                sx={{ fontSize: 11, height: 20 }}
              />
            ))}
          </Stack>
        </Box>
        <Typography variant="body2" sx={{ whiteSpace: "nowrap" }}>
          {formatCurrency(Number(stock.latest_price ?? 0))}
        </Typography>
      </Stack>
    </Box>
  );
}

export default function RecommendationsCard() {
  const [tab, setTab] = useState<CategoryKey>("long_term");
  const { data, isLoading, error } = useRecommendations();

  const items: RecommendedStock[] = data ? data[tab] : [];

  return (
    <Card sx={{ mb: 3 }}>
      <CardContent>
        <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 1 }}>
          <RecommendIcon fontSize="small" color="primary" />
          <Typography variant="subtitle1" fontWeight="bold">
            日本株のおすすめ
          </Typography>
        </Stack>

        <Tabs
          value={tab}
          onChange={(_, v) => setTab(v as CategoryKey)}
          variant="fullWidth"
          sx={{ borderBottom: 1, borderColor: "divider", mb: 1 }}
        >
          <Tab label={CATEGORY_LABELS.long_term} value="long_term" />
          <Tab label={CATEGORY_LABELS.day_trade} value="day_trade" />
          <Tab label={CATEGORY_LABELS.range_bound} value="range_bound" />
        </Tabs>

        {isLoading && (
          <Stack spacing={1} sx={{ mt: 1 }}>
            {[1, 2, 3, 4, 5].map((i) => (
              <Skeleton key={i} height={56} variant="rounded" />
            ))}
          </Stack>
        )}

        {error && (
          <Typography color="error" variant="body2">
            おすすめの取得に失敗しました
          </Typography>
        )}

        {!isLoading && !error && items.length === 0 && (
          <Typography color="text.secondary" variant="body2" sx={{ p: 2 }}>
            条件を満たす銘柄がありません
          </Typography>
        )}

        {!isLoading && items.length > 0 && (
          <Box>
            {items.map((s) => (
              <StockRow key={s.code} stock={s} />
            ))}
          </Box>
        )}

        {data && (
          <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 1.5 }}>
            生成: {new Date(data.generated_at).toLocaleString("ja-JP")}
          </Typography>
        )}
      </CardContent>
    </Card>
  );
}
