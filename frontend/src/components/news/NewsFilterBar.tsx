import {
  Box,
  Button,
  MenuItem,
  Stack,
  TextField,
} from "@mui/material";
import type { NewsCategory, NewsListParams } from "@/types/news";

const CATEGORIES: { value: NewsCategory | ""; label: string }[] = [
  { value: "", label: "すべて" },
  { value: "stock", label: "個別銘柄" },
  { value: "market", label: "市場" },
  { value: "fx", label: "FX" },
  { value: "earnings", label: "決算" },
];

interface NewsFilterBarProps {
  filters: NewsListParams;
  onChange: (next: NewsListParams) => void;
  onReset: () => void;
}

export default function NewsFilterBar({ filters, onChange, onReset }: NewsFilterBarProps) {
  return (
    <Box sx={{ mb: 2 }}>
      <Stack
        direction={{ xs: "column", md: "row" }}
        spacing={1.5}
        alignItems={{ xs: "stretch", md: "center" }}
      >
        <TextField
          select
          size="small"
          label="カテゴリ"
          value={filters.category ?? ""}
          onChange={(e) =>
            onChange({
              ...filters,
              category: (e.target.value || undefined) as NewsCategory | undefined,
              page: 1,
            })
          }
          sx={{ minWidth: 140 }}
        >
          {CATEGORIES.map((c) => (
            <MenuItem key={c.value} value={c.value}>
              {c.label}
            </MenuItem>
          ))}
        </TextField>
        <TextField
          size="small"
          type="date"
          label="開始日"
          InputLabelProps={{ shrink: true }}
          value={filters.date_from ?? ""}
          onChange={(e) =>
            onChange({ ...filters, date_from: e.target.value || undefined, page: 1 })
          }
        />
        <TextField
          size="small"
          type="date"
          label="終了日"
          InputLabelProps={{ shrink: true }}
          value={filters.date_to ?? ""}
          onChange={(e) =>
            onChange({ ...filters, date_to: e.target.value || undefined, page: 1 })
          }
        />
        <TextField
          size="small"
          label="キーワード"
          value={filters.keyword ?? ""}
          onChange={(e) =>
            onChange({ ...filters, keyword: e.target.value || undefined, page: 1 })
          }
          sx={{ minWidth: 200 }}
        />
        <Button variant="outlined" size="small" onClick={onReset}>
          リセット
        </Button>
      </Stack>
    </Box>
  );
}
