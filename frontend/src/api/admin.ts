/**
 * Admin 管理 API クライアント (is_superuser 専用)。
 *
 * バックエンド `apps/auth_cognito/presentation/urls.py` (`/api/admin/*`) と対応。
 */
import apiClient from "./client";
import type {
  AdminUserListResponse,
  AdminUserRow,
  CognitoUserListResponse,
  UserAllowedEmailInfo,
} from "@/types/admin";

export const adminApi = {
  listUsers: () => apiClient.get<AdminUserListResponse>("/admin/users/"),

  createUser: (email: string) =>
    apiClient.post<AdminUserRow>("/admin/users/", { email }),

  addAllowedEmail: (userId: number, email: string, label = "") =>
    apiClient.post<UserAllowedEmailInfo>(
      `/admin/users/${userId}/allowed-emails/`,
      { email, label },
    ),

  removeAllowedEmail: (userId: number, allowedId: number) =>
    apiClient.delete(`/admin/users/${userId}/allowed-emails/${allowedId}/`),

  deleteCognitoLink: (userId: number, linkId: number) =>
    apiClient.delete(`/admin/users/${userId}/cognito-links/${linkId}/`),

  listCognitoUsers: () =>
    apiClient.get<CognitoUserListResponse>("/admin/cognito-users/"),

  disableUser: (userId: number) =>
    apiClient.post(`/admin/users/${userId}/disable/`),

  enableUser: (userId: number) =>
    apiClient.post(`/admin/users/${userId}/enable/`),

  deleteUser: (userId: number) => apiClient.delete(`/admin/users/${userId}/`),

  disableCognitoUser: (username: string) =>
    apiClient.post(`/admin/cognito-users/${encodeURIComponent(username)}/disable/`),

  enableCognitoUser: (username: string) =>
    apiClient.post(`/admin/cognito-users/${encodeURIComponent(username)}/enable/`),

  deleteCognitoUser: (username: string) =>
    apiClient.delete(`/admin/cognito-users/${encodeURIComponent(username)}/`),
};
