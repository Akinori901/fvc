import { Card, CardContent, Typography, Stack, Box } from "@mui/material";
import type { ValuationResult } from "@/types/valuation";
import EvaluationBadge from "@/components/common/EvaluationBadge";
import { formatCurrency, formatPercent, formatMultiple } from "@/utils/format";
import { getEvaluationZone } from "@/utils/evaluation";

interface Props {
  result: ValuationResult;
}

export default function ResultSummary({ result }: Props) {
  const discountRate = parseFloat(result.discount_rate);
  const zone = getEvaluationZone(discountRate);

  return (
    <Card
      sx={{
        border: 2,
        borderColor: zone.color,
        bgcolor: zone.bgColor,
      }}
    >
      <CardContent>
        <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
          <Typography variant="h6">算出結果</Typography>
          <EvaluationBadge discountRate={discountRate} />
        </Stack>

        <Stack direction="row" spacing={4}>
          <Box>
            <Typography variant="body2" color="text.secondary">
              適正株価
            </Typography>
            <Typography variant="h5" fontWeight="bold">
              {formatCurrency(result.fair_value)}
            </Typography>
          </Box>
          <Box>
            <Typography variant="body2" color="text.secondary">
              現在株価
            </Typography>
            <Typography variant="h5">
              {formatCurrency(result.current_price)}
            </Typography>
          </Box>
          <Box>
            <Typography variant="body2" color="text.secondary">
              乖離率
            </Typography>
            <Typography
              variant="h5"
              sx={{ color: discountRate >= 0 ? "success.main" : "error.main" }}
            >
              {formatPercent(result.discount_rate)}
            </Typography>
          </Box>
        </Stack>

        <Stack direction="row" spacing={4} sx={{ mt: 2 }}>
          <Box>
            <Typography variant="body2" color="text.secondary">
              適正PBR
            </Typography>
            <Typography variant="body1">
              {formatMultiple(result.fair_pbr)}
            </Typography>
          </Box>
          <Box>
            <Typography variant="body2" color="text.secondary">
              成長率（入力）
            </Typography>
            <Typography variant="body1">
              {formatPercent(result.growth_rate)}
            </Typography>
          </Box>
          <Box>
            <Typography variant="body2" color="text.secondary">
              判定
            </Typography>
            <Typography variant="body1" fontWeight="bold">
              {result.is_undervalued ? "割安" : "割高"}
            </Typography>
          </Box>
        </Stack>

        {result.implied_growth_rate != null && (
          <Stack direction="row" spacing={4} sx={{ mt: 2, pt: 2, borderTop: 1, borderColor: "divider" }}>
            <Box>
              <Typography variant="body2" color="text.secondary">
                現在PBR
              </Typography>
              <Typography variant="body1">
                {formatMultiple(result.current_pbr)}
              </Typography>
            </Box>
            <Box>
              <Typography variant="body2" color="text.secondary">
                市場が織り込む成長率
              </Typography>
              <Typography variant="body1" fontWeight="bold" color="primary">
                {formatPercent(result.implied_growth_rate)}
              </Typography>
            </Box>
            <Box>
              <Typography variant="body2" color="text.secondary">
                使用ROE
              </Typography>
              <Typography variant="body1">
                {formatPercent(result.roe)}
              </Typography>
            </Box>
          </Stack>
        )}
      </CardContent>
    </Card>
  );
}
