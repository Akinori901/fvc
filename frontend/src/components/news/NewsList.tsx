import { Alert, Box, CircularProgress, Pagination, Stack, Typography } from "@mui/material";
import type { NewsArticle } from "@/types/news";
import NewsCard from "./NewsCard";

interface NewsListProps {
  articles: NewsArticle[];
  isLoading?: boolean;
  error?: unknown;
  emptyMessage?: string;
  pagination?: {
    page: number;
    pageSize: number;
    total: number;
    onPageChange: (page: number) => void;
  };
}

export default function NewsList({
  articles,
  isLoading,
  error,
  emptyMessage = "該当するニュースはありません。",
  pagination,
}: NewsListProps) {
  if (isLoading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", mt: 4 }}>
        <CircularProgress />
      </Box>
    );
  }
  if (error) {
    const msg = error instanceof Error ? error.message : "ニュースの取得に失敗しました";
    return <Alert severity="error">{msg}</Alert>;
  }
  if (articles.length === 0) {
    return (
      <Alert severity="info">
        <Typography variant="body2">{emptyMessage}</Typography>
      </Alert>
    );
  }

  const totalPages = pagination
    ? Math.max(1, Math.ceil(pagination.total / pagination.pageSize))
    : 0;

  return (
    <Stack spacing={0.5}>
      {articles.map((a) => (
        <NewsCard key={a.id} article={a} />
      ))}
      {pagination && totalPages > 1 && (
        <Box sx={{ display: "flex", justifyContent: "center", mt: 2 }}>
          <Pagination
            count={totalPages}
            page={pagination.page}
            onChange={(_, p) => pagination.onPageChange(p)}
            color="primary"
          />
        </Box>
      )}
    </Stack>
  );
}
