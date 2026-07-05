import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { goalsApi } from "@/api/goals";
import type { FinancialGoalInput } from "@/types/goals";

export function useGoals() {
  return useQuery({
    queryKey: ["goals"],
    queryFn: () => goalsApi.list().then((r) => r.data),
  });
}

export function useGoalProgress(goalId: number | null) {
  return useQuery({
    queryKey: ["goal-progress", goalId],
    queryFn: () => goalsApi.progress(goalId as number).then((r) => r.data),
    enabled: goalId != null,
  });
}

export function useCreateGoal() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: FinancialGoalInput) => goalsApi.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["goals"] }),
  });
}

export function useUpdateGoal() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: FinancialGoalInput }) =>
      goalsApi.update(id, data),
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ["goals"] });
      qc.invalidateQueries({ queryKey: ["goal-progress", vars.id] });
    },
  });
}

export function useDeleteGoal() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => goalsApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["goals"] }),
  });
}

export function useReorderGoals() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (orderedIds: number[]) => goalsApi.reorder(orderedIds),
    // 失敗時はサーバーから再取得して整合性を回復
    onError: () => qc.invalidateQueries({ queryKey: ["goals"] }),
  });
}
