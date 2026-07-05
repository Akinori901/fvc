import { Box, Card, CardContent, Divider, Stack, Typography } from "@mui/material";
import ScheduleIcon from "@mui/icons-material/Schedule";

import { formatJst, formatJstShort, nextRunAt, type SimpleCron } from "@/utils/cronNextRun";

// terraform/eventbridge.tf と同期すること
const SCHEDULES: { name: string; cron: SimpleCron }[] = [
  { name: "国内株式情報（株価・夜間）", cron: { minute: 0, hour: 20, daysOfWeek: [1, 2, 3, 4, 5] } },
  { name: "国内株式情報（朝補完）", cron: { minute: 0, hour: 8, daysOfWeek: [1, 2, 3, 4, 5] } },
  { name: "国内株式（財務データ）", cron: { minute: 0, hour: 17, daysOfWeek: [1, 2, 3, 4, 5] } },
  { name: "国内 配当データ（ETF/REIT）", cron: { minute: 30, hour: 4, daysOfWeek: [0] } },
  { name: "国内 配当データ（普通株）", cron: { minute: 30, hour: 5, daysOfWeek: [0] } },
  { name: "為替・金利データ", cron: { minute: 0, hour: 7, daysOfWeek: [1, 2, 3, 4, 5] } },
  { name: "米国株式（株価）", cron: { minute: 0, hour: 7, daysOfWeek: [2, 3, 4, 5, 6] } },
  { name: "米国株式（財務データ）", cron: { minute: 0, hour: 18, daysOfWeek: [1, 2, 3, 4, 5] } },
  { name: "米国 配当データ", cron: { minute: 0, hour: 5, daysOfWeek: [0] } },
  { name: "おすすめ銘柄更新", cron: { minute: 0, hour: 9, daysOfWeek: [1, 2, 3, 4, 5] } },
];

export default function UpcomingSyncCard() {
  const now = new Date();
  const items = SCHEDULES.map((s) => ({ name: s.name, runAt: nextRunAt(s.cron, now) }));
  // 直近順
  items.sort((a, b) => a.runAt.getTime() - b.runAt.getTime());
  const next = items[0];
  const rest = items.slice(1);

  if (!next) return null;

  return (
    <Card sx={{ mb: 3 }}>
      <CardContent>
        <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 1 }}>
          <ScheduleIcon fontSize="small" color="action" />
          <Typography variant="subtitle2" color="text.secondary">
            次回の定期同期
          </Typography>
        </Stack>

        <Typography variant="body1" sx={{ mb: 1.5 }}>
          次回「<strong>{next.name}</strong>」の更新は{" "}
          <strong>{formatJst(next.runAt)}</strong> です
        </Typography>

        <Divider sx={{ my: 1 }} />

        <Stack spacing={0.5} sx={{ mt: 1 }}>
          {rest.map((item) => (
            <Box
              key={item.name}
              sx={{
                display: "flex",
                justifyContent: "space-between",
                fontSize: 13,
                color: "text.secondary",
              }}
            >
              <span>・{item.name}</span>
              <span>{formatJstShort(item.runAt)}</span>
            </Box>
          ))}
        </Stack>
      </CardContent>
    </Card>
  );
}
