import { useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Divider,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from "@mui/material";
import ShoppingCartIcon from "@mui/icons-material/ShoppingCart";
import SellIcon from "@mui/icons-material/Sell";
import {
  useExecuteTrade,
  usePaperPosition,
  usePaperTradeHistory,
} from "@/hooks/usePaperTrading";

interface Props {
  stockCode: string;
  latestPrice: string | null;
}

export default function PaperTradePanel({ stockCode, latestPrice }: Props) {
  const [tradeType, setTradeType] = useState<"buy" | "sell">("buy");
  const [quantity, setQuantity] = useState(100);
  const [memo, setMemo] = useState("");

  const { data: position, isLoading: posLoading } =
    usePaperPosition(stockCode);
  const { data: trades } = usePaperTradeHistory(stockCode);
  const executeMutation = useExecuteTrade();

  const price = latestPrice ? parseFloat(latestPrice) : null;
  const totalAmount = price ? price * quantity : null;

  const posQty = position?.quantity ?? 0;
  const avgCost = position ? parseFloat(position.avg_cost_price) : 0;

  // 含み損益
  const unrealizedProfit =
    position && price && posQty > 0
      ? (price - avgCost) * posQty
      : null;
  const unrealizedPct =
    avgCost > 0 && unrealizedProfit !== null
      ? (unrealizedProfit / (avgCost * posQty)) * 100
      : null;

  // 売り時の確定損益プレビュー
  const sellProfit =
    tradeType === "sell" && price && avgCost > 0
      ? (price - avgCost) * quantity
      : null;

  const canSell = posQty >= quantity && posQty > 0;
  const canTrade =
    price !== null &&
    quantity >= 100 &&
    quantity % 100 === 0 &&
    (tradeType === "buy" || canSell);

  const errorMsg =
    executeMutation.isError && executeMutation.error instanceof Error
      ? ((
          executeMutation.error as {
            response?: { data?: { detail?: string } };
          }
        )?.response?.data?.detail ?? executeMutation.error.message)
      : null;

  if (price === null) {
    return (
      <Card variant="outlined">
        <CardContent>
          <Typography color="text.secondary">
            株価データがないため売買できません。
          </Typography>
        </CardContent>
      </Card>
    );
  }

  return (
    <Stack spacing={2}>
      {/* ポジション表示 */}
      <Card variant="outlined">
        <CardContent>
          <Typography variant="subtitle2" color="text.secondary" gutterBottom>
            現在のポジション
          </Typography>
          {posLoading ? (
            <CircularProgress size={20} />
          ) : posQty > 0 ? (
            <Stack direction="row" spacing={3} alignItems="baseline">
              <Typography>
                保有: <strong>{posQty.toLocaleString()}株</strong>
              </Typography>
              <Typography>
                平均取得単価: <strong>¥{avgCost.toLocaleString()}</strong>
              </Typography>
              {unrealizedProfit !== null && (
                <Typography
                  color={unrealizedProfit >= 0 ? "success.main" : "error.main"}
                >
                  含み損益:{" "}
                  <strong>
                    {unrealizedProfit >= 0 ? "+" : ""}¥
                    {Math.round(unrealizedProfit).toLocaleString()}
                    {unrealizedPct !== null &&
                      ` (${unrealizedPct >= 0 ? "+" : ""}${unrealizedPct.toFixed(2)}%)`}
                  </strong>
                </Typography>
              )}
            </Stack>
          ) : (
            <Typography color="text.secondary">
              この銘柄のポジションはありません
            </Typography>
          )}
        </CardContent>
      </Card>

      {/* 売買フォーム */}
      <Card variant="outlined">
        <CardContent>
          <Stack spacing={2}>
            <ToggleButtonGroup
              value={tradeType}
              exclusive
              onChange={(_, v) => v && setTradeType(v)}
              size="small"
            >
              <ToggleButton value="buy" color="success">
                <ShoppingCartIcon sx={{ mr: 0.5 }} fontSize="small" />
                買い
              </ToggleButton>
              <ToggleButton
                value="sell"
                color="error"
                disabled={posQty === 0}
              >
                <SellIcon sx={{ mr: 0.5 }} fontSize="small" />
                売り
              </ToggleButton>
            </ToggleButtonGroup>

            <Stack direction="row" spacing={2} alignItems="center">
              <TextField
                label="数量（株）"
                type="number"
                value={quantity}
                onChange={(e) =>
                  setQuantity(Math.max(100, parseInt(e.target.value) || 100))
                }
                inputProps={{
                  step: 100,
                  min: 100,
                  max: tradeType === "sell" ? posQty : undefined,
                }}
                size="small"
                sx={{ width: 150 }}
              />
              <TextField
                label="メモ"
                value={memo}
                onChange={(e) => setMemo(e.target.value)}
                size="small"
                sx={{ flex: 1 }}
                inputProps={{ maxLength: 200 }}
              />
            </Stack>

            {/* プレビュー */}
            <Box sx={{ bgcolor: "grey.50", p: 1.5, borderRadius: 1 }}>
              <Typography variant="body2">
                ¥{price.toLocaleString()} × {quantity.toLocaleString()}株 ={" "}
                <strong>
                  ¥{totalAmount ? totalAmount.toLocaleString() : "-"}
                </strong>
              </Typography>
              {tradeType === "sell" && sellProfit !== null && (
                <Typography
                  variant="body2"
                  color={sellProfit >= 0 ? "success.main" : "error.main"}
                  sx={{ mt: 0.5 }}
                >
                  確定損益:{" "}
                  <strong>
                    {sellProfit >= 0 ? "+" : ""}¥
                    {Math.round(sellProfit).toLocaleString()}
                  </strong>
                </Typography>
              )}
            </Box>

            {quantity % 100 !== 0 && (
              <Alert severity="warning" variant="outlined">
                数量は100株単位で入力してください。
              </Alert>
            )}
            {tradeType === "sell" && quantity > posQty && posQty > 0 && (
              <Alert severity="warning" variant="outlined">
                保有数（{posQty}株）を超えています。
              </Alert>
            )}

            <Button
              variant="contained"
              color={tradeType === "buy" ? "success" : "error"}
              onClick={() => {
                executeMutation.mutate({
                  stock_code: stockCode,
                  trade_type: tradeType,
                  quantity,
                  memo: memo || undefined,
                });
              }}
              disabled={!canTrade || executeMutation.isPending}
              startIcon={
                executeMutation.isPending ? (
                  <CircularProgress size={16} color="inherit" />
                ) : tradeType === "buy" ? (
                  <ShoppingCartIcon />
                ) : (
                  <SellIcon />
                )
              }
            >
              {executeMutation.isPending
                ? "処理中..."
                : tradeType === "buy"
                  ? "購入する"
                  : "売却する"}
            </Button>

            {errorMsg && <Alert severity="error">{errorMsg}</Alert>}

            {executeMutation.isSuccess && (
              <Alert severity="success">
                {executeMutation.data.trade_type === "buy" ? "購入" : "売却"}
                が完了しました。
              </Alert>
            )}
          </Stack>
        </CardContent>
      </Card>

      {/* 売買履歴 */}
      {trades && trades.length > 0 && (
        <Card variant="outlined">
          <CardContent>
            <Typography variant="subtitle2" color="text.secondary" gutterBottom>
              売買履歴
            </Typography>
            <Divider sx={{ mb: 1 }} />
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>日時</TableCell>
                  <TableCell>種別</TableCell>
                  <TableCell align="right">数量</TableCell>
                  <TableCell align="right">単価</TableCell>
                  <TableCell align="right">金額</TableCell>
                  <TableCell align="right">損益</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {trades.map((t) => (
                  <TableRow key={t.id}>
                    <TableCell sx={{ fontSize: "0.8rem" }}>
                      {new Date(t.traded_at).toLocaleDateString("ja-JP")}
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={t.trade_type === "buy" ? "買" : "売"}
                        size="small"
                        color={t.trade_type === "buy" ? "success" : "error"}
                        variant="outlined"
                      />
                    </TableCell>
                    <TableCell align="right">
                      {t.quantity.toLocaleString()}
                    </TableCell>
                    <TableCell align="right">
                      ¥{parseFloat(t.price).toLocaleString()}
                    </TableCell>
                    <TableCell align="right">
                      ¥{parseFloat(t.total_amount).toLocaleString()}
                    </TableCell>
                    <TableCell align="right">
                      {t.realized_profit !== null ? (
                        <Typography
                          variant="body2"
                          color={
                            parseFloat(t.realized_profit) >= 0
                              ? "success.main"
                              : "error.main"
                          }
                        >
                          {parseFloat(t.realized_profit) >= 0 ? "+" : ""}¥
                          {Math.round(
                            parseFloat(t.realized_profit)
                          ).toLocaleString()}
                        </Typography>
                      ) : (
                        "-"
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </Stack>
  );
}
