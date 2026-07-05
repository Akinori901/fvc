# Django互換 re-export（実体は infrastructure/models/ にある）
from apps.goals.infrastructure.models import FinancialGoal, GoalMember

__all__ = ["FinancialGoal", "GoalMember"]
