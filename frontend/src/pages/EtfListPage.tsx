import { useState, useMemo } from "react";
import {
  Box,
  Typography,
  Button,
  Stack,
  Chip,
  TextField,
  InputAdornment,
  Select,
  MenuItem,
  Autocomplete,
} from "@mui/material";
import { DataGrid, type GridColDef } from "@mui/x-data-grid";
import SyncIcon from "@mui/icons-material/Sync";
import SearchIcon from "@mui/icons-material/Search";
import { useNavigate } from "react-router-dom";
import { useEtfList } from "@/hooks/useEtfList";
import { useSyncTrigger } from "@/hooks/useSync";
import { formatCurrency, formatPercent } from "@/utils/format";
import type { EtfResult } from "@/types/etf";

function getZoneStyle(zone: string) {
  switch (zone) {
    case "超割安":   return { color: "#1b5e20", bgColor: "#e8f5e9" };
    case "買い推奨": return { color: "#2e7d32", bgColor: "#c8e6c9" };
    case "レンジ中": return { color: "#f57f17", bgColor: "#fff9c4" };
    case "下落警戒": return { color: "#e65100", bgColor: "#ffe0b2" };
    case "購入危険": return { color: "#b71c1c", bgColor: "#ffcdd2" };
    default:        return { color: "#546e7a", bgColor: "#eceff1" };
  }
}

const ZONE_SCORE_MAP: Record<string, number> = {
  "超割安": 4, "買い推奨": 2, "レンジ中": -1, "下落警戒": -3, "購入危険": -4,
};

const columns: GridColDef<EtfResult>[] = [
  { field: "code", headerName: "コード", width: 90 },
  {
    field: "evaluation_zone",
    headerName: "総合評価",
    width: 110,
    sortable: false,
    renderCell: (params) => {
      if (!params.value) return "-";
      const style = getZoneStyle(params.value);
      return (
        <Chip
          label={params.value}
          size="small"
          sx={{ color: style.color, bgcolor: style.bgColor, fontWeight: "bold", fontSize: "0.7rem" }}
        />
      );
    },
  },
  { field: "name", headerName: "銘柄名", flex: 1, minWidth: 180 },
  { field: "sector", headerName: "セクター", width: 140 },
  {
    field: "latest_price",
    headerName: "株価",
    width: 110,
    renderCell: (params) =>
      params.value != null ? formatCurrency(Number(params.value)) : "-",
  },
  {
    field: "dividend_yield",
    headerName: "分配金利回り",
    width: 120,
    renderCell: (params) => {
      if (params.value == null) return "-";
      const val = Number(params.value);
      return (
        <Typography
          variant="body2"
          color={val >= 0.03 ? "success.main" : "text.primary"}
          fontWeight={val >= 0.03 ? "bold" : "normal"}
        >
          {formatPercent(val)}
        </Typography>
      );
    },
  },
  {
    field: "annual_dividend",
    headerName: "年間分配金",
    width: 110,
    renderCell: (params) =>
      params.value != null ? formatCurrency(Number(params.value)) : "-",
  },
  {
    field: "return_52w",
    headerName: "52週リターン",
    width: 120,
    renderCell: (params) => {
      if (params.value == null) return "-";
      const val = Number(params.value);
      return (
        <Typography
          variant="body2"
          color={val >= 0 ? "success.main" : "error.main"}
          fontWeight="bold"
        >
          {formatPercent(val)}
        </Typography>
      );
    },
  },
  {
    field: "net_assets",
    headerName: "純資産総額",
    width: 130,
    renderCell: (params) =>
      params.value != null
        ? `${Number(params.value).toLocaleString()}百万円`
        : "-",
  },
];

