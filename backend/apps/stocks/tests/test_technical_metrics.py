"""買い時テクニカルシグナル判定（technical_metrics._compute_buy_signals）の単体テスト。

DB を使わない純関数テスト。recent_prices は日付降順（先頭が最新）で渡す。
合成価格列は「クロス/反発が直近5営業日以内に発生」するよう調整してある。
"""

from __future__ import annotations

from decimal import Decimal

from apps.stocks.domain.entities import PriceEntity
from apps.stocks.domain.technical_metrics import _compute_buy_signals


def _desc(closes: list[float]) -> list[PriceEntity]:
    """古い順の終値リストから、日付降順（先頭が最新）の PriceEntity リストを作る。"""
    prices = [PriceEntity(stock_id=1, date=str(i), close_price=Decimal(str(c))) for i, c in enumerate(closes)]
    return list(reversed(prices))


def _signals(
    closes: list[float], *, need_ma: bool = True, need_macd: bool = True, need_rsi: bool = True
) -> dict[str, bool]:
    return _compute_buy_signals(_desc(closes), need_ma=need_ma, need_macd=need_macd, need_rsi=need_rsi)


class TestMaGoldenCross:
    def test_positive(self) -> None:
        # 下降80本（25MA<75MA）→ 末尾24本で上昇し、直近5日以内に25MAが75MAを上抜け
        closes = [200.0 - i * 0.8 for i in range(80)] + [200.0 - 64.0 + i * 3 for i in range(1, 25)]
        assert _signals(closes)["ma_golden_cross"] is True

    def test_negative_no_cross(self) -> None:
        # ずっと下降のまま（クロスなし）
        closes = [300.0 - i for i in range(130)]
        assert _signals(closes)["ma_golden_cross"] is False

    def test_negative_insufficient_data(self) -> None:
        # 100本未満は判定対象外 → 全 False
        closes = [100.0 + i for i in range(50)]
        assert all(v is False for v in _signals(closes).values())


class TestPriceCross:
    def test_price_cross_ma25_positive(self) -> None:
        closes = [200.0 - i * 0.7 for i in range(95)] + [200.0 - 66.5 + i * 4 for i in range(1, 6)]
        assert _signals(closes)["price_cross_ma25"] is True

    def test_price_cross_ma75_positive(self) -> None:
        closes = [200.0 - i * 0.6 for i in range(100)] + [200.0 - 60.0 + i * 5 for i in range(1, 6)]
        assert _signals(closes)["price_cross_ma75"] is True


class TestRsiRebound:
    def test_positive(self) -> None:
        # 継続下落で RSI が 30 以下 → 末尾で反発して 30 を上抜け
        closes = [300.0 - i * 1.5 for i in range(115)] + [300.0 - 172.5 + i * 5 for i in range(1, 4)]
        assert _signals(closes)["rsi_rebound"] is True

    def test_negative_flat(self) -> None:
        # ほぼ横ばい（RSI が 30 以下に達しない）
        closes = [100.0 + (i % 2) for i in range(130)]
        assert _signals(closes)["rsi_rebound"] is False


class TestMacdGoldenCross:
    def test_positive(self) -> None:
        # 下落から末尾で上昇転換 → MACD ヒストグラムが負→正
        closes = [200.0 - i * 0.8 for i in range(100)] + [200.0 - 80.0 + i * 2 for i in range(1, 4)]
        assert _signals(closes)["macd_golden_cross"] is True


class TestPullbackBuy:
    def test_positive(self) -> None:
        # 上昇トレンド（25MA>75MA を維持）で一時的に終値が25日線を割り込み、末尾で再度上抜け
        closes = [100.0 + i * 2 for i in range(112)] + [318.0, 312.0, 308.0, 300.0, 330.0]
        assert _signals(closes)["pullback_buy"] is True

    def test_negative_downtrend(self) -> None:
        # 下降トレンド（25MA<75MA）では押し目買いにならない
        closes = [300.0 - i for i in range(130)]
        assert _signals(closes)["pullback_buy"] is False


class TestNeedFlags:
    def test_skips_uncomputed_signals(self) -> None:
        # need_* が False の系列は計算されず False のまま
        closes = [200.0 - i * 0.8 for i in range(80)] + [200.0 - 64.0 + i * 3 for i in range(1, 25)]
        result = _compute_buy_signals(_desc(closes), need_ma=False, need_macd=False, need_rsi=False)
        assert all(v is False for v in result.values())
