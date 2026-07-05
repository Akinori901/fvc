import apiClient from "./client";
import type { FinancialGoal, FinancialGoalInput, GoalProgress } from "@/types/goals";

export const goalsApi = {
  list: () => apiClient.get<FinancialGoal[]>("/goals/"),
  create: (data: FinancialGoalInput) => apiClient.post<FinancialGoal>("/goals/", data),
  update: (id: number, data: FinancialGoalInput) =>
    apiClient.put<FinancialGoal>(`/goals/${id}/`, data),
  delete: (id: number) => apiClient.delete(`/goals/${id}/`),
  progress: (id: number) => apiClient.get<GoalProgress>(`/goals/${id}/progress/`),
  reorder: (orderedIds: number[]) =>
    apiClient.put<void>("/goals/reorder/", { ordered_ids: orderedIds }),
};
