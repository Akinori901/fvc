import { useState } from "react";
import { Box, Typography } from "@mui/material";
import { useNewsList } from "@/hooks/useNews";
import type { NewsListParams } from "@/types/news";
import NewsFilterBar from "@/components/news/NewsFilterBar";
import NewsList from "@/components/news/NewsList";

const PAGE_SIZE = 20;

export default function NewsPage() {
  const [filters, setFilters] = useState<NewsListParams>({ page: 1, page_size: PAGE_SIZE });
  const { data, isLoading, error } = useNewsList(filters);

  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        ニュース
      </Typography>
      <NewsFilterBar
        filters={filters}
        onChange={setFilters}
        onReset={() => setFilters({ page: 1, page_size: PAGE_SIZE })}
      />
      <NewsList
        articles={data?.results ?? []}
        isLoading={isLoading}
        error={error}
        pagination={
          data
            ? {
                page: filters.page ?? 1,
                pageSize: PAGE_SIZE,
                total: data.count,
                onPageChange: (p) => setFilters({ ...filters, page: p }),
              }
            : undefined
        }
      />
    </Box>
  );
}
