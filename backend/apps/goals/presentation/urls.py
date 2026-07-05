"""目標管理URLルーティング。"""

from django.urls import path

from apps.goals.presentation.views.goal_views import GoalDetailView, GoalListView
from apps.goals.presentation.views.progress_views import GoalProgressView
from apps.goals.presentation.views.reorder_view import GoalReorderView

urlpatterns = [
    path("goals/", GoalListView.as_view(), name="goal-list"),
    path("goals/reorder/", GoalReorderView.as_view(), name="goal-reorder"),
    path("goals/<int:pk>/", GoalDetailView.as_view(), name="goal-detail"),
    path("goals/<int:pk>/progress/", GoalProgressView.as_view(), name="goal-progress"),
]
