export type MemberRole = "self" | "spouse" | "child" | "parent" | "other";

export const MEMBER_ROLE_LABELS: Record<MemberRole, string> = {
  self: "本人",
  spouse: "配偶者",
  child: "子",
  parent: "親",
  other: "その他",
};

export type InstitutionType =
  | "securities_jp"
  | "securities_us"
  | "bank"
  | "ideco"
  | "mutual_aid"
  | "company_loan"
  | "insurance"
  | "pension"
  | "other";

export const INSTITUTION_TYPE_LABELS: Record<InstitutionType, string> = {
  securities_jp: "国内証券",
  securities_us: "米国証券",
  bank: "銀行",
  ideco: "iDeCo",
  mutual_aid: "小規模企業共済",
  company_loan: "会社貸付",
  insurance: "保険",
  pension: "年金",
  other: "その他",
};

export type AssetClass =
  | "cash"
  | "jp_stock"
  | "us_stock"
  | "jp_bond"
  | "us_bond"
  | "etf"
  | "fund"
  | "insurance"
  | "mutual_aid"
  | "loan"
  | "real_estate"
  | "other";

export const ASSET_CLASS_LABELS: Record<AssetClass, string> = {
  cash: "現金・預金",
  jp_stock: "国内株式",
  us_stock: "米国株式",
  jp_bond: "国内債券",
  us_bond: "米国債",
  etf: "ETF",
  fund: "投資信託",
  insurance: "保険",
  mutual_aid: "共済",
  loan: "貸付",
  real_estate: "不動産・土地",
  other: "その他",
};

export const ASSET_CLASS_COLORS: Record<AssetClass, string> = {
  jp_stock: "#1565c0",
  us_stock: "#6a1b9a",
  cash: "#2e7d32",
  etf: "#00838f",
  fund: "#558b2f",
  jp_bond: "#4527a0",
  us_bond: "#ad1457",
  insurance: "#c62828",
  mutual_aid: "#ef6c00",
  loan: "#827717",
  real_estate: "#795548",
  other: "#546e7a",
} as Record<AssetClass, string>;

export interface FamilyMember {
  id: number;
  name: string;
  role: MemberRole;
  role_display: string;
  color_code: string;
  display_order: number;
  include_in_family_total: boolean;
}

export interface FamilyMemberInput {
  name: string;
  role: MemberRole;
  color_code?: string;
  display_order?: number;
  include_in_family_total?: boolean;
}

export type TradingType = "spot" | "margin";

export const TRADING_TYPE_LABELS: Record<TradingType, string> = {
  spot: "現物",
  margin: "信用",
};

export type MarginCreditType = "system_6m" | "general_6m" | "general_unlimited";

export const MARGIN_CREDIT_TYPE_LABELS: Record<MarginCreditType, string> = {
  system_6m: "制度信用 (6ヶ月)",
  general_6m: "一般信用 (6ヶ月)",
  general_unlimited: "一般信用 (無期限)",
};

export interface PortfolioAccount {
  id: number;
  family_member_id: number;
  family_member_name: string;
  institution: string;
  institution_type: InstitutionType;
  institution_type_display: string;
  asset_class: AssetClass;
  asset_class_display: string;
  trading_type: TradingType;
  trading_type_display: string;
  nickname: string;
  currency: string;
  notes: string;
  is_active: boolean;
  expected_return_rate: string | null;
  margin_credit_type: MarginCreditType | null;
  margin_credit_type_display: string;
  margin_interest_rate: string | null;
  // 取込漏れ警告。"no_detail"=明細欠落 / "stale"=更新が古い
  import_warnings?: ImportWarning[];
}

// 口座の取込漏れ警告コード
export type ImportWarning = 'no_detail' | 'stale';

export interface PortfolioAccountInput {
  family_member_id: number;
  institution: string;
  institution_type: InstitutionType;
  asset_class: AssetClass;
  trading_type?: TradingType;
  nickname?: string;
  currency?: string;
  notes?: string;
  is_active?: boolean;
  expected_return_rate?: string | null;
  margin_credit_type?: MarginCreditType | null;
  margin_interest_rate?: string | null;
}

export interface AccountHolding {
  id?: number;
  ticker_code?: string;
  asset_name: string;
  asset_type: string;
  quantity?: string | null;
  unit_price?: string | null;
  value_jpy: string;
  cost_jpy?: string | null;
  built_date?: string | null;
}

export interface AccountSnapshot {
  id: number;
  account_id: number;
  snapshot_date: string;
  total_value_jpy: string;
  total_cost_jpy: string | null;
  exchange_rate: string | null;
  notes: string;
  holdings: AccountHolding[];
}

export interface AccountSnapshotListResponse {
  count: number;
  limit: number;
  offset: number;
  results: AccountSnapshot[];
}

export interface AccountSnapshotInput {
  snapshot_date: string;
  total_value_jpy: string | number;
  total_cost_jpy?: string | number | null;
  exchange_rate?: string | number | null;
  notes?: string;
  holdings?: AccountHolding[];
}

export interface AssetClassSummary {
  asset_class: AssetClass;
  label: string;
  value_jpy: string;
}

export interface AccountTypeSummary {
  account_type: string;
  label: string;
  value_jpy: string;
}

export interface TopHoldingSummary {
  name: string;
  value_jpy: string;
}

