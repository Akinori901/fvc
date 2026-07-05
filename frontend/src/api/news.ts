import apiClient from "./client";
import type { NewsListParams, NewsListResponse } from "@/types/news";

export const newsApi = {
  list: (params: NewsListParams = {}) =>
    apiClient.get<NewsListResponse>("/news/", { params }),

  listForStock: (code: string, params: Pick<NewsListParams, "page" | "page_size"> = {}) =>
    apiClient.get<NewsListResponse>(`/news/stocks/${code}/`, { params }),
};
