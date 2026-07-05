export interface StockAttributesInput {
  dividend_yield?: string | number | null;
  consecutive_dividend_years?: number | null;
  progressive_dividend_years?: number | null;
  is_owner_managed?: boolean | null;
}

export type StockAttributeKey =
  | "high_dividend"
  | "consecutive_dividend"
  | "progressive_dividend"
  | "owner_managed";

export interface StockAttribute {
  key: StockAttributeKey;
  label: string;
  color: "success" | "info" | "warning" | "default";
}

const HIGH_DIVIDEND_THRESHOLD = 0.035;
const DIVIDEND_YEARS_THRESHOLD = 5;

export function getStockAttributes(input: StockAttributesInput): StockAttribute[] {
  const result: StockAttribute[] = [];
  const dy = input.dividend_yield != null ? Number(input.dividend_yield) : null;
  if (dy != null && !Number.isNaN(dy) && dy >= HIGH_DIVIDEND_THRESHOLD) {
    result.push({ key: "high_dividend", label: "高配当", color: "success" });
  }
  if ((input.consecutive_dividend_years ?? 0) >= DIVIDEND_YEARS_THRESHOLD) {
    result.push({ key: "consecutive_dividend", label: "連続配当", color: "info" });
  }
  if ((input.progressive_dividend_years ?? 0) >= DIVIDEND_YEARS_THRESHOLD) {
    result.push({ key: "progressive_dividend", label: "累進配当", color: "info" });
  }
  if (input.is_owner_managed) {
    result.push({ key: "owner_managed", label: "オーナー経営", color: "warning" });
  }
  return result;
}
