import { useParams, useNavigate } from "react-router-dom";
import { Box, Typography, Button } from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import { useValuation } from "@/hooks/useValuations";
import ResultSummary from "@/components/valuation/ResultSummary";
import PriceRangeBar from "@/components/valuation/PriceRangeBar";
import LoadingSpinner from "@/components/common/LoadingSpinner";
import ErrorAlert from "@/components/common/ErrorAlert";

export default function ValuationDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: valuation, isLoading, error } = useValuation(Number(id));

  if (isLoading) return <LoadingSpinner />;
  if (error || !valuation) return <ErrorAlert message="算出結果が見つかりません" />;

  return (
    <Box>
      <Button
        startIcon={<ArrowBackIcon />}
        onClick={() => navigate("/valuations")}
        sx={{ mb: 1 }}
      >
        算出履歴に戻る
      </Button>

      <Typography variant="h5" gutterBottom>
        算出結果詳細
      </Typography>

      <ResultSummary result={valuation} />
      <PriceRangeBar
        fairValue={parseFloat(valuation.fair_value)}
        currentPrice={parseFloat(valuation.current_price)}
      />
    </Box>
  );
}
