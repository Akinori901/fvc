import { useNavigate } from "react-router-dom";
import {
  Box,
  Card,
  CardContent,
  Typography,
  Stack,
  Button,
  Chip,
} from "@mui/material";
import CalculateIcon from "@mui/icons-material/Calculate";
import ListAltIcon from "@mui/icons-material/ListAlt";
import { useStocks } from "@/hooks/useStocks";
import { useValuations } from "@/hooks/useValuations";
import { useSyncLogs } from "@/hooks/useSync";
import { formatCurrency, formatPercent, formatMultiple } from "@/utils/format";
import UpcomingSyncCard from "./dashboard/UpcomingSyncCard";
import RecommendationsCard from "./dashboard/RecommendationsCard";

export default function DashboardPage() {
  const navigate = useNavigate();
  const { data: stocks } = useStocks();
  const { data: valuations } = useValuations(5);
  const { data: syncLogs } = useSyncLogs(3);

  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        ダッシュボード
      </Typography>

      {/* サマリーカード */}
      <Stack direction="row" spacing={2} sx={{ mb: 3 }}>
        <Card sx={{ flex: 1 }}>
          <CardContent>
            <Typography variant="body2" color="text.secondary">
              登録銘柄数
            </Typography>
            <Typography variant="h4">{stocks?.length ?? 0}</Typography>
          </CardContent>
        </Card>
        <Card sx={{ flex: 1 }}>
          <CardContent>
            <Typography variant="body2" color="text.secondary">
              算出回数
            </Typography>
            <Typography variant="h4">{valuations?.length ?? 0}</Typography>
          </CardContent>
        </Card>
        <Card sx={{ flex: 1 }}>
          <CardContent>
            <Typography variant="body2" color="text.secondary">
              クイックアクション
            </Typography>
            <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
              <Button
                variant="contained"
                size="small"
                startIcon={<CalculateIcon />}
                onClick={() => navigate("/valuations/calculate")}
              >
                算出
              </Button>
              <Button
                variant="outlined"
                size="small"
                startIcon={<ListAltIcon />}
                onClick={() => navigate("/stocks")}
              >
                銘柄
              </Button>
            </Stack>
          </CardContent>
        </Card>
      </Stack>

      {/* 次回定期同期 */}
      <UpcomingSyncCard />

      {/* 日本株のおすすめ */}
      <RecommendationsCard />

      {/* 最近のバリュエーション */}
      <Typography variant="h6" gutterBottom>
        最近の算出結果
      </Typography>
      <Card sx={{ mb: 3 }}>
        <CardContent>
          {valuations && valuations.length > 0 ? (
            <Stack spacing={1}>
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
                      適正株価: {formatCurrency(v.fair_value)}
                    </Typography>
                    <Typography variant="body2">
                      成長率: {formatPercent(v.growth_rate)}
                    </Typography>
                    <Typography variant="body2">
                      適正PBR: {formatMultiple(v.fair_pbr)}
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
            <Typography color="text.secondary">
              まだ算出結果がありません。「適正株価算出」から始めましょう。
            </Typography>
          )}
        </CardContent>
      </Card>

      {/* 最近の同期ログ */}
      <Typography variant="h6" gutterBottom>
        最近の同期
      </Typography>
      <Card>
        <CardContent>
          {syncLogs && syncLogs.length > 0 ? (
            <Stack spacing={1}>
              {syncLogs.map((log) => (
                <Box
                  key={log.id}
                  sx={{
                    display: "flex",
                    justifyContent: "space-between",
                    p: 1,
                    borderBottom: "1px solid",
                    borderColor: "divider",
                  }}
                >
                  <Stack direction="row" spacing={2}>
                    <Chip label={log.sync_type} size="small" />
                    <Typography variant="body2">
                      {log.provider} / {log.market}
                    </Typography>
                  </Stack>
                  <Stack direction="row" spacing={1} alignItems="center">
                    <Typography variant="body2" color="text.secondary">
                      {log.success_count}/{log.total_count}件
                    </Typography>
                    <Chip
                      label={log.status}
                      size="small"
                      color={
                        log.status === "success"
                          ? "success"
                          : log.status === "failed"
                            ? "error"
                            : "default"
                      }
                    />
                  </Stack>
                </Box>
              ))}
            </Stack>
          ) : (
            <Typography color="text.secondary">
              まだ同期が実行されていません。
            </Typography>
          )}
        </CardContent>
      </Card>
    </Box>
  );
}
