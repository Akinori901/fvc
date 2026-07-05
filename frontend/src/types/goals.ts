export type GoalScopeType = "family" | "members";

export interface FinancialGoal {
  id: number;
  name: string;
  target_value_jpy: string;
  target_date: string; // YYYY-MM-DD
  scope_type: GoalScopeType;
  member_ids: number[];
  is_active: boolean;
  display_order: number;
  created_at: string | null;
  updated_at: string | null;
}

export interface FinancialGoalInput {
  name: string;
  target_value_jpy: string | number;
  target_date: string; // YYYY-MM-DD
  scope_type: GoalScopeType;
  member_ids?: number[];
}

export interface GoalChartPoint {
  date: string; // YYYY-MM-DD
  actual: number | null;
  ideal: number | null;
  projected: number | null;
}

export type ProjectionStatus = "ahead" | "on_track" | "behind" | "unknown";

export interface GoalProgress {
  goal: FinancialGoal;
  current_value_jpy: string;
  achievement_rate_pct: string;
  ideal_value_now_jpy: string;
  gap_jpy: string;
  avg_monthly_increase_jpy: string | null;
  projected_value_at_target_jpy: string | null;
  projection_status: ProjectionStatus;
  chart: GoalChartPoint[];
}
