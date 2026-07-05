import { Autocomplete, TextField } from "@mui/material";
import type { Stock } from "@/types/stock";

interface Props {
  stocks: Stock[];
  onSelect: (stock: Stock | null) => void;
  label?: string;
}

export default function StockSearchBar({
  stocks,
  onSelect,
  label = "銘柄検索",
}: Props) {
  return (
    <Autocomplete
      options={stocks}
      getOptionLabel={(opt) => `${opt.code} - ${opt.name}`}
      onChange={(_e, value) => onSelect(value)}
      renderInput={(params) => (
        <TextField {...params} label={label} size="small" />
      )}
      isOptionEqualToValue={(opt, val) => opt.code === val.code}
      noOptionsText="該当する銘柄がありません"
      sx={{ minWidth: 300 }}
    />
  );
}
