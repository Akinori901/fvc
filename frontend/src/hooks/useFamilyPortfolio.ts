import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  familyMemberApi,
  portfolioAccountApi,
  accountSnapshotApi,
  familyPortfolioApi,
} from "@/api/familyPortfolio";
import type {
  AccountSnapshotInput,
  FamilyMemberInput,
  PortfolioAccountInput,
} from "@/types/familyPortfolio";

// -----------------------------------------------
// 家族メンバー
// -----------------------------------------------

export function useFamilyMembers() {
  return useQuery({
    queryKey: ["family-members"],
    queryFn: () => familyMemberApi.list().then((r) => r.data),
  });
}

export function useCreateFamilyMember() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: FamilyMemberInput) => familyMemberApi.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["family-members"] }),
  });
}

export function useUpdateFamilyMember() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: FamilyMemberInput }) =>
      familyMemberApi.update(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["family-members"] }),
  });
}

export function useDeleteFamilyMember() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => familyMemberApi.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["family-members"] });
      qc.invalidateQueries({ queryKey: ["portfolio-accounts"] });
    },
  });
}

// -----------------------------------------------
// 口座
// -----------------------------------------------

export function usePortfolioAccounts() {
  return useQuery({
    queryKey: ["portfolio-accounts"],
    queryFn: () => portfolioAccountApi.list().then((r) => r.data),
  });
}

export function useCreatePortfolioAccount() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: PortfolioAccountInput) => portfolioAccountApi.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["portfolio-accounts"] }),
  });
}

export function useUpdatePortfolioAccount() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: PortfolioAccountInput }) =>
      portfolioAccountApi.update(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["portfolio-accounts"] }),
  });
}

export function useDeletePortfolioAccount() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => portfolioAccountApi.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["portfolio-accounts"] });
      qc.invalidateQueries({ queryKey: ["family-portfolio-dashboard"] });
    },
  });
}

// -----------------------------------------------
// スナップショット
// -----------------------------------------------

export function useAccountSnapshots(accountId: number) {
  return useQuery({
    queryKey: ["account-snapshots", accountId],
    queryFn: () => accountSnapshotApi.list(accountId).then((r) => r.data),
    enabled: accountId > 0,
  });
}

export function useUpsertSnapshot() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ accountId, data }: { accountId: number; data: AccountSnapshotInput }) =>
      accountSnapshotApi.upsert(accountId, data),
    onSuccess: (_, { accountId }) => {
      qc.invalidateQueries({ queryKey: ["account-snapshots", accountId] });
      qc.invalidateQueries({ queryKey: ["family-portfolio-dashboard"] });
    },
  });
}

export function useDeleteSnapshot() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ accountId, date }: { accountId: number; date: string }) =>
      accountSnapshotApi.delete(accountId, date),
    onSuccess: (_, { accountId }) => {
      qc.invalidateQueries({ queryKey: ["account-snapshots", accountId] });
      qc.invalidateQueries({ queryKey: ["family-portfolio-dashboard"] });
    },
  });
}

// -----------------------------------------------
// ダッシュボード
// -----------------------------------------------

export function useFamilyPortfolioDashboard(view: "individual" | "family" = "family") {
  return useQuery({
    queryKey: ["family-portfolio-dashboard", view],
    queryFn: () => familyPortfolioApi.dashboard(view).then((r) => r.data),
  });
}

// -----------------------------------------------
// X共有用ダッシュボード
// -----------------------------------------------

export function useShareDashboard(member?: string) {
  return useQuery({
    queryKey: ["share-dashboard", member],
    queryFn: () => familyPortfolioApi.shareDashboard(member).then((r) => r.data),
  });
}

// -----------------------------------------------
// 資産推移
// -----------------------------------------------

export function usePortfolioHistory(period: string) {
  return useQuery({
    queryKey: ["portfolio-history", period],
    queryFn: () => familyPortfolioApi.history(period).then((r) => r.data),
  });
}

// -----------------------------------------------
// CSV インポート
// -----------------------------------------------

export function usePreviewCsv() {
  return useMutation({
    mutationFn: ({ file, provider, familyMemberId }: { file: File; provider: string; familyMemberId?: number }) =>
      familyPortfolioApi.previewCsv(file, provider, familyMemberId).then((r) => r.data),
  });
}

export function useImportCsv() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      file,
      provider,
      familyMemberId,
      snapshotDate,
    }: {
      file: File;
      provider: string;
      familyMemberId: number;
      snapshotDate?: string;
    }) => familyPortfolioApi.importCsv(file, provider, familyMemberId, snapshotDate).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["family-portfolio-dashboard"] });
      qc.invalidateQueries({ queryKey: ["portfolio-accounts"] });
    },
  });
}
