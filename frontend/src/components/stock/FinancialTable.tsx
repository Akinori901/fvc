import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
} from "@mui/material";
import type { StockFinancial } from "@/types/stock";
import { formatCurrency, formatPercent, formatDecimal } from "@/utils/format";

interface Props {
  financials: StockFinancial[];
  marketType?: string; // "US" ならドル建て表示
}

export default function FinancialTable({ financials, marketType }: Props) {
  const sorted = [...financials].sort((a, b) => b.fiscal_year - a.fiscal_year);

  return (
    <TableContainer component={Paper} variant="outlined">
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>年度</TableCell>
            <TableCell align="right">BPS</TableCell>
            <TableCell align="right">EPS</TableCell>
            <TableCell align="right">ROE</TableCell>
            <TableCell align="right">純資産</TableCell>
            <TableCell align="right">発行済株式数</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {sorted.map((f) => (
            <TableRow key={f.id}>
              <TableCell>{f.fiscal_year}</TableCell>
              <TableCell align="right">{formatDecimal(f.bps)}</TableCell>
              <TableCell align="right">{formatDecimal(f.eps)}</TableCell>
              <TableCell align="right">
                {f.eps != null && f.bps != null && Number(f.bps) !== 0
                  ? formatPercent(Number(f.eps) / Number(f.bps))
                  : "-"}
              </TableCell>
              <TableCell align="right">
                {f.net_assets != null
                  ? formatCurrency(f.net_assets * 1_000_000, marketType)
                  : "-"}
              </TableCell>
              <TableCell align="right">
                {f.total_shares?.toLocaleString() ?? "-"}
              </TableCell>
            </TableRow>
          ))}
          {sorted.length === 0 && (
            <TableRow>
              <TableCell colSpan={6} align="center">
                財務データがありません
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </TableContainer>
  );
}
