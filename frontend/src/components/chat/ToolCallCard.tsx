import { useState } from "react";
import { Box, Typography, Collapse, IconButton, Chip } from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import BuildIcon from "@mui/icons-material/Build";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import ErrorOutlineIcon from "@mui/icons-material/ErrorOutline";

interface ToolCallCardProps {
  toolName: string;
  args: Record<string, unknown>;
  result: Record<string, unknown> | string;
  succeeded?: boolean;
}

/**
 * Function Calling のツール呼び出し結果を折りたたみ表示する。
 *
 * デフォルトは折りたたみ状態。クリックで展開して引数と結果の JSON を確認できる。
 */
export default function ToolCallCard({
  toolName,
  args,
  result,
  succeeded = true,
}: ToolCallCardProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <Box
      sx={{
        border: "1px solid",
        borderColor: "divider",
        borderRadius: 1,
        bgcolor: "background.default",
        mb: 1,
      }}
    >
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          gap: 1,
          px: 1.5,
          py: 0.75,
          cursor: "pointer",
        }}
        onClick={() => setExpanded((v) => !v)}
      >
        <BuildIcon fontSize="small" color="action" />
        <Typography variant="body2" sx={{ fontFamily: "monospace", flexGrow: 1 }}>
          {toolName}
        </Typography>
        <Chip
          size="small"
          icon={succeeded ? <CheckCircleOutlineIcon /> : <ErrorOutlineIcon />}
          label={succeeded ? "成功" : "失敗"}
          color={succeeded ? "success" : "error"}
          variant="outlined"
        />
        <IconButton size="small">
          {expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
        </IconButton>
      </Box>
      <Collapse in={expanded}>
        <Box sx={{ px: 1.5, pb: 1.5 }}>
          <Typography variant="caption" color="text.secondary">
            引数
          </Typography>
          <Box
            component="pre"
            sx={{
              m: 0,
              p: 1,
              bgcolor: "grey.100",
              borderRadius: 0.5,
              fontSize: "0.75rem",
              overflowX: "auto",
              whiteSpace: "pre-wrap",
              wordBreak: "break-word",
            }}
          >
            {JSON.stringify(args, null, 2)}
          </Box>

          <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: "block" }}>
            結果
          </Typography>
          <Box
            component="pre"
            sx={{
              m: 0,
              p: 1,
              bgcolor: "grey.100",
              borderRadius: 0.5,
              fontSize: "0.75rem",
              overflowX: "auto",
              whiteSpace: "pre-wrap",
              wordBreak: "break-word",
              maxHeight: 240,
            }}
          >
            {typeof result === "string" ? result : JSON.stringify(result, null, 2)}
          </Box>
        </Box>
      </Collapse>
    </Box>
  );
}
