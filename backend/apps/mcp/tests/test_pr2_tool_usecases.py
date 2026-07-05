"""PR2 で追加した 4 ツール UseCase の単体テスト（依存はモック）。"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from apps.mcp.application.usecases.tools.get_screening_candidates_usecase import (
    GetScreeningCandidatesToolUseCase,
)
from apps.mcp.application.usecases.tools.get_sell_candidates_usecase import (
    GetSellCandidatesToolUseCase,
)
from apps.mcp.application.usecases.tools.get_stock_opportunity_tags_usecase import (
    GetStockOpportunityTagsToolUseCase,
)
from apps.mcp.application.usecases.tools.get_stock_risk_tags_usecase import (
    GetStockRiskTagsToolUseCase,
)


def _screening(
    *,
    code: str = "7203",
    name: str = "トヨタ自動車",
    sector: str = "輸送用機器",
    fair_value: Decimal | None = Decimal("3000"),
    evaluation_zone: str | None = "cheap",
    momentum_signal: str | None = "neutral",
    roe_trend: str | None = "stable",
    current_pbr: Decimal | None = Decimal("1.2"),
    fair_pbr: Decimal | None = Decimal("1.5"),
    discount_rate: Decimal | None = Decimal("0.10"),
    latest_price: Decimal | None = Decimal("2700"),
    latest_price_date: str | None = "2026-05-15",
    roe: Decimal | None = Decimal("0.14"),
    dividend_yield: Decimal | None = Decimal("2.5"),
    liquidity_level: str | None = "high",
    long_balance: int | None = None,
    short_balance: int | None = None,
    avg_turnover_20d: Decimal | None = None,
    progressive_dividend_years: int | None = None,
    price_position_52w: Decimal | None = None,
    not_calculable_reason: str | None = None,
) -> MagicMock:
    r = MagicMock()
    r.code = code
    r.name = name
    r.sector = sector
    r.fair_value = fair_value
    r.evaluation_zone = evaluation_zone
    r.momentum_signal = momentum_signal
    r.roe_trend = roe_trend
    r.current_pbr = current_pbr
    r.fair_pbr = fair_pbr
    r.discount_rate = discount_rate
    r.latest_price = latest_price
    r.latest_price_date = latest_price_date
    r.roe = roe
    r.dividend_yield = dividend_yield
    r.liquidity_level = liquidity_level
    r.long_balance = long_balance
    r.short_balance = short_balance
    r.avg_turnover_20d = avg_turnover_20d
    r.progressive_dividend_years = progressive_dividend_years
    r.price_position_52w = price_position_52w
    r.not_calculable_reason = not_calculable_reason
    return r


# ============================================================
# GetScreeningCandidatesToolUseCase
# ============================================================


class TestGetScreeningCandidatesToolUseCase:
    def test_returns_filtered_candidates_with_defaults(self) -> None:
        screening = MagicMock()
        screening.execute.return_value = [
            _screening(code="7203", evaluation_zone="cheap"),
            _screening(code="6758", evaluation_zone="very_cheap"),
            _screening(code="9999", evaluation_zone="very_expensive"),  # 除外
        ]
        usecase = GetScreeningCandidatesToolUseCase(screening_usecase=screening)
        result = usecase.execute()
        assert result["count"] == 2
        codes = [c["code"] for c in result["candidates"]]
        assert "9999" not in codes

    def test_applies_max_pbr_ratio_filter(self) -> None:
        screening = MagicMock()
        screening.execute.return_value = [
            _screening(code="A", current_pbr=Decimal("1.0"), fair_pbr=Decimal("2.0")),  # OK
            _screening(code="B", current_pbr=Decimal("3.0"), fair_pbr=Decimal("2.0")),  # NG
        ]
        usecase = GetScreeningCandidatesToolUseCase(screening_usecase=screening)
        result = usecase.execute(max_pbr_ratio=Decimal("1.0"))
        codes = [c["code"] for c in result["candidates"]]
        assert codes == ["A"]

    def test_exclude_codes_filter(self) -> None:
        screening = MagicMock()
        screening.execute.return_value = [
            _screening(code="A"),
            _screening(code="B"),
        ]
        usecase = GetScreeningCandidatesToolUseCase(screening_usecase=screening)
        result = usecase.execute(exclude_codes=["A"])
        codes = [c["code"] for c in result["candidates"]]
        assert codes == ["B"]

    def test_limit_truncates_results(self) -> None:
        screening = MagicMock()
        screening.execute.return_value = [_screening(code=f"{i}") for i in range(50)]
        usecase = GetScreeningCandidatesToolUseCase(screening_usecase=screening)
        result = usecase.execute(limit=5)
        assert result["count"] == 5


# ============================================================
# GetSellCandidatesToolUseCase
# ============================================================


def _holding(*, ticker_code: str = "5892") -> MagicMock:
    h = MagicMock()
    h.ticker_code = ticker_code
    return h


def _snapshot(*, account_id: int = 1, holdings: list[MagicMock] | None = None) -> MagicMock:
    s = MagicMock()
    s.account_id = account_id
    s.holdings = holdings or []
    return s


class TestGetSellCandidatesToolUseCase:
    def test_extracts_only_when_all_3_conditions_match(self) -> None:
        snap = _snapshot(holdings=[_holding(ticker_code="A"), _holding(ticker_code="B")])
        snapshot_repo = MagicMock()
        snapshot_repo.find_latest_by_user.return_value = [snap]

        screening = MagicMock()

        def execute_side_effect(*args: object, **kwargs: object) -> list[MagicMock]:
            code = kwargs.get("code")
            if code == "A":
                return [
                    _screening(
                        code="A",
                        evaluation_zone="very_expensive",
                        momentum_signal="sell",
                        roe_trend="declining",
                    )
                ]
            if code == "B":
                return [_screening(code="B", evaluation_zone="cheap", momentum_signal="neutral")]
            return []

        screening.execute.side_effect = execute_side_effect

        usecase = GetSellCandidatesToolUseCase(snapshot_repo=snapshot_repo, screening_usecase=screening)
        result = usecase.execute(user_id=2)

        assert result["count"] == 1
        assert result["evaluated_holdings_count"] == 2
        assert result["candidates"][0]["code"] == "A"
        assert "very_expensive" in result["candidates"][0]["trigger_reasons"]

    def test_returns_empty_when_no_holdings(self) -> None:
        snapshot_repo = MagicMock()
        snapshot_repo.find_latest_by_user.return_value = []
        screening = MagicMock()
        usecase = GetSellCandidatesToolUseCase(snapshot_repo=snapshot_repo, screening_usecase=screening)
        result = usecase.execute(user_id=2)
        assert result == {
            "count": 0,
            "evaluated_holdings_count": 0,
            "candidates": [],
            "judgment_criteria": (
                "保守的: evaluation_zone == very_expensive AND "
                "momentum_signal in (sell, caution) AND roe_trend == declining"
            ),
        }
        screening.execute.assert_not_called()

    def test_skips_holdings_without_ticker_code(self) -> None:
        snap = _snapshot(holdings=[_holding(ticker_code="")])
        snapshot_repo = MagicMock()
        snapshot_repo.find_latest_by_user.return_value = [snap]
        screening = MagicMock()
        usecase = GetSellCandidatesToolUseCase(snapshot_repo=snapshot_repo, screening_usecase=screening)
        result = usecase.execute(user_id=2)
        assert result["evaluated_holdings_count"] == 0


# ============================================================
# GetStockRiskTagsToolUseCase
# ============================================================


class TestGetStockRiskTagsToolUseCase:
    def test_returns_tags_for_known_stock(self) -> None:
        screening = MagicMock()
        screening.execute.return_value = [
            _screening(
                code="5892",
                name="yutori",
                long_balance=400_000,
                short_balance=0,
                latest_price_date="2026-05-15",
            )
        ]
        usecase = GetStockRiskTagsToolUseCase(screening_usecase=screening)
        result = usecase.execute(code="5892")
        assert result["code"] == "5892"
        tag_names = [t["tag"] for t in result["risk_tags"]]
        assert "risk_high_margin_overhang" in tag_names

    def test_raises_when_stock_not_found(self) -> None:
        screening = MagicMock()
        screening.execute.return_value = []
        usecase = GetStockRiskTagsToolUseCase(screening_usecase=screening)
        with pytest.raises(ValueError):
            usecase.execute(code="0000")


# ============================================================
# GetStockOpportunityTagsToolUseCase
# ============================================================


class TestGetStockOpportunityTagsToolUseCase:
    def test_returns_tags_with_rsi(self) -> None:
        screening = MagicMock()
        screening.execute.return_value = [
            _screening(code="7203", evaluation_zone="cheap", progressive_dividend_years=10)
        ]
        technicals = MagicMock()
        indicators = MagicMock()
        indicators.latest = MagicMock(rsi_14=Decimal("25"))
        technicals.execute.return_value = indicators

        usecase = GetStockOpportunityTagsToolUseCase(screening_usecase=screening, technicals_usecase=technicals)
        result = usecase.execute(code="7203")
        assert result["rsi_14"] == "25"
        tag_names = [t["tag"] for t in result["opportunity_tags"]]
        assert "opportunity_value_zone" in tag_names
        assert "opportunity_consecutive_dividend_increase" in tag_names
        assert "opportunity_oversold_rsi" in tag_names

    def test_returns_tags_when_rsi_fetch_fails(self) -> None:
        screening = MagicMock()
        screening.execute.return_value = [_screening(code="7203", evaluation_zone="cheap")]
        technicals = MagicMock()
        technicals.execute.side_effect = RuntimeError("DB error")

        usecase = GetStockOpportunityTagsToolUseCase(screening_usecase=screening, technicals_usecase=technicals)
        result = usecase.execute(code="7203")
        assert result["rsi_14"] is None
        tag_names = [t["tag"] for t in result["opportunity_tags"]]
        assert "opportunity_oversold_rsi" not in tag_names

    def test_raises_when_stock_not_found(self) -> None:
        screening = MagicMock()
        screening.execute.return_value = []
        usecase = GetStockOpportunityTagsToolUseCase(screening_usecase=screening, technicals_usecase=MagicMock())
        with pytest.raises(ValueError):
            usecase.execute(code="0000")
