import { useState } from "react";
import { useStockNews } from "@/hooks/useNews";
import NewsList from "./NewsList";

interface StockNewsTabProps {
  stockCode: string;
}

export default function StockNewsTab({ stockCode }: StockNewsTabProps) {
  const [page, setPage] = useState(1);
  const pageSize = 20;
  const { data, isLoading, error } = useStockNews(stockCode, page, pageSize);

  return (
    <NewsList
      articles={data?.results ?? []}
      isLoading={isLoading}
      error={error}
      emptyMessage="この銘柄に紐付くニュースはまだ取り込まれていません。バックエンドで `sync_news --category stock --code <code>` を実行してください。"
      pagination={
        data
          ? {
              page,
              pageSize,
              total: data.count,
              onPageChange: setPage,
            }
          : undefined
      }
    />
  );
}
