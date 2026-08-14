/**
 * 通貨フォーマット。marketType="US" の銘柄はドル建て（$, 小数2桁）、
 * それ以外は従来どおり円建て（¥, 整数）で表示する。
 * 米国株の株価・財務は DB にドルのまま保存されているため、記号のみ切り替える。
 */
export function formatCurrency(
  value: string | number | null | undefined,
  marketType?: string | null,
): string {
  if (value == null) return "-";
  const num = typeof value === "string" ? parseFloat(value) : value;
  if (isNaN(num)) return "-";
  if (marketType === "US") {
    return num.toLocaleString("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  }
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
