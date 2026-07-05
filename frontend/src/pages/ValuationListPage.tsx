import { useNavigate } from "react-router-dom";
import {
  Box,
  Typography,
  Card,
  CardContent,
  Stack,
} from "@mui/material";
import { useValuations } from "@/hooks/useValuations";
import EvaluationBadge from "@/components/common/EvaluationBadge";
import LoadingSpinner from "@/components/common/LoadingSpinner";
import ErrorAlert from "@/components/common/ErrorAlert";
import { formatCurrency, formatPercent, formatMultiple } from "@/utils/format";

export default function ValuationListPage() {
  const navigate = useNavigate();
  const { data: valuations, isLoading, error } = useValuations();

  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorAlert />;

  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        算出履歴
      </Typography>

      {valuations && valuations.length > 0 ? (
        <Stack spacing={2}>
          {valuations.map((v) => (
            <Card
              key={v.id}
              sx={{
                cursor: "pointer",
                "&:hover": { bgcolor: "action.hover" },
              }}
              onClick={() => navigate(`/valuations/${v.id}`)}
            >
              <CardContent>
                <Stack
                  direction="row"
                  justifyContent="space-between"
                  alignItems="center"
                >
                  <Stack direction="row" spacing={3}>
                    <Box>
                      <Typography variant="body2" color="text.secondary">
                        適正株価
                      </Typography>
                      <Typography variant="body1" fontWeight="bold">
                        {formatCurrency(v.fair_value)}
                      </Typography>
                    </Box>
                    <Box>
                      <Typography variant="body2" color="text.secondary">
                        現在株価
                      </Typography>
                      <Typography variant="body1">
                        {formatCurrency(v.current_price)}
                      </Typography>
                    </Box>
                    <Box>
                      <Typography variant="body2" color="text.secondary">
                        成長率
                      </Typography>
                      <Typography variant="body1">
                        {formatPercent(v.growth_rate)}
                      </Typography>
                    </Box>
                    <Box>
                      <Typography variant="body2" color="text.secondary">
                        適正PBR
                      </Typography>
                      <Typography variant="body1">
                        {formatMultiple(v.fair_pbr)}
                      </Typography>
                    </Box>
                    <Box>
                      <Typography variant="body2" color="text.secondary">
                        乖離率
                      </Typography>
                      <Typography variant="body1">
                        {formatPercent(v.discount_rate)}
                      </Typography>
                    </Box>
                  </Stack>
                  <EvaluationBadge
                    discountRate={parseFloat(v.discount_rate)}
                  />
                </Stack>
              </CardContent>
            </Card>
          ))}
        </Stack>
      ) : (
        <Card>
          <CardContent>
            <Typography color="text.secondary" align="center">
              まだ算出結果がありません。
            </Typography>
          </CardContent>
        </Card>
      )}
    </Box>
  );
}
