import { Card, CardContent, Stack, Typography } from "@mui/material";

import { formatCurrency } from "@/utils/format";
import type { GoalProgress, ProjectionStatus } from "@/types/goals";

interface Props {
  progress: GoalProgress;
}

const STATUS_LABEL: Record<ProjectionStatus, string> = {
  ahead: "前倒し",
  on_track: "順調",
  behind: "遅れ気味",
  unknown: "判定不可",
};

const STATUS_COLOR: Record<ProjectionStatus, string> = {
  ahead: "primary.main",
  on_track: "success.main",
  behind: "warning.main",
  unknown: "text.secondary",
};

export default function GoalProgressCard({ progress }: Props) {
  const current = Number(progress.current_value_jpy);
  const target = Number(progress.goal.target_value_jpy);
  const achievement = Number(progress.achievement_rate_pct);
  const ideal = Number(progress.ideal_value_now_jpy);
  const gap = Number(progress.gap_jpy);
  const projected =
    progress.projected_value_at_target_jpy !== null
      ? Number(progress.projected_value_at_target_jpy)
      : null;
  const avgIncrease =
    progress.avg_monthly_increase_jpy !== null
      ? Number(progress.avg_monthly_increase_jpy)
      : null;

  const isAchieved = achievement >= 100;

  return (
    <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
      {/* 達成率 */}
      <Card sx={{ flex: 1 }}>
        <CardContent>
          <Typography variant="body2" color="text.secondary">
            達成率
          </Typography>
          <Stack direction="row" alignItems="baseline" spacing={1}>
            <Typography
              variant="h4"
              fontWeight="bold"
              color={isAchieved ? "primary.main" : "text.primary"}
            >
              {achievement.toFixed(1)}%
            </Typography>
            {isAchieved && (
              <Typography variant="caption" color="primary.main" fontWeight="bold">
                達成済み
              </Typography>
            )}
          </Stack>
          <Typography variant="caption" color="text.secondary">
            目標 {formatCurrency(target)}
          </Typography>
        </CardContent>
      </Card>

      {/* 現在額 */}
      <Card sx={{ flex: 1 }}>
        <CardContent>
          <Typography variant="body2" color="text.secondary">
            現在額
          </Typography>
          <Typography variant="h4" fontWeight="bold">
            {formatCurrency(current)}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            理想 {formatCurrency(ideal)}
          </Typography>
        </CardContent>
      </Card>

      {/* GAP */}
      <Card sx={{ flex: 1 }}>
        <CardContent>
          <Typography variant="body2" color="text.secondary">
            進捗GAP
          </Typography>
          <Typography
            variant="h4"
            fontWeight="bold"
            color={gap >= 0 ? "success.main" : "error.main"}
          >
            {gap >= 0 ? "+" : ""}
            {formatCurrency(gap)}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {gap >= 0 ? "進捗線より前進" : "進捗線より遅れ"}
          </Typography>
        </CardContent>
      </Card>

      {/* 到達予測 */}
      <Card sx={{ flex: 1 }}>
        <CardContent>
          <Typography variant="body2" color="text.secondary">
            到達予測
          </Typography>
          <Typography
            variant="h4"
            fontWeight="bold"
            color={STATUS_COLOR[progress.projection_status]}
          >
            {projected !== null ? formatCurrency(projected) : "—"}
          </Typography>
          <Typography
            variant="caption"
            color={STATUS_COLOR[progress.projection_status]}
          >
            {STATUS_LABEL[progress.projection_status]}
            {avgIncrease !== null && (
              <>（月+{formatCurrency(avgIncrease)}）</>
            )}
          </Typography>
        </CardContent>
      </Card>
    </Stack>
  );
}
