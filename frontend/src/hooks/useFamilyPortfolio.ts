import { useQuery, useMutation, useQueryClient, useInfiniteQuery } from "@tanstack/react-query";
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

const SNAPSHOTS_PAGE_SIZE = 12;

/** スナップショット履歴を12件ずつページング取得（「もっと見る」で追加ロード） */
export function useAccountSnapshots(accountId: number) {
  return useInfiniteQuery({
    queryKey: ["account-snapshots", accountId],
    queryFn: ({ pageParam = 0 }) =>
      accountSnapshotApi.list(accountId, SNAPSHOTS_PAGE_SIZE, pageParam).then((r) => r.data),
    initialPageParam: 0,
    getNextPageParam: (lastPage) => {
      const loaded = lastPage.offset + lastPage.results.length;
      return loaded < lastPage.count ? loaded : undefined;
    },
    enabled: accountId > 0,
  });
}

/** 特定日のスナップショット単体を holdings 込みで取得（フォーム読み込み用） */
export function useAccountSnapshot(accountId: number, date: string | null) {
  return useQuery({
    queryKey: ["account-snapshot", accountId, date],
    queryFn: () => accountSnapshotApi.get(accountId, date as string).then((r) => r.data),
    enabled: accountId > 0 && !!date,
    retry: false,
  });
}

export function useUpsertSnapshot() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ accountId, data }: { accountId: number; data: AccountSnapshotInput }) =>
      accountSnapshotApi.upsert(accountId, data),
    onSuccess: (_, { accountId, data }) => {
      qc.invalidateQueries({ queryKey: ["account-snapshots", accountId] });
      qc.invalidateQueries({ queryKey: ["account-snapshot", accountId, data.snapshot_date] });
      qc.invalidateQueries({ queryKey: ["family-portfolio-dashboard"] });
    },
  });
}

export function useDeleteSnapshot() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ accountId, date }: { accountId: number; date: string }) =>
      accountSnapshotApi.delete(accountId, date),
    onSuccess: (_, { accountId, date }) => {
      qc.invalidateQueries({ queryKey: ["account-snapshots", accountId] });
      qc.invalidateQueries({ queryKey: ["account-snapshot", accountId, date] });
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
