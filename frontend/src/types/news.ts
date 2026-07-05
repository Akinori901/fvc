export type NewsCategory = "stock" | "market" | "fx" | "earnings";

export type NewsSource = "google_news_rss" | "yfinance" | "jquants";

export interface NewsArticle {
  id: number;
  source: NewsSource;
  category: NewsCategory;
  title: string;
  url: string;
  summary: string;
  publisher: string | null;
  language: string;
  published_at: string;
  fetched_at: string;
  ai_analyzed_at: string | null;
  importance_score: string | null;
}

export interface NewsListResponse {
  count: number;
  page: number;
  page_size: number;
  results: NewsArticle[];
}

export interface NewsListParams {
  category?: NewsCategory;
  date_from?: string;
  date_to?: string;
  keyword?: string;
  page?: number;
  page_size?: number;
}
