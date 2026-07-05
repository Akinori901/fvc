"""ニュース機能URLルーティング。"""

from django.urls import path

from .views.news_list_view import NewsListView
from .views.stock_news_view import StockNewsView

urlpatterns = [
    path("news/", NewsListView.as_view(), name="news-list"),
    path("news/stocks/<str:code>/", StockNewsView.as_view(), name="news-stock"),
]
