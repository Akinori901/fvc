"""AI機能Djangoリポジトリ実装。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from apps.ai.domain.entities import AiAnalysisLogEntity, AiConfigEntity, AiDecisionEntity
from apps.ai.domain.repositories import (
    AiAnalysisLogRepository,
    AiConfigRepository,
    AiDecisionRepository,
)
from apps.ai.infrastructure.models import AiAnalysisLog, AiDecision, UserAiConfig

if TYPE_CHECKING:
    from datetime import datetime


class DjangoAiConfigRepository(AiConfigRepository):
    """ユーザーAI設定リポジトリ Django実装。"""

    def find_by_user_id(self, user_id: int) -> AiConfigEntity | None:
        try:
            obj = UserAiConfig.objects.get(user_id=user_id)
        except UserAiConfig.DoesNotExist:
            return None
        return self._to_entity(obj)

    def save(self, entity: AiConfigEntity) -> AiConfigEntity:
        obj, _ = UserAiConfig.objects.update_or_create(
            user_id=entity.user_id,
            defaults={
                "provider": entity.provider,
                "api_key": entity.api_key,
                "model": entity.model,
                "is_enabled": entity.is_enabled,
            },
        )
        return self._to_entity(obj)

    def _to_entity(self, obj: UserAiConfig) -> AiConfigEntity:
        return AiConfigEntity(
            id=obj.pk,
            user_id=obj.user_id,
            provider=obj.provider,
            api_key=obj.api_key,
            model=obj.model,
            is_enabled=obj.is_enabled,
            updated_at=obj.updated_at,
        )


class DjangoAiAnalysisLogRepository(AiAnalysisLogRepository):
    """AI分析ログリポジトリ Django実装。"""

    def save(self, entity: AiAnalysisLogEntity) -> AiAnalysisLogEntity:
        obj = AiAnalysisLog.objects.create(
            user_id=entity.user_id,
            stock_id=entity.stock_id,
            question_type=entity.question_type,
            custom_question=entity.custom_question,
            expert_role=entity.expert_role,
            model_used=entity.model_used,
            prompt_tokens=entity.prompt_tokens,
            completion_tokens=entity.completion_tokens,
            is_success=entity.is_success,
            error_message=entity.error_message,
        )
        return AiAnalysisLogEntity(
            id=obj.pk,
            user_id=obj.user_id,
            stock_id=obj.stock_id,
            question_type=obj.question_type,
            custom_question=obj.custom_question,
            expert_role=obj.expert_role,
            model_used=obj.model_used,
            prompt_tokens=obj.prompt_tokens,
            completion_tokens=obj.completion_tokens,
            is_success=obj.is_success,
            error_message=obj.error_message,
            created_at=obj.created_at,
        )

    def count_since(self, user_id: int, since: datetime) -> int:
        return AiAnalysisLog.objects.filter(
            user_id=user_id,
            created_at__gte=since,
        ).count()


class DjangoAiDecisionRepository(AiDecisionRepository):
    """AI 判断履歴リポジトリ Django 実装。"""

    def save(self, entity: AiDecisionEntity) -> AiDecisionEntity:
        obj = AiDecision.objects.create(
            user_id=entity.user_id,
            stock_id=entity.stock_id,
            decision_type=entity.decision_type,
            rationale=entity.rationale,
            confidence=entity.confidence,
            snapshot_indicators=entity.snapshot_indicators,
            ai_model=entity.ai_model,
        )
        return self._to_entity(obj)

    def find_by_user(self, user_id: int, limit: int = 50) -> list[AiDecisionEntity]:
        return [self._to_entity(obj) for obj in AiDecision.objects.filter(user_id=user_id)[:limit]]

    @staticmethod
    def _to_entity(obj: AiDecision) -> AiDecisionEntity:
        return AiDecisionEntity(
            id=obj.pk,
            user_id=obj.user_id,
            stock_id=obj.stock_id,
            decision_type=obj.decision_type,
            rationale=obj.rationale,
            confidence=obj.confidence,
            snapshot_indicators=obj.snapshot_indicators or {},
            ai_model=obj.ai_model,
            decided_at=obj.decided_at,
        )
