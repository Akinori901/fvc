export interface PlanFeatures {
  label: string;
  stock_list_sync: boolean;
  financial_sync: boolean;
  financial_years: number;
  price_sync: boolean;
  manual_calculation: boolean;
}

export interface ApiConfigInfo {
  provider: string;
  is_enabled: boolean;
  plan: string;
  plan_features: PlanFeatures;
}
