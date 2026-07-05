export interface ApiError {
  detail?: string;
  message?: string;
  [key: string]: unknown;
}
