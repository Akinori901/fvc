import { useState } from "react";
import {
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
  Stack,
  TextField,
  Typography,
  Alert,
  Chip,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from "@mui/material";
import type { SelectChangeEvent } from "@mui/material";
import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome";
import SettingsIcon from "@mui/icons-material/Settings";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import { aiApi, type AnalyzeRequest, type AnalyzeResult, type ExpertRole } from "@/api/ai";

const QUESTION_TYPES: {
  value: AnalyzeRequest["question_type"];
  label: string;
}[] = [
  { value: "pbr_low", label: "なぜPBRが低いのか" },
  { value: "investment_risk", label: "投資リスクの分析" },
  { value: "growth_outlook", label: "成長見通しの考察" },
  { value: "price_forecast", label: "3ヶ月後の予想株価" },
  { value: "price_drop_reason", label: "株価急落の原因" },
  { value: "dividend_analysis", label: "配当分析" },
  { value: "sector_comparison", label: "セクター内比較" },
  { value: "custom", label: "カスタム質問" },
];

const EXPERT_ROLES: { value: ExpertRole; label: string; description: string }[] = [
  { value: "general", label: "汎用アナリスト", description: "標準のバランス型分析" },
  { value: "quant", label: "クオンツ", description: "統計・ファクター・ボラティリティ重視" },
  { value: "fundamental", label: "ファンダメンタルズ", description: "財務・業績・本質的価値重視" },
  { value: "macro", label: "マクロ", description: "金利・為替・景気循環の視点" },
  { value: "technical", label: "テクニカル", description: "チャート・モメンタム・需給の視点" },
  { value: "risk_mgmt", label: "リスク管理", description: "下振れシナリオ・ドローダウン重視" },
];

interface Props {
  stockCode: string;
}

export default function AiAnalysisPanel({ stockCode }: Props) {
  const navigate = useNavigate();
  const [questionType, setQuestionType] =
    useState<AnalyzeRequest["question_type"]>("pbr_low");
  const [customQuestion, setCustomQuestion] = useState("");
  const [expertRole, setExpertRole] = useState<ExpertRole>("general");
  const [result, setResult] = useState<AnalyzeResult | null>(null);

  const { data: aiConfig, isLoading: configLoading } = useQuery({
    queryKey: ["aiConfig"],
    queryFn: () => aiApi.getConfig().then((r) => r.data),
  });

  const analyzeMutation = useMutation({
    mutationFn: () =>
      aiApi
        .analyzeStock(stockCode, {
          question_type: questionType,
          custom_question: questionType === "custom" ? customQuestion : undefined,
          expert_role: expertRole,
        })
        .then((r) => r.data),
    onSuccess: (data) => setResult(data),
  });

  if (configLoading) return null;

  // AI設定未登録 or 無効の場合
  if (!aiConfig?.is_enabled || !aiConfig?.has_api_key) {
    return (
      <Card variant="outlined">
        <CardContent>
          <Stack spacing={2} alignItems="center" sx={{ py: 2 }}>
            <AutoAwesomeIcon sx={{ fontSize: 40, color: "text.secondary" }} />
            <Typography variant="body1" color="text.secondary" align="center">
              AI分析を使用するには、Gemini APIキーの登録が必要です。
            </Typography>
            <Button
              variant="outlined"
              startIcon={<SettingsIcon />}
              onClick={() => navigate("/settings")}
            >
              設定ページへ
            </Button>
          </Stack>
        </CardContent>
      </Card>
    );
  }

  const errorMsg =
    analyzeMutation.isError && analyzeMutation.error instanceof Error
      ? (analyzeMutation.error as { response?: { data?: { detail?: string } } })
          ?.response?.data?.detail ?? analyzeMutation.error.message
      : null;

  return (
    <Card variant="outlined">
      <CardContent>
        <Stack spacing={2}>
          <Stack direction="row" alignItems="center" spacing={1}>
            <AutoAwesomeIcon fontSize="small" color="action" />
            <Typography variant="subtitle2" color="text.secondary">
              AI分析（{aiConfig.model}）
            </Typography>
          </Stack>

          <FormControl size="small" sx={{ maxWidth: 320 }}>
            <InputLabel id="expert-role-label">専門家視点</InputLabel>
            <Select
              labelId="expert-role-label"
              label="専門家視点"
              value={expertRole}
              onChange={(e: SelectChangeEvent) => {
                setExpertRole(e.target.value as ExpertRole);
                setResult(null);
              }}
            >
              {EXPERT_ROLES.map((role) => (
                <MenuItem key={role.value} value={role.value}>
                  <Box>
                    <Typography variant="body2">{role.label}</Typography>
                    <Typography variant="caption" color="text.secondary">
                      {role.description}
                    </Typography>
                  </Box>
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <Stack direction="row" spacing={1} flexWrap="wrap">
            {QUESTION_TYPES.map((qt) => (
              <Chip
                key={qt.value}
                label={qt.label}
                onClick={() => {
                  setQuestionType(qt.value);
                  setResult(null);
                }}
                color={questionType === qt.value ? "primary" : "default"}
                variant={questionType === qt.value ? "filled" : "outlined"}
                size="small"
              />
            ))}
          </Stack>

          {questionType === "custom" && (
            <TextField
              label="質問内容"
              multiline
              rows={2}
              value={customQuestion}
              onChange={(e) => setCustomQuestion(e.target.value)}
              placeholder="例: この銘柄が注目されている理由を教えてください"
              fullWidth
              inputProps={{ maxLength: 500 }}
            />
          )}

          <Button
            variant="contained"
            startIcon={
              analyzeMutation.isPending ? (
                <CircularProgress size={16} color="inherit" />
              ) : (
                <AutoAwesomeIcon />
              )
            }
            onClick={() => {
              setResult(null);
              analyzeMutation.mutate();
            }}
            disabled={
              analyzeMutation.isPending ||
              (questionType === "custom" && !customQuestion.trim())
            }
          >
            {analyzeMutation.isPending ? "分析中..." : "AI分析を実行"}
          </Button>

          {errorMsg && (
            <Alert severity="error">
              {errorMsg}
            </Alert>
          )}

          {result && (
            <Box>
              <Box
                sx={{
                  "& h1, & h2, & h3, & h4": {
                    mt: 2,
                    mb: 1,
                    fontSize: "1rem",
                    fontWeight: "bold",
                  },
                  "& h3": { fontSize: "0.95rem" },
                  "& p": { my: 0.5, fontSize: "0.875rem", lineHeight: 1.8 },
                  "& ul, & ol": { pl: 3, my: 0.5 },
                  "& li": { fontSize: "0.875rem", lineHeight: 1.8 },
                  "& strong": { fontWeight: "bold" },
                  "& hr": { my: 2 },
                }}
              >
                <ReactMarkdown>{result.analysis}</ReactMarkdown>
              </Box>
              <Typography
                variant="caption"
                color="text.secondary"
                sx={{ mt: 1, display: "block" }}
              >
                モデル: {result.model} • トークン:{" "}
                {result.prompt_tokens + result.completion_tokens}
              </Typography>
            </Box>
          )}
        </Stack>
      </CardContent>
    </Card>
  );
}
