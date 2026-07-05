/** 通貨フォーマット（円） */
export function formatCurrency(value: string | number | null | undefined): string {
  if (value == null) return "-";
  const num = typeof value === "string" ? parseFloat(value) : value;
  if (isNaN(num)) return "-";
  return num.toLocaleString("ja-JP", {
    style: "currency",
    currency: "JPY",
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  });
}

/** パーセントフォーマット */
export function formatPercent(value: string | number | null | undefined, digits = 2): string {
  if (value == null) return "-";
  const num = typeof value === "string" ? parseFloat(value) : value;
  if (isNaN(num)) return "-";
  return `${(num * 100).toFixed(digits)}%`;
}

/** 倍率フォーマット */
export function formatMultiple(value: string | number | null | undefined, digits = 2): string {
  if (value == null) return "-";
  const num = typeof value === "string" ? parseFloat(value) : value;
  if (isNaN(num)) return "-";
  return `${num.toFixed(digits)}倍`;
}

/** 小数フォーマット */
export function formatDecimal(value: string | number | null | undefined, digits = 2): string {
  if (value == null) return "-";
  const num = typeof value === "string" ? parseFloat(value) : value;
  if (isNaN(num)) return "-";
  return num.toFixed(digits);
}

/** 数値パース（string → number） */
export function toNumber(value: string | number | null | undefined): number | null {
  if (value == null) return null;
  const num = typeof value === "string" ? parseFloat(value) : value;
  return isNaN(num) ? null : num;
}
