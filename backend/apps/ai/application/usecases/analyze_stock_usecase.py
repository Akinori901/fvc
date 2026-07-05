"""個別株AI分析ユースケース。

フロー:
1. AI設定取得・有効チェック
2. レート制限チェック（1分間にN回まで）
3. 銘柄データ収集（Stock + Financial + 最新Valuation）
4. プロンプト構築
5. Gemini API呼び出し
6. 実行ログ保存
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from apps.ai.application.dto import AnalysisRequestDTO, AnalysisResultDTO, StockContextDTO
from apps.ai.application.services.gemini_client_service import GeminiClientService
from apps.ai.domain.entities import AiAnalysisLogEntity
from apps.ai.domain.exceptions import AiConfigNotFoundError, AiRateLimitExceededError

if TYPE_CHECKING:
    from decimal import Decimal

    from apps.ai.application.services.prompt_builder_service import PromptBuilderService
    from apps.ai.domain.repositories import AiAnalysisLogRepository, AiConfigRepository
    from apps.stocks.domain.repositories import FinancialRepository, StockRepository
    from apps.valuations.domain.repositories import ValuationRepository

logger = logging.getLogger(__name__)

_RATE_LIMIT_PER_MINUTE = 5


class AnalyzeStockUseCase:
    def __init__(
        self,
        ai_config_repo: AiConfigRepository,
        ai_log_repo: AiAnalysisLogRepository,
        stock_repo: StockRepository,
        financial_repo: FinancialRepository,
        valuation_repo: ValuationRepository,
        prompt_builder: PromptBuilderService,
    ) -> None:
        self._ai_config_repo = ai_config_repo
        self._ai_log_repo = ai_log_repo
        self._stock_repo = stock_repo
        self._financial_repo = financial_repo
        self._valuation_repo = valuation_repo
        self._prompt_builder = prompt_builder

    def execute(self, request: AnalysisRequestDTO) -> AnalysisResultDTO:
        # 1. AI設定取得・有効チェック
        config = self._ai_config_repo.find_by_user_id(request.user_id)
        if config is None or not config.is_enabled or not config.api_key:
            raise AiConfigNotFoundError("AI設定が有効ではありません。設定ページでGemini APIキーを登録してください。")

        # 2. レート制限チェック
        one_minute_ago = datetime.now(tz=UTC) - timedelta(minutes=1)
        recent_count = self._ai_log_repo.count_since(request.user_id, one_minute_ago)
        if recent_count >= _RATE_LIMIT_PER_MINUTE:
            raise AiRateLimitExceededError(
                max_per_minute=_RATE_LIMIT_PER_MINUTE,
                current_count=recent_count,
            )

        # 3. 銘柄データ収集
        stock = self._stock_repo.find_by_code(request.stock_code)
        if stock is None or stock.id is None:
            raise ValueError(f"銘柄が見つかりません: {request.stock_code}")

        financial = self._financial_repo.find_latest_by_stock_id(stock.id)
        valuations = self._valuation_repo.find_by_stock_id(stock.id, user_id=request.user_id)
        latest_valuation = valuations[-1] if valuations else None

        # effective_bps: adj_factor適用済みBPS
        effective_bps: Decimal | None = None
        if financial and financial.bps:
            effective_bps = financial.bps * financial.adj_factor

        pbr: Decimal | None = None
        if stock.latest_price and effective_bps and effective_bps > 0:
            pbr = stock.latest_price / effective_bps

        context = StockContextDTO(
            code=stock.code,
            name=stock.name,
            sector=stock.sector,
            latest_price=stock.latest_price,
            bps=effective_bps,
            eps=financial.eps if financial else None,
            roe=financial.roe if financial else None,
            revenue=financial.revenue if financial else None,
            operating_income=financial.operating_income if financial else None,
            pbr=pbr,
            fair_value=latest_valuation.fair_value if latest_valuation else None,
            discount_rate=latest_valuation.discount_rate if latest_valuation else None,
        )

        # 4. プロンプト構築・API呼び出し
        system_prompt = self._prompt_builder.build_system_prompt(request.expert_role)
        user_prompt = self._prompt_builder.build_user_prompt(context, request.question_type, request.custom_question)

        gemini_client = GeminiClientService(api_key=config.api_key, model=config.model)
        generated_at = datetime.now(tz=UTC)

        try:
            response = gemini_client.chat(system_prompt, user_prompt)
        except Exception as exc:
            # 失敗ログを保存して再raise
            self._ai_log_repo.save(
                AiAnalysisLogEntity(
                    user_id=request.user_id,
                    stock_id=stock.id,
                    question_type=request.question_type,
                    custom_question=request.custom_question,
                    expert_role=request.expert_role,
                    model_used=config.model,
                    is_success=False,
                    error_message=str(exc),
                )
            )
            raise

        # 5. 成功ログ保存
        self._ai_log_repo.save(
            AiAnalysisLogEntity(
                user_id=request.user_id,
                stock_id=stock.id,
                question_type=request.question_type,
                custom_question=request.custom_question,
                expert_role=request.expert_role,
                model_used=response.model,
                prompt_tokens=response.prompt_tokens,
                completion_tokens=response.completion_tokens,
                is_success=True,
            )
        )

        logger.info(
            "AI分析完了: user=%d stock=%s model=%s tokens=%d+%d",
            request.user_id,
            request.stock_code,
            response.model,
            response.prompt_tokens,
            response.completion_tokens,
        )

        return AnalysisResultDTO(
            analysis=response.content,
            model=response.model,
            generated_at=generated_at,
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
        )
