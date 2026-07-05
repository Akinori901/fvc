import { Card, CardContent, Chip, Link, Stack, Typography } from "@mui/material";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import type { NewsArticle, NewsCategory } from "@/types/news";

const CATEGORY_LABEL: Record<NewsCategory, string> = {
  stock: "個別銘柄",
  market: "市場",
  fx: "FX",
  earnings: "決算",
};

const CATEGORY_COLOR: Record<NewsCategory, "primary" | "success" | "warning" | "info"> = {
  stock: "primary",
  market: "info",
  fx: "success",
  earnings: "warning",
};

interface NewsCardProps {
  article: NewsArticle;
}

export default function NewsCard({ article }: NewsCardProps) {
  const publishedDate = new Date(article.published_at);
  const dateStr = publishedDate.toLocaleString("ja-JP", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
  const score = article.importance_score
    ? Number(article.importance_score).toFixed(0)
    : null;

  return (
    <Card variant="outlined" sx={{ mb: 1.5 }}>
      <CardContent sx={{ "&:last-child": { pb: 2 } }}>
        <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
          <Chip
            label={CATEGORY_LABEL[article.category]}
            color={CATEGORY_COLOR[article.category]}
            size="small"
            variant="outlined"
          />
          {article.publisher && (
            <Typography variant="caption" color="text.secondary">
              {article.publisher}
            </Typography>
          )}
          <Typography variant="caption" color="text.secondary" sx={{ ml: "auto" }}>
            {dateStr}
          </Typography>
          {score && (
            <Chip label={`重要度 ${score}`} size="small" sx={{ ml: 0.5 }} />
          )}
        </Stack>
        <Link
          href={article.url}
          target="_blank"
          rel="noopener noreferrer"
          underline="hover"
          color="inherit"
        >
          <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
            {article.title}
            <OpenInNewIcon fontSize="inherit" sx={{ ml: 0.5, verticalAlign: "middle" }} />
          </Typography>
        </Link>
        {article.summary && (
          <Typography
            variant="body2"
            color="text.secondary"
            sx={{
              display: "-webkit-box",
              WebkitLineClamp: 3,
              WebkitBoxOrient: "vertical",
              overflow: "hidden",
            }}
          >
            {article.summary}
          </Typography>
        )}
      </CardContent>
    </Card>
  );
}
