import { Box, Typography } from "@mui/material";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";
import { DataGrid, type GridColDef } from "@mui/x-data-grid";
import { useQuery } from "@tanstack/react-query";
import { dividendApi, type DividendRecord } from "@/api/dividends";
import { formatCurrency } from "@/utils/format";

interface Props {
  stockCode: string;
}

const columns: GridColDef<DividendRecord>[] = [
  { field: "date", headerName: "権利落ち日", width: 130 },
  {
    field: "amount",
    headerName: "1株/口あたり分配金",
    width: 160,
    renderCell: (params) => formatCurrency(Number(params.value)),
  },
  { field: "source", headerName: "データソース", width: 120 },
];

export default function DividendHistoryPanel({ stockCode }: Props) {
  const { data: dividends, isLoading } = useQuery({
    queryKey: ["stockDividends", stockCode],
    queryFn: () => dividendApi.getStockDividends(stockCode).then((r) => r.data),
    enabled: !!stockCode,
  });

  if (isLoading) return null;

  if (!dividends || dividends.length === 0) {
    return (
      <Typography color="text.secondary" sx={{ py: 4, textAlign: "center" }}>
        分配金データがありません。分配金同期を実行してください。
      </Typography>
    );
  }

  const chartData = [...dividends]
    .reverse()
    .map((d) => ({
      date: d.date,
      amount: Number(d.amount),
    }));

  return (
    <Box>
      {chartData.length > 1 && (
        <Box sx={{ width: "100%", height: 300, mb: 3 }}>
          <ResponsiveContainer>
            <BarChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 10 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 11 }}
                tickFormatter={(v: string) => v.slice(0, 7)}
              />
              <YAxis
                tick={{ fontSize: 11 }}
                tickFormatter={(v: number) => `¥${v.toLocaleString()}`}
              />
              <Tooltip
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                formatter={((value: number) => [`¥${value.toLocaleString()}`, "分配金"]) as any}
              />
              <Bar dataKey="amount" fill="#66bb6a" />
            </BarChart>
          </ResponsiveContainer>
        </Box>
      )}

      <DataGrid
        rows={dividends}
        columns={columns}
        getRowId={(row) => row.date}
        initialState={{
          pagination: { paginationModel: { pageSize: 10 } },
        }}
        pageSizeOptions={[10, 25]}
        disableRowSelectionOnClick
        sx={{ bgcolor: "background.paper" }}
        autoHeight
      />
    </Box>
  );
}
