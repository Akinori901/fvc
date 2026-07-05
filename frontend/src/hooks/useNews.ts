import { useQuery } from "@tanstack/react-query";
import { newsApi } from "@/api/news";
import type { NewsListParams } from "@/types/news";

export function useNewsList(params: NewsListParams = {}) {
  return useQuery({
    queryKey: ["news", "list", params],
    queryFn: () => newsApi.list(params).then((r) => r.data),
    staleTime: 5 * 60 * 1000,
  });
}

export function useStockNews(code: string, page = 1, pageSize = 20) {
  return useQuery({
    queryKey: ["news", "stock", code, page, pageSize],
    queryFn: () =>
      newsApi.listForStock(code, { page, page_size: pageSize }).then((r) => r.data),
    enabled: !!code,
    staleTime: 5 * 60 * 1000,
  });
}
