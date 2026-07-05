import { Chip } from "@mui/material";
import { getStockAttributes, type StockAttributesInput } from "@/utils/stockAttributes";

interface Props {
  input: StockAttributesInput;
}

export default function StockAttributeBadges({ input }: Props) {
  const attrs = getStockAttributes(input);
  return (
    <>
      {attrs.map((attr) => (
        <Chip
          key={attr.key}
          label={attr.label}
          size="small"
          color={attr.color}
          variant="outlined"
          sx={{ fontSize: "0.7rem", height: 22 }}
        />
      ))}
    </>
  );
}
