import { Chip } from "@mui/material";
import { getEvaluationZone, getZoneInfoByZone } from "@/utils/evaluation";
import type { EvaluationZone } from "@/utils/evaluation";

interface Props {
  discountRate?: number;
  zone?: EvaluationZone;
}

export default function EvaluationBadge({ discountRate, zone }: Props) {
  const zoneInfo = zone != null ? getZoneInfoByZone(zone) : getEvaluationZone(discountRate!);

  return (
    <Chip
      label={zoneInfo.label}
      size="small"
      sx={{
        color: zoneInfo.color,
        bgcolor: zoneInfo.bgColor,
        fontWeight: "bold",
      }}
    />
  );
}
