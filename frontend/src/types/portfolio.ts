export type AccountType =
  | "nisa_growth"
  | "nisa_reserve"
  | "specific"
  | "general"
  | "us_securities";

export const ACCOUNT_TYPE_LABELS: Record<AccountType, string> = {
  nisa_growth: "NISA成長投資枠",
  nisa_reserve: "NISAつみたて投資枠",
  specific: "特定口座",
  general: "一般口座",
  us_securities: "米国証券口座",
};