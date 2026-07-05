import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Box,
  Typography,
  Card,
  CardContent,
  IconButton,
  Stack,
  Button,
  TextField,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Chip,
} from "@mui/material";
import DeleteIcon from "@mui/icons-material/Delete";
import AddIcon from "@mui/icons-material/Add";
import StockSearchBar from "@/components/stock/StockSearchBar";
import LoadingSpinner from "@/components/common/LoadingSpinner";
import ErrorAlert from "@/components/common/ErrorAlert";
import StockAttributeBadges from "@/components/common/StockAttributeBadges";
import { useWatchlist, useAddToWatchlist, useRemoveFromWatchlist } from "@/hooks/useWatchlist";
import { useStocks } from "@/hooks/useStocks";
import { computeOverallRating } from "@/utils/overallRating";
import { getZoneInfoByZone } from "@/utils/evaluation";
import { formatCurrency } from "@/utils/format";
import type { Stock } from "@/types/stock";
import type { WatchlistItem } from "@/types/watchlist";
import type { EvaluationZone } from "@/utils/evaluation";

function WatchlistItemCard({
  item,
  onDelete,
  isDeleting,
}: {
  item: WatchlistItem;
  onDelete: () => void;
  isDeleting: boolean;
}) {
  const navigate = useNavigate();

  const price = item.latest_price ? Number(item.latest_price) : null;
  const fairValue = item.fair_value ? Number(item.fair_value) : null;
  const priceGap = fairValue != null && price != null ? fairValue - price : null;

  const zoneInfo = item.evaluation_zone
    ? getZoneInfoByZone(item.evaluation_zone as EvaluationZone)
    : null;

  const overallRating = computeOverallRating({
    evaluationZone: (item.evaluation_zone as EvaluationZone) ?? null,
    growthRateLabel: item.growth_rate_label ?? null,
    roeTrend: (item.roe_trend as "improving" | "declining" | "stable") ?? null,
    epsCagr3y: item.eps_cagr_3y ? Number(item.eps_cagr_3y) : null,
    epsGrowthYoy: item.eps_growth_yoy ? Number(item.eps_growth_yoy) : null,
    slRatio: item.sl_ratio ? Number(item.sl_ratio) : null,
  });

  return (
    <Card>
      <CardContent
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          py: 1.5,
          "&:last-child": { pb: 1.5 },
        }}
      >
        <Box
          sx={{ cursor: "pointer", flex: 1, minWidth: 0 }}
          onClick={() => navigate(`/stocks/${item.stock_code}`)}
        >
          <Stack direction="row" alignItems="center" spacing={1} flexWrap="wrap" sx={{ mb: 0.5, rowGap: 0.5 }}>
            <Typography variant="body1" fontWeight="bold" noWrap>
              {item.stock_code} - {item.stock_name}
            </Typography>
            {zoneInfo && (
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
            )}
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
            <StockAttributeBadges input={item} />
          </Stack>

          <Stack direction="row" spacing={2} alignItems="center">
            {price != null && (
              <Typography variant="body2" color="text.secondary">
                株価: {formatCurrency(price)}
              </Typography>
            )}
            {fairValue != null && (
              <Typography variant="body2" color="text.secondary">
                適正: {formatCurrency(fairValue)}
              </Typography>
            )}
            {priceGap != null && (
              <Typography
                variant="body2"
                fontWeight="bold"
                color={priceGap >= 0 ? "success.main" : "error.main"}
              >
                ギャップ: {priceGap >= 0 ? "+" : ""}{formatCurrency(priceGap)}
              </Typography>
            )}
          </Stack>

          {item.memo && (
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
              {item.memo}
            </Typography>
          )}
        </Box>
        <IconButton
          onClick={onDelete}
          disabled={isDeleting}
          size="small"
          color="error"
        >
          <DeleteIcon />
        </IconButton>
      </CardContent>
    </Card>
  );
}

export default function WatchlistPage() {
  const { data: watchlist, isLoading, error } = useWatchlist();
  const { data: stocks } = useStocks();
  const addMutation = useAddToWatchlist();
  const removeMutation = useRemoveFromWatchlist();

  const [dialogOpen, setDialogOpen] = useState(false);
  const [selectedStock, setSelectedStock] = useState<Stock | null>(null);
  const [memo, setMemo] = useState("");

  const handleAdd = () => {
    if (!selectedStock) return;
    addMutation.mutate(
      { stock_code: selectedStock.code, memo },
      {
        onSuccess: () => {
          setDialogOpen(false);
          setSelectedStock(null);
          setMemo("");
        },
      }
    );
  };

  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorAlert />;

  return (
    <Box>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
        <Typography variant="h5">ウォッチリスト</Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => setDialogOpen(true)}
        >
          追加
        </Button>
      </Stack>

      {watchlist && watchlist.length > 0 ? (
        <Stack spacing={1}>
          {watchlist.map((item) => (
            <WatchlistItemCard
              key={item.id}
              item={item}
              onDelete={() => removeMutation.mutate(item.stock_code)}
              isDeleting={removeMutation.isPending}
            />
          ))}
        </Stack>
      ) : (
        <Card>
          <CardContent>
            <Typography color="text.secondary" align="center">
              ウォッチリストに銘柄がありません。「追加」ボタンで銘柄を追加しましょう。
            </Typography>
          </CardContent>
        </Card>
      )}

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>ウォッチリストに追加</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <StockSearchBar
              stocks={stocks ?? []}
              onSelect={setSelectedStock}
            />
            <TextField
              label="メモ（任意）"
              value={memo}
              onChange={(e) => setMemo(e.target.value)}
              multiline
              rows={2}
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>キャンセル</Button>
          <Button
            variant="contained"
            onClick={handleAdd}
            disabled={!selectedStock || addMutation.isPending}
          >
            追加
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
