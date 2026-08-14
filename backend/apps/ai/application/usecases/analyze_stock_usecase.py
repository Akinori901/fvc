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
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from apps.ai.application.dto import AnalysisRequestDTO, AnalysisResultDTO, StockContextDTO
from apps.ai.application.services.gemini_client_service import GeminiClientService
from apps.ai.domain.entities import AiAnalysisLogEntity
from apps.ai.domain.exceptions import AiConfigNotFoundError, AiRateLimitExceededError

if TYPE_CHECKING:
    from apps.ai.application.services.prompt_builder_service import PromptBuilderService
    from apps.ai.domain.repositories import AiAnalysisLogRepository, AiConfigRepository
    from apps.fx.domain.repositories import FxRateRepository, InterestRateRepository
    from apps.stocks.application.usecases.screening_usecase import ScreeningUseCase
    from apps.stocks.domain.repositories import FinancialRepository, PriceRepository, StockRepository

logger = logging.getLogger(__name__)

_RATE_LIMIT_PER_MINUTE = 5

# Gordon Growth Model の前提成長率（年率2%）— 画面のスクリーニング指標と揃える
_DEFAULT_GROWTH_RATE = Decimal("0.02")

# テクニカル指標の計算に用いる日足の取得件数（銘柄詳細ページと同じ 300 日）
_TECH_FETCH_LIMIT = 300


def _pct_from_ratio(value: Decimal | None) -> Decimal | None:
    """比率（0.42）を % 値（42.0）に変換。None はそのまま。"""
    if value is None:
        return None
    return (value * Decimal("100")).quantize(Decimal("0.01"))


