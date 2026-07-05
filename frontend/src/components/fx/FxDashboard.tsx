import { useState } from "react";
import {
  Box,
  Card,
  CardContent,
  Chip,
  Grid,
  IconButton,
  Popover,
  Typography,
} from "@mui/material";
import HelpOutlineIcon from "@mui/icons-material/HelpOutline";
import type { FxAnalysis } from "@/types/fx";

const ZONE_CONFIG: Record<
  string,
  {
    label: string;
    color: "success" | "info" | "default" | "warning" | "error";
    title: string;
    description: string;
    action: string;
  }
> = {
  strong_buy: {
    label: "強い買い",
    color: "success",
    title: "強い買いシグナル",
    description:
      "金利差モデルの適正値から -2σ 以上乖離しています（大幅な円高水準）。",
    action:
      "積極的なドル買いを検討できる局面です。分割購入で平均取得コストを下げる戦略が有効です。",
  },
  buy: {
    label: "買い",
    color: "info",
    title: "買いシグナル",
    description:
      "適正値から -1σ〜-2σ 乖離しています（やや円高水準）。",
    action:
      "ドル買いの好機です。一括ではなく段階的な購入を推奨します。",
  },
  neutral: {
    label: "中立",
    color: "default",
    title: "中立",
    description: "適正値 ±1σ の範囲内です。",
    action:
      "急いで売買する必要はありません。次のシグナルまで様子見が妥当です。",
  },
  sell: {
    label: "売り",
    color: "warning",
    title: "売りシグナル",
    description:
      "適正値から +1σ〜+2σ 乖離しています（やや円安水準）。",
    action:
      "保有ドルの一部利確を検討してください。新規ドル買いは控えめに。",
  },
  strong_sell: {
    label: "強い売り",
    color: "error",
    title: "強い売りシグナル",
    description:
      "適正値から +2σ 以上乖離しています（大幅な円安水準）。",
    action:
      "ドル売り（円転）を積極的に検討できる局面です。新規ドル買いは非推奨。円高への回帰を待つのが賢明です。",
  },
};

function MetricCard({
  title,
  value,
  sub,
}: {
  title: string;
  value: string;
  sub?: string;
}) {
  return (
    <Card variant="outlined">
      <CardContent sx={{ py: 1.5, "&:last-child": { pb: 1.5 } }}>
        <Typography variant="caption" color="text.secondary">
          {title}
        </Typography>
        <Typography variant="h6" fontWeight="bold">
          {value}
        </Typography>
        {sub && (
          <Typography variant="body2" color="text.secondary">
            {sub}
          </Typography>
        )}
      </CardContent>
    </Card>
  );
}

interface Props {
  data: FxAnalysis;
}

export default function FxDashboard({ data }: Props) {
  const zone = data.regression?.zone ?? "neutral";
  const zoneInfo = ZONE_CONFIG[zone] ?? ZONE_CONFIG["neutral"];

  const [anchorEl, setAnchorEl] = useState<HTMLButtonElement | null>(null);

  return (
    <Box>
      {/* Zone Badge */}
      <Box sx={{ mb: 2, display: "flex", alignItems: "center", gap: 2 }}>
        <Typography variant="h5" fontWeight="bold">
          USD/JPY 分析
        </Typography>
        <Chip
          label={zoneInfo?.label ?? "中立"}
          color={zoneInfo?.color ?? "default"}
          variant="filled"
          size="medium"
        />
        <IconButton
          size="small"
          onClick={(e) => setAnchorEl(e.currentTarget)}
          sx={{ color: "text.secondary" }}
        >
          <HelpOutlineIcon fontSize="small" />
        </IconButton>
        <Popover
          open={Boolean(anchorEl)}
          anchorEl={anchorEl}
          onClose={() => setAnchorEl(null)}
          anchorOrigin={{ vertical: "bottom", horizontal: "left" }}
          transformOrigin={{ vertical: "top", horizontal: "left" }}
        >
          <Box sx={{ p: 2, maxWidth: 340 }}>
            <Typography variant="subtitle2" fontWeight="bold" gutterBottom>
              {zoneInfo?.title}
            </Typography>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              {zoneInfo?.description}
            </Typography>
            <Typography variant="body2" sx={{ mt: 1 }}>
              {zoneInfo?.action}
            </Typography>
          </Box>
        </Popover>
      </Box>

      <Grid container spacing={2}>
        {/* 現在レート */}
        <Grid size={{ xs: 6, sm: 4, md: 3 }}>
          <MetricCard
            title="現在レート"
            value={`¥${Number(data.current_rate).toFixed(2)}`}
            sub={data.current_rate_date}
          />
        </Grid>

        {/* 適正値 */}
        {data.regression && (
          <Grid size={{ xs: 6, sm: 4, md: 3 }}>
            <MetricCard
              title="金利差モデル適正値"
              value={`¥${Number(data.regression.fair_value).toFixed(2)}`}
              sub={`乖離: ${Number(data.regression.current_deviation).toFixed(2)}円`}
            />
          </Grid>
        )}

        {/* 金利差 */}
        {data.interest_rate_diff && (
          <Grid size={{ xs: 6, sm: 4, md: 3 }}>
            <MetricCard
              title="日米金利差"
              value={`${Number(data.interest_rate_diff).toFixed(2)}%`}
              sub={`US: ${data.us_10y ? Number(data.us_10y).toFixed(2) : "-"}% / JP: ${data.jp_10y ? Number(data.jp_10y).toFixed(2) : "-"}%`}
            />
          </Grid>
        )}

        {/* PPP */}
        {data.ppp_rate && (
          <Grid size={{ xs: 6, sm: 4, md: 3 }}>
            <MetricCard
              title="PPP均衡レート"
              value={`¥${Number(data.ppp_rate).toFixed(2)}`}
              sub={
                data.ppp_deviation
                  ? `乖離率: ${Number(data.ppp_deviation) >= 0 ? "+" : ""}${Number(data.ppp_deviation).toFixed(1)}%`
                  : undefined
              }
            />
          </Grid>
        )}

        {/* 買いゾーン */}
        {data.buy_zone_lower && data.sell_zone_upper && (
          <Grid size={{ xs: 6, sm: 4, md: 3 }}>
            <MetricCard
              title="買い/売りゾーン (±1σ)"
              value={`¥${Number(data.buy_zone_lower).toFixed(1)} ~ ¥${Number(data.sell_zone_upper).toFixed(1)}`}
            />
          </Grid>
        )}

        {/* 強い買い/売りゾーン */}
        {data.strong_buy_lower && data.strong_sell_upper && (
          <Grid size={{ xs: 6, sm: 4, md: 3 }}>
            <MetricCard
              title="強い買い/売り (±2σ)"
              value={`¥${Number(data.strong_buy_lower).toFixed(1)} ~ ¥${Number(data.strong_sell_upper).toFixed(1)}`}
            />
          </Grid>
        )}

        {/* R² */}
        {data.regression && (
          <Grid size={{ xs: 6, sm: 4, md: 3 }}>
            <MetricCard
              title="モデル決定係数 (R²)"
              value={Number(data.regression.r_squared).toFixed(4)}
            />
          </Grid>
        )}
      </Grid>
    </Box>
  );
}
