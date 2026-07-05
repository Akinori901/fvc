import { Alert, AlertTitle } from "@mui/material";
import { useApiConfigs } from "@/hooks/useSettings";

export default function PlanLimitBanner() {
  const { data: configs } = useApiConfigs();

  const jquants = configs?.find((c) => c.provider === "jquants");

  if (!jquants) return null;

  const features = jquants.plan_features;

  if (features.price_sync && features.financial_sync) return null;

  const messages: string[] = [];
  if (!features.financial_sync) {
    messages.push("財務データの自動同期にはLightプラン以上が必要です");
  }
  if (!features.price_sync) {
    messages.push("株価データの自動同期にはStandardプラン以上が必要です");
  }

  return (
    <Alert severity="warning" sx={{ mb: 2 }}>
      <AlertTitle>
        J-Quants {features.label}プラン（機能制限あり）
      </AlertTitle>
      {messages.map((msg, i) => (
        <div key={i}>{msg}</div>
      ))}
    </Alert>
  );
}