export interface StockHoldingV2 {
  stock_id: number | null;
  stock_code: string;
  asset_name: string;
  ticker_code: string;
  asset_type: string;
  quantity: string | null;
  unit_price: string | null;
  latest_price: string | null;
  value_jpy: string;
  cost_jpy: string | null;
  unrealized_gain_jpy: string | null;
  account_id: number;
  account_name: string;
  member_name: string;
}

export interface MemberDashboard {
  member_id: number;
  name: string;
  role: MemberRole;
  color_code: string;
  total_value_jpy: string;
  total_cost_jpy: string | null;
  unrealized_gain_jpy: string | null;
  by_asset_class: AssetClassSummary[];
}

export interface AccountRow {
  id: number;
  institution: string;
  nickname: string;
  institution_type: InstitutionType;
  asset_class: AssetClass;
  asset_class_display: string;
  trading_type?: TradingType;
  currency: string;
  member_id: number;
  member_name: string;
  latest_value_jpy: string | null;
  latest_cost_jpy: string | null;
  latest_date: string | null;
}

// CSV インポート関連
export interface CsvParsedHolding {
  ticker_code: string;
  asset_name: string;
  asset_type: string;
  quantity: string;
  unit_price: string | null;
  currency: string;
  value_jpy: string;
  cost_jpy: string | null;
}

export interface CsvHoldingDiff {
  ticker_code: string;
  asset_name: string;
  status: "new" | "removed" | "changed" | "unchanged";
  new_value_jpy: string | null;
  old_value_jpy: string | null;
  new_quantity: string | null;
  old_quantity: string | null;
}

export interface CsvAccountDiff {
  has_existing: boolean;
  existing_snapshot_date: string;
  existing_total_value_jpy: string;
  value_change_jpy: string;
  holdings_diff: CsvHoldingDiff[];
}

export interface CsvAccountGroup {
  asset_type_raw: string;
  account_type_raw: string;
  asset_class: string;
  total_value_jpy: string;
  total_cost_jpy: string;
  currency: string;
  holdings_count: number;
  holdings: CsvParsedHolding[];
  diff?: CsvAccountDiff;
}

export interface CsvPreviewResult {
  provider: string;
  snapshot_date: string;
  exchange_rates: Record<string, string>;
  account_groups: CsvAccountGroup[];
}

export interface CsvImportResult {
  message: string;
  created_count: number;
  updated_count: number;
  preview: CsvPreviewResult;
}

export interface FamilyDashboard {
  view: string;
  total_value_jpy: string;
  total_cost_jpy: string | null;
  unrealized_gain_jpy: string | null;
  latest_snapshot_date: string | null;
  earliest_snapshot_date: string | null;
  by_member: MemberDashboard[];
  by_asset_class: AssetClassSummary[];
  by_account_type: AccountTypeSummary[];
  by_top_holdings: TopHoldingSummary[];
  accounts: AccountRow[];
  stock_holdings_v2: StockHoldingV2[];
}

// X共有用ダッシュボード
export interface MonthlyChartPoint {
  date: string;
  value: number;
  // 株式系評価額のみ (現金/保険/共済等を除く)。月初来パフォーマンス % の分母に使う。
  stock_value?: number;
  nikkei225?: number;
  topix?: number;
  nasdaq100?: number;
  sp500?: number;
}

export interface ShareDashboard {
  label: string;
  total_value_jpy: string;
  total_cost_jpy: string | null;
  unrealized_gain_jpy: string | null;
  latest_snapshot_date: string | null;
  earliest_snapshot_date: string | null;
  yoy_change_jpy: string | null;
  yoy_change_pct: string | null;
  dod_change_jpy: string | null;
  dod_change_pct: string | null;
  by_asset_class: AssetClassSummary[];
  monthly_chart: MonthlyChartPoint[];
  // 月初時点の総資産 (dynamic_valuation 再評価)。MTD 分母用。
  monthly_chart_total_baseline?: string | null;
  // 現在の総資産 (total_value_jpy と同等)。MTD 分子用。
  monthly_chart_total_current?: string | null;
  // 取込漏れ警告の種別ごとの口座数（例: { no_detail: 2, stale: 1 }）
  import_warning_counts?: Record<string, number>;
}

// 資産推移関連
export interface PortfolioHistoryMember {
  id: number;
  name: string;
  color_code: string;
}

export interface PortfolioHistoryPoint {
  date: string;
  total: number;
  members: Record<string, number>;
}

export interface PortfolioHistoryResponse {
  period: string;
  members: PortfolioHistoryMember[];
  history: PortfolioHistoryPoint[];
}

// シミュレーション関連
export type GrowthRateSource =
  | "eps_cagr"
  | "fund_slider"
  | "account_rate"
  | "flat";

export const GROWTH_RATE_SOURCE_LABELS: Record<GrowthRateSource, string> = {
  eps_cagr: "EPS成長率(CAGR)",
  fund_slider: "手動設定",
  account_rate: "口座設定",
  flat: "横ばい",
};

export interface HoldingSimulation {
  asset_name: string;
  ticker_code: string;
  asset_type: string;
  category: AssetClass;
  category_label: string;
  current_value: string;
  growth_rate: string;
  growth_rate_percent: string;
  growth_rate_source: GrowthRateSource;
  projected_value: string;
  yearly_values: string[];
}

export interface CategoryYearly {
  label: string;
  values: string[];
}

export interface SimulationResponse {
  years: number;
  holdings: HoldingSimulation[];
  yearly_totals: string[];
  yearly_by_category: Record<string, CategoryYearly>;
}
