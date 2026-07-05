"""PR6 で追加した 2 ツール UseCase の単体テスト（依存はモック）。"""

from __future__ import annotations

import datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from apps.mcp.application.usecases.tools.get_price_distribution_3m_usecase import (
    GetPriceDistribution3mToolUseCase,
)
from apps.mcp.application.usecases.tools.save_ai_decision_usecase import (
    SaveAiDecisionToolUseCase,
)

# ============================================================
# SaveAiDecisionToolUseCase
# ============================================================


class TestSaveAiDecisionToolUseCase:
    def test_saves_decision_with_snapshot(self) -> None:
        decision_repo = MagicMock()
        saved = MagicMock()
        saved.id = 42
        saved.user_id = 2
        saved.decision_type = "buy"
        saved.rationale = "Strong moat"
        saved.confidence = Decimal("0.8")
        saved.ai_model = "claude-4.5-sonnet"
        saved.decided_at = datetime.datetime(2026, 5, 18, tzinfo=datetime.UTC)
        decision_repo.save.return_value = saved

        stock_repo = MagicMock()
        stock = MagicMock()
        stock.id = 100
        stock.code = "7203"
        stock.name = "トヨタ自動車"
        stock_repo.find_by_code.return_value = stock

        summary_uc = MagicMock()
        summary_uc.execute.return_value = {
            "code": "7203",
            "name": "トヨタ自動車",
            "fair_value": "3000",
            "evaluation_zone": "cheap",
        }

        usecase = SaveAiDecisionToolUseCase(
            decision_repo=decision_repo,
            stock_repo=stock_repo,
            summary_usecase=summary_uc,
        )
        result = usecase.execute(
            user_id=2,
            code="7203",
            decision_type="buy",
            rationale="Strong moat",
            confidence=Decimal("0.8"),
            ai_model="claude-4.5-sonnet",
        )

        assert result["id"] == 42
        assert result["decision_type"] == "buy"
        assert result["stock_code"] == "7203"
        assert "code" in result["snapshot_indicators_keys"]
        decision_repo.save.assert_called_once()
        saved_entity = decision_repo.save.call_args.args[0]
        assert saved_entity.snapshot_indicators["evaluation_zone"] == "cheap"

    def test_rejects_invalid_decision_type(self) -> None:
        usecase = SaveAiDecisionToolUseCase(
            decision_repo=MagicMock(),
            stock_repo=MagicMock(),
            summary_usecase=MagicMock(),
        )
        with pytest.raises(ValueError):
            usecase.execute(user_id=2, code="7203", decision_type="invalid", rationale="x")

    def test_raises_when_stock_not_found(self) -> None:
        stock_repo = MagicMock()
        stock_repo.find_by_code.return_value = None
        usecase = SaveAiDecisionToolUseCase(
            decision_repo=MagicMock(),
            stock_repo=stock_repo,
            summary_usecase=MagicMock(),
        )
        with pytest.raises(ValueError):
            usecase.execute(user_id=2, code="0000", decision_type="buy", rationale="x")

    def test_graceful_when_summary_fails(self) -> None:
        decision_repo = MagicMock()
        saved = MagicMock()
        saved.id = 1
        saved.user_id = 2
        saved.decision_type = "hold"
        saved.rationale = "..."
        saved.confidence = None
        saved.ai_model = ""
        saved.decided_at = None
        decision_repo.save.return_value = saved

        stock_repo = MagicMock()
        stock = MagicMock()
        stock.id = 100
        stock.code = "7203"
        stock.name = "トヨタ"
        stock_repo.find_by_code.return_value = stock

        summary_uc = MagicMock()
        summary_uc.execute.side_effect = RuntimeError("DB error")

        usecase = SaveAiDecisionToolUseCase(
            decision_repo=decision_repo,
            stock_repo=stock_repo,
            summary_usecase=summary_uc,
        )
        result = usecase.execute(user_id=2, code="7203", decision_type="hold", rationale="...")
        # snapshot 取得失敗でも保存は通る
        assert result["id"] == 1
        assert result["snapshot_indicators_keys"] == []


# ============================================================
# GetPriceDistribution3mToolUseCase
# ============================================================


def _price(date_str: str, close: float) -> MagicMock:
    p = MagicMock()
    p.date = date_str
    p.close_price = Decimal(str(close))
    return p


class TestGetPriceDistribution3mToolUseCase:
    def test_returns_distribution_with_fair_value(self) -> None:
        stock_repo = MagicMock()
        stock = MagicMock()
        stock.id = 100
        stock.code = "7203"
        stock.name = "トヨタ自動車"
        stock.latest_price = Decimal("2800")
        stock_repo.find_by_code.return_value = stock

        # 60 個の価格データ (Bootstrap 計算可能)
        price_repo = MagicMock()
        price_repo.find_by_stock_id.return_value = [
            _price(f"2026-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}", 2800 - i * 5) for i in range(60)
        ]

        screening_uc = MagicMock()
        sr = MagicMock()
        sr.fair_value = Decimal("3000")
        screening_uc.execute.return_value = [sr]

        usecase = GetPriceDistribution3mToolUseCase(
            stock_repo=stock_repo,
            price_repo=price_repo,
            screening_usecase=screening_uc,
        )
        result = usecase.execute(code="7203", simulation_runs=200, rng_seed=42)

        assert result["code"] == "7203"
        assert result["model"] == "bootstrap"
        assert result["fair_value"] == "3000"
        assert result["percentiles"] is not None
        assert "p50" in result["percentiles"]
        assert result["prob_above_current"] is not None
        assert result["prob_above_fair_value"] is not None
        assert result.get("not_calculable_reason") is None

    def test_raises_when_stock_not_found(self) -> None:
        stock_repo = MagicMock()
        stock_repo.find_by_code.return_value = None
        usecase = GetPriceDistribution3mToolUseCase(
            stock_repo=stock_repo,
            price_repo=MagicMock(),
            screening_usecase=MagicMock(),
        )
        with pytest.raises(ValueError):
            usecase.execute(code="0000")

    def test_raises_when_no_latest_price(self) -> None:
        stock_repo = MagicMock()
        stock = MagicMock()
        stock.id = 100
        stock.latest_price = None
        stock_repo.find_by_code.return_value = stock
        usecase = GetPriceDistribution3mToolUseCase(
            stock_repo=stock_repo,
            price_repo=MagicMock(),
            screening_usecase=MagicMock(),
        )
        with pytest.raises(ValueError):
            usecase.execute(code="7203")

    def test_returns_not_calculable_when_insufficient_data(self) -> None:
        stock_repo = MagicMock()
        stock = MagicMock()
        stock.id = 100
        stock.code = "7203"
        stock.name = "トヨタ"
        stock.latest_price = Decimal("2800")
        stock_repo.find_by_code.return_value = stock

        price_repo = MagicMock()
        price_repo.find_by_stock_id.return_value = [_price("2026-05-15", 2800), _price("2026-05-14", 2790)]

        screening_uc = MagicMock()
        screening_uc.execute.return_value = []

        usecase = GetPriceDistribution3mToolUseCase(
            stock_repo=stock_repo,
            price_repo=price_repo,
            screening_usecase=screening_uc,
        )
        result = usecase.execute(code="7203", simulation_runs=100)
        assert result["not_calculable_reason"] is not None
        assert result["percentiles"] is None
