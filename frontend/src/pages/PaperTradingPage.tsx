import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Stack,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tabs,
  Typography,
} from "@mui/material";
import DeleteForeverIcon from "@mui/icons-material/DeleteForever";
import {
  usePaperPositions,
  usePaperTradeHistory,
  useResetPaperTrading,
} from "@/hooks/usePaperTrading";

export default function PaperTradingPage() {
  const navigate = useNavigate();
  const [tab, setTab] = useState(0);
  const [resetOpen, setResetOpen] = useState(false);

  const { data, isLoading, error } = usePaperPositions();
  const { data: trades, isLoading: tradesLoading } = usePaperTradeHistory();
  const resetMutation = useResetPaperTrading();

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" py={4}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return <Alert severity="error">データの読み込みに失敗しました。</Alert>;
  }

  const summary = data?.summary;
  const positions = data?.positions ?? [];

  return (
    <Box>
      {/* ヘッダー */}
      <Stack
        direction="row"
        justifyContent="space-between"
        alignItems="center"
        mb={2}
      >
        <Typography variant="h5" fontWeight="bold">
          仮想売買
        </Typography>
        <Button
          variant="outlined"
          color="error"
          size="small"
          startIcon={<DeleteForeverIcon />}
          onClick={() => setResetOpen(true)}
        >
          リセット
        </Button>
      </Stack>

      {/* サマリーカード */}
      {summary && (
        <Stack direction="row" spacing={2} mb={3} flexWrap="wrap" useFlexGap>
          <SummaryCard label="総投資額" value={summary.total_investment} />
          <SummaryCard
            label="含み損益合計"
            value={summary.total_unrealized_profit}
            colored
          />
          <SummaryCard
            label="確定損益合計"
            value={summary.total_realized_profit}
            colored
          />
          <SummaryCard
            label="保有銘柄数"
            value={String(summary.position_count)}
            plain
          />
        </Stack>
      )}

      {/* タブ */}
      <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 2 }}>
        <Tab label="ポジション" />
        <Tab label="売買履歴" />
      </Tabs>

      {/* ポジション一覧 */}
      {tab === 0 && (
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>コード</TableCell>
                <TableCell>銘柄名</TableCell>
                <TableCell align="right">保有数</TableCell>
                <TableCell align="right">平均取得</TableCell>
                <TableCell align="right">現在値</TableCell>
                <TableCell align="right">含み損益</TableCell>
                <TableCell align="right">確定損益</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {positions.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} align="center">
                    <Typography color="text.secondary" sx={{ py: 2 }}>
                      ポジションがありません。銘柄詳細ページから購入してください。
                    </Typography>
                  </TableCell>
                </TableRow>
              ) : (
                positions.map((p) => {
                  const unrealized = p.unrealized_profit
                    ? parseFloat(p.unrealized_profit)
                    : null;
                  return (
                    <TableRow
                      key={p.stock_code}
                      hover
                      sx={{ cursor: "pointer" }}
                      onClick={() => navigate(`/stocks/${p.stock_code}`)}
                    >
                      <TableCell>{p.stock_code}</TableCell>
                      <TableCell>{p.stock_name}</TableCell>
                      <TableCell align="right">
                        {p.quantity.toLocaleString()}
                      </TableCell>
                      <TableCell align="right">
                        ¥{parseFloat(p.avg_cost_price).toLocaleString()}
                      </TableCell>
                      <TableCell align="right">
                        {p.latest_price
                          ? `¥${parseFloat(p.latest_price).toLocaleString()}`
                          : "-"}
                      </TableCell>
                      <TableCell align="right">
                        {unrealized !== null ? (
                          <Typography
                            variant="body2"
                            color={
                              unrealized >= 0 ? "success.main" : "error.main"
                            }
                            fontWeight="bold"
                          >
                            {unrealized >= 0 ? "+" : ""}¥
                            {Math.round(unrealized).toLocaleString()}
                            {p.unrealized_profit_pct &&
                              ` (${parseFloat(p.unrealized_profit_pct) >= 0 ? "+" : ""}${p.unrealized_profit_pct}%)`}
                          </Typography>
                        ) : (
                          "-"
                        )}
                      </TableCell>
                      <TableCell align="right">
                        {parseFloat(p.realized_profit_total) !== 0 ? (
                          <Typography
                            variant="body2"
                            color={
                              parseFloat(p.realized_profit_total) >= 0
                                ? "success.main"
                                : "error.main"
                            }
                          >
                            ¥
                            {Math.round(
                              parseFloat(p.realized_profit_total)
                            ).toLocaleString()}
                          </Typography>
                        ) : (
                          "-"
                        )}
                      </TableCell>
                    </TableRow>
                  );
                })
              )}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {/* 売買履歴 */}
      {tab === 1 && (
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>日時</TableCell>
                <TableCell>種別</TableCell>
                <TableCell>銘柄</TableCell>
                <TableCell align="right">数量</TableCell>
                <TableCell align="right">単価</TableCell>
                <TableCell align="right">金額</TableCell>
                <TableCell align="right">損益</TableCell>
                <TableCell>メモ</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {tradesLoading ? (
                <TableRow>
                  <TableCell colSpan={8} align="center">
                    <CircularProgress size={20} />
                  </TableCell>
                </TableRow>
              ) : !trades || trades.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={8} align="center">
                    <Typography color="text.secondary" sx={{ py: 2 }}>
                      売買履歴がありません。
                    </Typography>
                  </TableCell>
                </TableRow>
              ) : (
                trades.map((t) => (
                  <TableRow key={t.id}>
                    <TableCell sx={{ fontSize: "0.8rem", whiteSpace: "nowrap" }}>
                      {new Date(t.traded_at).toLocaleString("ja-JP", {
                        month: "2-digit",
                        day: "2-digit",
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={t.trade_type === "buy" ? "買" : "売"}
                        size="small"
                        color={t.trade_type === "buy" ? "success" : "error"}
                        variant="outlined"
                      />
                    </TableCell>
                    <TableCell>
                      {t.stock_code} {t.stock_name}
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
                    <TableCell sx={{ fontSize: "0.8rem", maxWidth: 120 }}>
                      {t.memo}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {/* リセット確認ダイアログ */}
      <Dialog open={resetOpen} onClose={() => setResetOpen(false)}>
        <DialogTitle>仮想売買データのリセット</DialogTitle>
        <DialogContent>
          <DialogContentText>
            全ての仮想売買データが削除されます。この操作は取り消せません。
            よろしいですか？
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setResetOpen(false)}>キャンセル</Button>
          <Button
            color="error"
            variant="contained"
            onClick={() => {
              resetMutation.mutate();
              setResetOpen(false);
            }}
          >
            リセットする
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

function SummaryCard({
  label,
  value,
  colored,
  plain,
}: {
  label: string;
  value: string;
  colored?: boolean;
  plain?: boolean;
}) {
  const numVal = plain ? 0 : parseFloat(value);
  const color = colored
    ? numVal >= 0
      ? "success.main"
      : "error.main"
    : "text.primary";

  return (
    <Card variant="outlined" sx={{ minWidth: 160, flex: "1 1 0" }}>
      <CardContent sx={{ py: 1.5, "&:last-child": { pb: 1.5 } }}>
        <Typography variant="caption" color="text.secondary">
          {label}
        </Typography>
        <Typography variant="h6" fontWeight="bold" color={color}>
          {plain
            ? value
            : `¥${Math.round(parseFloat(value)).toLocaleString()}`}
        </Typography>
      </CardContent>
    </Card>
  );
}
