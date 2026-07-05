import { useState } from "react";
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
  IconButton,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { mcpApiKeysApi } from "@/api/mcpApiKeys";
import type { IssuedMcpApiKey } from "@/types/mcpApiKey";

export default function McpApiKeySection() {
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["mcpApiKeys"],
    queryFn: () => mcpApiKeysApi.list().then((r) => r.data),
  });

  const [label, setLabel] = useState("");
  const [issued, setIssued] = useState<IssuedMcpApiKey | null>(null);
  const [revokeTarget, setRevokeTarget] = useState<{ id: number; label: string } | null>(null);
  const [copyMessage, setCopyMessage] = useState<string | null>(null);

  const issueMutation = useMutation({
    mutationFn: (l: string) => mcpApiKeysApi.issue(l).then((r) => r.data),
    onSuccess: (res) => {
      setIssued(res);
      setLabel("");
      queryClient.invalidateQueries({ queryKey: ["mcpApiKeys"] });
    },
  });

  const revokeMutation = useMutation({
    mutationFn: (id: number) => mcpApiKeysApi.revoke(id),
    onSuccess: () => {
      setRevokeTarget(null);
      queryClient.invalidateQueries({ queryKey: ["mcpApiKeys"] });
    },
  });

  const handleCopy = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopyMessage("クリップボードにコピーしました");
      setTimeout(() => setCopyMessage(null), 2000);
    } catch {
      setCopyMessage("コピーに失敗しました");
    }
  };

  return (
    <Card variant="outlined" sx={{ mb: 3 }}>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          外部AI連携 APIキー
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Claude Desktop / Claude iOS / ChatGPT Custom GPT などから本サービスのデータを利用するための API キーを発行します。
          発行されたキーは <code>Authorization: Bearer fvc_mcp_xxx</code> ヘッダで送信してください。
          MCP 接続先: <code>http://localhost:18000/mcp</code>、REST API: <code>http://localhost:18000/api/v1/mcp/tools/...</code>
        </Typography>

        {/* 発行フォーム */}
        <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} sx={{ mb: 2 }}>
          <TextField
            size="small"
            label="ラベル（例: Claude Desktop / iOS）"
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            fullWidth
            inputProps={{ maxLength: 100 }}
          />
          <Button
            variant="contained"
            disabled={!label.trim() || issueMutation.isPending}
            onClick={() => issueMutation.mutate(label.trim())}
          >
            キー発行
          </Button>
        </Stack>

        {issueMutation.isError && (
          <Alert severity="error" sx={{ mb: 2 }}>
            キーの発行に失敗しました
          </Alert>
        )}

        {copyMessage && (
          <Alert severity="info" sx={{ mb: 2 }}>
            {copyMessage}
          </Alert>
        )}

        {/* 一覧 */}
        {isLoading ? (
          <Box sx={{ display: "flex", justifyContent: "center", p: 2 }}>
            <CircularProgress />
          </Box>
        ) : (
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>ラベル</TableCell>
                  <TableCell>キー prefix</TableCell>
                  <TableCell>状態</TableCell>
                  <TableCell>最終利用</TableCell>
                  <TableCell>作成日時</TableCell>
                  <TableCell align="right">操作</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {(data?.items ?? []).length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} align="center">
                      <Typography variant="body2" color="text.secondary">
                        まだキーは発行されていません
                      </Typography>
                    </TableCell>
                  </TableRow>
                ) : (
                  data!.items.map((k) => (
                    <TableRow key={k.id}>
                      <TableCell>{k.label}</TableCell>
                      <TableCell>
                        <code>{k.key_prefix}...</code>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={k.is_active ? "有効" : "失効済"}
                          color={k.is_active ? "success" : "default"}
                          size="small"
                        />
                      </TableCell>
                      <TableCell>{k.last_used_at ? new Date(k.last_used_at).toLocaleString("ja-JP") : "-"}</TableCell>
                      <TableCell>{new Date(k.created_at).toLocaleString("ja-JP")}</TableCell>
                      <TableCell align="right">
                        {k.is_active && (
                          <Tooltip title="このキーを失効させる">
                            <IconButton
                              size="small"
                              color="error"
                              onClick={() => setRevokeTarget({ id: k.id, label: k.label })}
                            >
                              <DeleteOutlineIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        )}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </CardContent>

      {/* 発行直後の平文キー表示モーダル */}
      <Dialog open={issued !== null} onClose={() => setIssued(null)} maxWidth="sm" fullWidth>
        <DialogTitle>APIキーを発行しました</DialogTitle>
        <DialogContent>
          <Alert severity="warning" sx={{ mb: 2 }}>
            このキーは <strong>この画面でしか確認できません</strong>。コピーして安全な場所に保存してください。
          </Alert>
          <Typography variant="caption" color="text.secondary">
            ラベル: {issued?.label}
          </Typography>
          <Stack direction="row" spacing={1} alignItems="center" sx={{ mt: 1 }}>
            <TextField
              fullWidth
              size="small"
              value={issued?.plain_key ?? ""}
              InputProps={{ readOnly: true, sx: { fontFamily: "monospace" } }}
            />
            <Tooltip title="クリップボードへコピー">
              <IconButton onClick={() => issued && handleCopy(issued.plain_key)}>
                <ContentCopyIcon />
              </IconButton>
            </Tooltip>
          </Stack>
          <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 2 }}>
            使い方の例（curl）:
            <Box component="pre" sx={{ fontFamily: "monospace", fontSize: "0.75rem", overflowX: "auto" }}>
{`curl -H "Authorization: Bearer ${issued?.plain_key ?? "<key>"}" \\
  http://localhost:18000/api/v1/mcp/tools/get_stock_summary?code=7203`}
            </Box>
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setIssued(null)} variant="contained">
            閉じる
          </Button>
        </DialogActions>
      </Dialog>

      {/* 失効確認モーダル */}
      <Dialog open={revokeTarget !== null} onClose={() => setRevokeTarget(null)}>
        <DialogTitle>キーを失効させますか？</DialogTitle>
        <DialogContent>
          <DialogContentText>
            「{revokeTarget?.label}」を失効させると、このキーでの API 呼び出しは即座にできなくなります。
            この操作は取り消せません。
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRevokeTarget(null)}>キャンセル</Button>
          <Button
            onClick={() => revokeTarget && revokeMutation.mutate(revokeTarget.id)}
            color="error"
            variant="contained"
            disabled={revokeMutation.isPending}
          >
            失効させる
          </Button>
        </DialogActions>
      </Dialog>
    </Card>
  );
}