export default function EtfListPage() {
  const navigate = useNavigate();
  const { data, isLoading } = useEtfList();
  const syncMutation = useSyncTrigger();

  const [searchText, setSearchText] = useState("");
  const [sector, setSector] = useState<string | null>(null);
  const [minYield, setMinYield] = useState("");
  const [minOverallScore, setMinOverallScore] = useState<number | "">("");

  const sectors = useMemo(() => {
    if (!data) return [];
    return [...new Set(data.map((r) => r.sector).filter(Boolean))].sort();
  }, [data]);

  const filteredResults = useMemo(() => {
    let results = data ?? [];
    if (searchText.trim()) {
      const q = searchText.toLowerCase();
      results = results.filter(
        (r) => r.code.toLowerCase().includes(q) || r.name.toLowerCase().includes(q)
      );
    }
    if (sector) {
      results = results.filter((r) => r.sector === sector);
    }
    if (minYield !== "") {
      const threshold = Number(minYield) / 100;
      results = results.filter(
        (r) => r.dividend_yield != null && Number(r.dividend_yield) >= threshold
      );
    }
    if (minOverallScore !== "") {
      const threshold = Number(minOverallScore);
      results = results.filter((r) => {
        const score = ZONE_SCORE_MAP[r.evaluation_zone ?? ""] ?? -99;
        return score >= threshold;
      });
    }
    return results;
  }, [data, searchText, sector, minYield, minOverallScore]);

  return (
    <Box>
      <Stack
        direction="row"
        justifyContent="space-between"
        alignItems="center"
        sx={{ mb: 2 }}
      >
        <Box>
          <Typography variant="h5">ETF一覧</Typography>
          <Typography variant="body2" color="text.secondary">
            分配金利回り降順 — yfinance / J-Quants Premium
          </Typography>
        </Box>
        <Stack direction="row" spacing={1} alignItems="center">
          <Button
            variant="outlined"
            startIcon={<SyncIcon />}
            onClick={() => syncMutation.mutate({ sync_type: "dividends" })}
            disabled={syncMutation.isPending}
          >
            {syncMutation.isPending ? "同期中..." : "分配金同期"}
          </Button>
        </Stack>
      </Stack>

      <Stack direction="row" spacing={2} alignItems="center" sx={{ mb: 2 }} flexWrap="wrap">
        <TextField
          size="small"
          placeholder="コード・銘柄名で検索"
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          sx={{ width: 240 }}
          slotProps={{
            input: {
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon fontSize="small" sx={{ color: "text.secondary" }} />
                </InputAdornment>
              ),
            },
          }}
        />
        <Autocomplete
          options={sectors}
          value={sector}
          onChange={(_, v) => setSector(v)}
          renderInput={(params) => (
            <TextField {...params} label="セクター" size="small" />
          )}
          sx={{ width: 200 }}
        />
        <TextField
          label="利回り最低"
          size="small"
          value={minYield}
          onChange={(e) => setMinYield(e.target.value)}
          placeholder="例: 3"
          slotProps={{
            input: {
              endAdornment: <Typography variant="caption">%</Typography>,
            },
          }}
          sx={{ width: 120 }}
        />
        <Select
          size="small"
          value={minOverallScore}
          onChange={(e) => setMinOverallScore(e.target.value as number | "")}
          displayEmpty
          sx={{ minWidth: 150 }}
        >
          <MenuItem value="">総合評価: すべて</MenuItem>
          <MenuItem value={-1}>レンジ中以上</MenuItem>
          <MenuItem value={2}>買い推奨以上</MenuItem>
          <MenuItem value={4}>超割安のみ</MenuItem>
        </Select>
        <Typography variant="body2" color="text.secondary">
          {filteredResults.length} 銘柄
          {data && filteredResults.length !== data.length
            ? ` / ${data.length} 件中`
            : ""}
        </Typography>
      </Stack>

      <DataGrid
        rows={filteredResults}
        columns={columns}
        getRowId={(row) => row.code}
        loading={isLoading}
        initialState={{
          pagination: { paginationModel: { pageSize: 25 } },
        }}
        pageSizeOptions={[25, 50, 100]}
        disableRowSelectionOnClick
        onRowClick={(params) => navigate(`/etf/${params.row.code}`)}
        sx={{
          bgcolor: "background.paper",
          "& .MuiDataGrid-row": { cursor: "pointer" },
          "& .MuiDataGrid-row:hover": { bgcolor: "action.hover" },
        }}
        autoHeight
      />
    </Box>
  );
}
