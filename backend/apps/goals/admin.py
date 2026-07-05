from django.contrib import admin

from .models import FinancialGoal, GoalMember


@admin.register(FinancialGoal)
class FinancialGoalAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("id", "user", "name", "target_value_jpy", "target_date", "scope_type", "is_active")
    list_filter = ("scope_type", "is_active")
    search_fields = ("name", "user__username")


@admin.register(GoalMember)
class GoalMemberAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("goal", "family_member")
