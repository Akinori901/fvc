import { Box, Paper, Typography } from "@mui/material";
import PersonIcon from "@mui/icons-material/Person";
import SmartToyIcon from "@mui/icons-material/SmartToy";
import type { ChatMessage } from "@/api/chat";
import ToolCallCard from "./ToolCallCard";

interface ChatMessageBubbleProps {
  message: ChatMessage;
}

/**
 * チャットメッセージ 1 件の表示。
 *
 * - role=user: 右寄せ、淡い青背景
 * - role=assistant: 左寄せ、白背景
 * - role=tool: ToolCallCard に置き換え（左寄せ）
 */
export default function ChatMessageBubble({ message }: ChatMessageBubbleProps) {
  if (message.role === "tool") {
    return (
      <Box sx={{ display: "flex", justifyContent: "flex-start", mb: 1 }}>
        <Box sx={{ maxWidth: "85%" }}>
          <ToolCallCard
            toolName={message.tool_name || "tool"}
            args={message.tool_args}
            result={message.tool_result && Object.keys(message.tool_result).length > 0 ? message.tool_result : message.content}
            succeeded={message.tool_result && Object.keys(message.tool_result).length > 0}
          />
        </Box>
      </Box>
    );
  }

  const isUser = message.role === "user";
  return (
    <Box
      sx={{
        display: "flex",
        justifyContent: isUser ? "flex-end" : "flex-start",
        gap: 1,
        mb: 1.5,
        alignItems: "flex-start",
      }}
    >
      {!isUser && (
        <Box
          sx={{
            width: 32,
            height: 32,
            borderRadius: "50%",
            bgcolor: "primary.main",
            color: "primary.contrastText",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flexShrink: 0,
          }}
        >
          <SmartToyIcon fontSize="small" />
        </Box>
      )}
      <Paper
        elevation={0}
        sx={{
          maxWidth: "75%",
          px: 1.5,
          py: 1,
          bgcolor: isUser ? "primary.50" : "grey.50",
          border: "1px solid",
          borderColor: "divider",
        }}
      >
        <Typography
          variant="body2"
          sx={{
            whiteSpace: "pre-wrap",
            wordBreak: "break-word",
          }}
        >
          {message.content || (isUser ? "" : "...")}
        </Typography>
      </Paper>
      {isUser && (
        <Box
          sx={{
            width: 32,
            height: 32,
            borderRadius: "50%",
            bgcolor: "grey.300",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flexShrink: 0,
          }}
        >
          <PersonIcon fontSize="small" />
        </Box>
      )}
    </Box>
  );
}
