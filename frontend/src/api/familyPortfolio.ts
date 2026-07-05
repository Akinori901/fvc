import apiClient from "./client";
import type {
  AccountSnapshot,
  AccountSnapshotInput,
  CsvImportResult,
  CsvPreviewResult,
  FamilyDashboard,
  FamilyMember,
  FamilyMemberInput,
  PortfolioAccount,
  PortfolioAccountInput,
  PortfolioHistoryResponse,
  ShareDashboard,
  SimulationResponse,
} from "@/types/familyPortfolio";

export const familyMemberApi = {
  list: () => apiClient.get<FamilyMember[]>("/family-members/"),
  create: (data: FamilyMemberInput) => apiClient.post<FamilyMember>("/family-members/", data),
  update: (id: number, data: FamilyMemberInput) =>
    apiClient.put<FamilyMember>(`/family-members/${id}/`, data),
  delete: (id: number) => apiClient.delete(`/family-members/${id}/`),
};

export const portfolioAccountApi = {
  list: () => apiClient.get<PortfolioAccount[]>("/portfolio-accounts/"),
  create: (data: PortfolioAccountInput) =>
    apiClient.post<PortfolioAccount>("/portfolio-accounts/", data),
  update: (id: number, data: PortfolioAccountInput) =>
    apiClient.put<PortfolioAccount>(`/portfolio-accounts/${id}/`, data),
  delete: (id: number) => apiClient.delete(`/portfolio-accounts/${id}/`),
};

export const accountSnapshotApi = {
  list: (accountId: number) =>
    apiClient.get<AccountSnapshot[]>(`/portfolio-accounts/${accountId}/snapshots/`),
  upsert: (accountId: number, data: AccountSnapshotInput) =>
    apiClient.post<AccountSnapshot>(`/portfolio-accounts/${accountId}/snapshots/`, data),
  update: (accountId: number, date: string, data: AccountSnapshotInput) =>
    apiClient.put<AccountSnapshot>(`/portfolio-accounts/${accountId}/snapshots/${date}/`, data),
  delete: (accountId: number, date: string) =>
    apiClient.delete(`/portfolio-accounts/${accountId}/snapshots/${date}/`),
};

export const familyPortfolioApi = {
  dashboard: (view: "individual" | "family" = "family") =>
    apiClient.get<FamilyDashboard>("/family-portfolio/dashboard/", { params: { view } }),

  previewCsv: (file: File, provider: string, familyMemberId?: number) => {
    const form = new FormData();
    form.append("file", file);
    form.append("provider", provider);
    if (familyMemberId) form.append("family_member_id", String(familyMemberId));
    return apiClient.post<CsvPreviewResult>("/family-portfolio/import-csv/?preview=true", form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },

  importCsv: (file: File, provider: string, familyMemberId: number, snapshotDate?: string) => {
    const form = new FormData();
    form.append("file", file);
    form.append("provider", provider);
    form.append("family_member_id", String(familyMemberId));
    if (snapshotDate) form.append("snapshot_date", snapshotDate);
    return apiClient.post<CsvImportResult>("/family-portfolio/import-csv/", form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },

  simulation: (params: { years: number; view: string; fund_growth_rate: number }) =>
    apiClient.get<SimulationResponse>("/family-portfolio/simulation/", { params }),

  history: (period: string = "1y") =>
    apiClient.get<PortfolioHistoryResponse>("/family-portfolio/history/", { params: { period } }),

  shareDashboard: (member?: string) =>
    apiClient.get<ShareDashboard>("/family-portfolio/share-dashboard/", {
      params: member ? { member } : {},
    }),
};
