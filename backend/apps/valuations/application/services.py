from decimal import Decimal
from typing import Any

from apps.core.exceptions import EntityNotFoundError, ValidationError
from apps.stocks.domain.repositories import FinancialRepository, PriceRepository, StockRepository

from ..domain.entities import MARKET_COST_OF_CAPITAL, FairValueCalculation, ValuationResult, growth_rate_label
from ..domain.repositories import ValuationRepository
from .dto import CalculateFairValueDTO, ReverseCalculateDTO


class ValuationService:
    """適正価格算出サービス"""

    def __init__(
        self,
        stock_repo: StockRepository,
        financial_repo: FinancialRepository,
        price_repo: PriceRepository,
        valuation_repo: ValuationRepository,
    ) -> None:
        self._stock_repo = stock_repo
        self._financial_repo = financial_repo
        self._price_repo = price_repo
        self._valuation_repo = valuation_repo

    def calculate_fair_value(self, dto: CalculateFairValueDTO, user_id: int) -> ValuationResult:
        """適正株価を算出し、結果を保存して返却（ゴードン成長モデル）"""
        stock = self._stock_repo.find_by_code(dto.stock_code)
        if stock is None:
            raise EntityNotFoundError(f"銘柄が見つかりません: {dto.stock_code}")
        assert stock.id is not None

        # 最新の財務データ（BPS・ROE）を取得
        financial = self._financial_repo.find_latest_by_stock_id(stock.id)
        if financial is None:
            raise ValidationError(f"財務データがありません。データを同期してください: {dto.stock_code}")

        roe = financial.computed_roe
        if roe is None:
            raise ValidationError(f"ROEが取得できません。財務データを同期してください: {dto.stock_code}")

        # 市場種別から資本コストを決定
        market_type = stock.market_type or "JP"
        cost_of_capital = MARKET_COST_OF_CAPITAL.get(market_type, MARKET_COST_OF_CAPITAL["JP"])

        # 成長率の検証（g < r）
        if dto.growth_rate >= cost_of_capital:
            raise ValidationError(
                f"成長率は資本コスト（{market_type}: {int(cost_of_capital * 100)}%）未満である必要があります。"
                f"入力値: {float(dto.growth_rate * 100):.1f}%"
            )

        # 現在株価の決定
        current_price = dto.current_price
        if current_price is None:
            latest_price = self._price_repo.find_latest_by_stock_id(stock.id)
            if latest_price is None:
                raise ValidationError(f"株価データがありません: {dto.stock_code}")
            current_price = latest_price.close_price

        # 適正価格を計算（ゴードン成長モデル）
        calculation = FairValueCalculation(
            growth_rate=dto.growth_rate,
            bps=financial.bps,
            current_price=current_price,
            roe=roe,
            cost_of_capital=cost_of_capital,
        )

        # 結果エンティティを作成して保存
        result = ValuationResult(
            stock_id=stock.id,
            user_id=user_id,
            growth_rate=dto.growth_rate,
            fair_pbr=calculation.fair_pbr,
            fair_value=calculation.fair_value,
            current_price=current_price,
            discount_rate=calculation.discount_rate,
            is_undervalued=calculation.is_undervalued,
            roe=roe,
            cost_of_capital=cost_of_capital,
            bps=financial.bps,
            current_pbr=calculation.current_pbr,
            implied_growth_rate=calculation.implied_growth_rate,
        )
        return self._valuation_repo.save(result)

    def reverse_calculate(self, dto: ReverseCalculateDTO) -> dict[str, Any]:
        """市場織り込み成長率を逆算する（DB保存なし）

        現在のPBRから、市場が期待している永続成長率を逆算する。
        g = (PBR × r - ROE) / (PBR - 1)
        """
        stock = self._stock_repo.find_by_code(dto.stock_code)
        if stock is None:
            raise EntityNotFoundError(f"銘柄が見つかりません: {dto.stock_code}")
        assert stock.id is not None

        # 最新財務データを取得
        financial = self._financial_repo.find_latest_by_stock_id(stock.id)
        if financial is None:
            raise ValidationError(f"財務データがありません。データを同期してください: {dto.stock_code}")

        roe = financial.computed_roe
        if roe is None:
            raise ValidationError(f"ROEが取得できません。財務データを同期してください: {dto.stock_code}")

        # 現在株価の決定
        current_price = dto.current_price
        if current_price is None:
            latest_price = self._price_repo.find_latest_by_stock_id(stock.id)
            if latest_price is None:
                raise ValidationError(f"株価データがありません: {dto.stock_code}")
            current_price = latest_price.close_price

        # 市場種別から資本コストを決定
        market_type = stock.market_type or "JP"
        cost_of_capital = MARKET_COST_OF_CAPITAL.get(market_type, MARKET_COST_OF_CAPITAL["JP"])

        bps = financial.bps
        current_pbr = (current_price / bps).quantize(Decimal("0.0001"))

        # PBR = 1.0 の場合は逆算不可
        if current_pbr == Decimal("1"):
            raise ValidationError("PBR=1.0 の場合、逆算は計算できません（ゼロ除算）。")

        implied_growth_rate = ((current_pbr * cost_of_capital - roe) / (current_pbr - Decimal("1"))).quantize(
            Decimal("0.0001")
        )

        return {
            "stock_code": stock.code,
            "stock_name": stock.name,
            "current_price": str(current_price),
            "bps": str(bps),
            "roe": str(roe),
            "cost_of_capital": str(cost_of_capital),
            "current_pbr": str(current_pbr),
            "implied_growth_rate": str(implied_growth_rate),
            "growth_rate_label": growth_rate_label(implied_growth_rate),
        }

    def list_valuations(self, user_id: int, limit: int = 50) -> list[ValuationResult]:
        return self._valuation_repo.list_all(user_id=user_id, limit=limit)

    def get_valuation(self, valuation_id: int, user_id: int) -> ValuationResult:
        result = self._valuation_repo.find_by_id(valuation_id, user_id=user_id)
        if result is None:
            raise EntityNotFoundError(f"算出結果が見つかりません: {valuation_id}")
        return result

    def list_by_stock(self, stock_code: str, user_id: int) -> list[ValuationResult]:
        stock = self._stock_repo.find_by_code(stock_code)
        if stock is None:
            raise EntityNotFoundError(f"銘柄が見つかりません: {stock_code}")
        assert stock.id is not None
        return self._valuation_repo.find_by_stock_id(stock.id, user_id=user_id)
