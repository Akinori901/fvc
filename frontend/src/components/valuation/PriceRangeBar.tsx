import { Box, Typography, Stack } from "@mui/material";
import { getAllZones } from "@/utils/evaluation";
import { formatCurrency } from "@/utils/format";

interface Props {
  fairValue: number;
  currentPrice: number;
}

export default function PriceRangeBar({ fairValue, currentPrice }: Props) {
  const zones = getAllZones();
  const ratio = currentPrice / fairValue;
  // ratio < 0.7 → 超割安, 0.7-0.9 → 割安, 0.9-1.1 → 適正, 1.1-1.3 → 割高, >1.3 → 危険
  const position = Math.min(Math.max(((ratio - 0.5) / 1.0) * 100, 0), 100);

  return (
    <Box sx={{ mt: 2 }}>
      <Typography variant="body2" color="text.secondary" gutterBottom>
        価格レンジ
      </Typography>
      <Box sx={{ position: "relative", height: 32, borderRadius: 1, overflow: "hidden", display: "flex" }}>
        {zones.map((z) => (
          <Box
            key={z.zone}
            sx={{ flex: 1, bgcolor: z.bgColor, display: "flex", alignItems: "center", justifyContent: "center" }}
          >
            <Typography variant="caption" sx={{ color: z.color, fontWeight: "bold" }}>
              {z.label}
            </Typography>
          </Box>
        ))}
        <Box
          sx={{
            position: "absolute",
            left: `${position}%`,
            top: 0,
            bottom: 0,
            width: 3,
            bgcolor: "primary.main",
            transform: "translateX(-50%)",
          }}
        />
      </Box>
      <Stack direction="row" justifyContent="space-between" sx={{ mt: 0.5 }}>
        <Typography variant="caption" color="text.secondary">
          {formatCurrency(fairValue * 0.5)}
        </Typography>
        <Typography variant="caption" color="text.secondary">
          適正: {formatCurrency(fairValue)}
        </Typography>
        <Typography variant="caption" color="text.secondary">
          {formatCurrency(fairValue * 1.5)}
        </Typography>
      </Stack>
    </Box>
  );
}
