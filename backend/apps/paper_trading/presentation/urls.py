"""仮想売買URLルーティング。"""

from django.urls import path

from .views.paper_position_views import PaperPositionDetailView, PaperPositionListView
from .views.paper_trade_view import PaperTradeView
from .views.paper_trading_reset_view import PaperTradingResetView

urlpatterns = [
    path("paper-trading/trades/", PaperTradeView.as_view(), name="paper-trades"),
    path("paper-trading/positions/", PaperPositionListView.as_view(), name="paper-positions"),
    path("paper-trading/positions/<str:code>/", PaperPositionDetailView.as_view(), name="paper-position-detail"),
    path("paper-trading/reset/", PaperTradingResetView.as_view(), name="paper-trading-reset"),
]