class AnalyzeStockUseCase:
    def __init__(
        self,
        ai_config_repo: AiConfigRepository,
        ai_log_repo: AiAnalysisLogRepository,
        stock_repo: StockRepository,
        financial_repo: FinancialRepository,
        price_repo: PriceRepository,
        screening_usecase: ScreeningUseCase,
        prompt_builder: PromptBuilderService,
        fx_repo: FxRateRepository | None = None,
        interest_repo: InterestRateRepository | None = None,
    ) -> None:
        self._ai_config_repo = ai_config_repo
        self._ai_log_repo = ai_log_repo
        self._stock_repo = stock_repo
        self._financial_repo = financial_repo
        self._price_repo = price_repo
        self._screening_usecase = screening_usecase
        self._prompt_builder = prompt_builder
        self._fx_repo = fx_repo
        self._interest_repo = interest_repo

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

        # 画面の「スクリーニング指標」と同じ計算結果を単一銘柄モードで取得。
        # 成長性・テクニカル・需給・配当・FCF・オーナー経営を一括で得る。
        screening_results = self._screening_usecase.execute(
            growth_rate=_DEFAULT_GROWTH_RATE,
            code=request.stock_code,
            include_inactive=True,
        )
        r = screening_results[0] if screening_results else None

        # revenue / operating_income は ScreeningResult に無いため financial から補う
        financial = self._financial_repo.find_latest_by_stock_id(stock.id)

        # テクニカル詳細（移動平均/RSI/MACD/BB/ATR）+ ヒストリカルボラ
        tech = self._collect_technicals(stock.id)
        # 財務健全性（自己資本比率/営業利益率/CF/時価総額/PER）
        fin = self._collect_financial_health(stock, financial)
        # 市場環境（為替・金利）
        macro = self._collect_macro()

        context = StockContextDTO(
            code=stock.code,
            name=stock.name,
            sector=stock.sector,
            latest_price=r.latest_price if r else stock.latest_price,
            bps=r.bps if r else None,
            eps=r.eps if r else None,
            roe=r.roe if r else None,
            revenue=financial.revenue if financial else None,
            operating_income=financial.operating_income if financial else None,
            pbr=r.current_pbr if r else None,
            fair_value=r.fair_value if r else None,
            discount_rate=r.discount_rate if r else None,
            # 成長性
            implied_growth_rate=r.implied_growth_rate if r else None,
            company_forecast_growth_rate=r.company_forecast_growth_rate if r else None,
            growth_rate_label=r.growth_rate_label if r else None,
            eps_growth_yoy=r.eps_growth_yoy if r else None,
            eps_cagr_3y=r.eps_cagr_3y if r else None,
            roe_trend=r.roe_trend if r else None,
            revenue_growth_yoy=r.revenue_growth_yoy if r else None,
            # テクニカル・需給
            sl_ratio=r.sl_ratio if r else None,
            long_balance_trend=r.long_balance_trend if r else None,
            momentum_signal=r.momentum_signal if r else None,
            price_position_52w=r.price_position_52w if r else None,
            distance_from_52w_high=r.distance_from_52w_high if r else None,
            liquidity_level=r.liquidity_level if r else None,
            # 配当
            dividend_yield=r.dividend_yield if r else None,
            payout_ratio=r.payout_ratio if r else None,
            consecutive_dividend_years=r.consecutive_dividend_years if r else None,
            progressive_dividend_years=r.progressive_dividend_years if r else None,
            # FCF
            fcf_yield=r.fcf_yield if r else None,
            fcf_margin=r.fcf_margin if r else None,
            # オーナー経営
            is_owner_managed=r.is_owner_managed if r else False,
            owner_ratio=r.owner_ratio if r else None,
            # テクニカル詳細・ボラ
            ma_25_deviation_pct=tech.get("ma_25_deviation_pct"),
            ma_75_deviation_pct=tech.get("ma_75_deviation_pct"),
            ma_200_deviation_pct=tech.get("ma_200_deviation_pct"),
            rsi_14=tech.get("rsi_14"),
            rsi_signal=tech.get("rsi_signal"),
            macd_hist=tech.get("macd_hist"),
            macd_cross=tech.get("macd_cross"),
            bb_position=tech.get("bb_position"),
            bb_signal=tech.get("bb_signal"),
            atr_pct=tech.get("atr_pct"),
            volatility_20d=tech.get("volatility_20d"),
            # 財務健全性
            equity_ratio=fin.get("equity_ratio"),
            operating_margin=fin.get("operating_margin"),
            operating_cash_flow=fin.get("operating_cash_flow"),
            free_cash_flow=fin.get("free_cash_flow"),
            market_cap=fin.get("market_cap"),
            per=fin.get("per"),
            # 市場環境
            usdjpy=macro.get("usdjpy"),
            jp_10y=macro.get("jp_10y"),
            us_10y=macro.get("us_10y"),
            market_type=stock.market_type or "JP",
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

    def _collect_technicals(self, stock_id: int) -> dict[str, Any]:
        """日足終値から移動平均/RSI/MACD/BB/ATR とヒストリカルボラを算出。

        データ不足・計算失敗時は空 dict を返し、AI分析全体は継続する。
        """
        from apps.stocks.domain.stock_technical_indicators import build_indicators
        from apps.stocks.domain.technical_metrics import compute_volatility_20d

        try:
            prices_desc = self._price_repo.find_by_stock_id(stock_id, limit=_TECH_FETCH_LIMIT)
        except Exception:  # noqa: BLE001 - テクニカルは補助情報。取得失敗でも分析は続行
            logger.warning("テクニカル価格取得に失敗: stock_id=%d", stock_id, exc_info=True)
            return {}
        if not prices_desc:
            return {}

        volatility = compute_volatility_20d(prices_desc)
        latest = build_indicators(prices_desc).latest
        if latest is None:
            # 指標計算に足りる日数が無い場合でもボラだけは返せることがある
            return {"volatility_20d": volatility}
        return {
            "ma_25_deviation_pct": latest.ma_25_deviation_pct,
            "ma_75_deviation_pct": latest.ma_75_deviation_pct,
            "ma_200_deviation_pct": latest.ma_200_deviation_pct,
            "rsi_14": latest.rsi_14,
            "rsi_signal": latest.rsi_signal,
            "macd_hist": latest.macd_hist,
            "macd_cross": latest.macd_cross,
            "bb_position": latest.bb_position,
            "bb_signal": latest.bb_signal,
            "atr_pct": latest.atr_pct,
            "volatility_20d": volatility,
        }

    def _collect_financial_health(self, stock: object, financial: object | None) -> dict[str, Any]:
        """自己資本比率/営業利益率/CF/時価総額/PER を算出。"""
        if financial is None:
            return {}
        result: dict[str, Any] = {
            # FinancialEntity.roe には J-Quants の EqAR（自己資本比率）が入る運用
            "equity_ratio": _pct_from_ratio(getattr(financial, "roe", None)),
            "operating_cash_flow": getattr(financial, "operating_cash_flow", None),
            "free_cash_flow": getattr(financial, "free_cash_flow", None),
        }

        revenue = getattr(financial, "revenue", None)
        op_income = getattr(financial, "operating_income", None)
        if revenue and op_income is not None and revenue != 0:
            result["operating_margin"] = (Decimal(op_income) / Decimal(revenue) * Decimal("100")).quantize(
                Decimal("0.01")
            )

        latest_price = getattr(stock, "latest_price", None)
        total_shares = getattr(financial, "total_shares", None)
        if latest_price and total_shares:
            # 時価総額（百万円）: 株価 × 発行済株式数 / 1,000,000
            result["market_cap"] = int(latest_price * Decimal(total_shares) / Decimal("1000000"))

        eps = getattr(financial, "eps", None)
        if latest_price and eps and eps != 0:
            result["per"] = (latest_price / eps).quantize(Decimal("0.01"))

        return result

    def _collect_macro(self) -> dict[str, Any]:
        """市場環境（為替・日米10年金利）を取得。repo 未注入時は空。"""
        result: dict[str, Any] = {}
        if self._fx_repo is not None:
            try:
                fx = self._fx_repo.find_latest("USDJPY")
                if fx is not None:
                    result["usdjpy"] = fx.close_rate
            except Exception:  # noqa: BLE001 - マクロは補助情報
                logger.warning("USDJPY取得に失敗", exc_info=True)
        if self._interest_repo is not None:
            try:
                jp = self._interest_repo.find_latest("JP", "10Y")
                us = self._interest_repo.find_latest("US", "10Y")
                if jp is not None:
                    result["jp_10y"] = jp.rate
                if us is not None:
                    result["us_10y"] = us.rate
            except Exception:  # noqa: BLE001 - マクロは補助情報
                logger.warning("金利取得に失敗", exc_info=True)
        return result
