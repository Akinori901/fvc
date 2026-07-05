# Django互換 re-export（実体は infrastructure/models/ にある）
from apps.paper_trading.infrastructure.models import PaperPosition, PaperTrade

__all__ = ["PaperTrade", "PaperPosition"]
