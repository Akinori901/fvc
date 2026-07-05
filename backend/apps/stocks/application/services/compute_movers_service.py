"""日次急騰急落集計の純関数ロジック。

価格の時系列リストを入力に、当日の前日比・出来高比率・ストップ高安フラグを算出する。
副作用なしのドメイン純関数として実装し、UseCase 側でリポジトリ呼び出しと組み合わせる。
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.stocks.domain.entities import PriceEntity


_VOLUME_AVG_WINDOW = 20  # 出来高 N 日平均


@dataclass(frozen=True)
class MoversInput:
    """1 銘柄分の入力。

    prices_desc: PriceEntity を「日付降順」で並べたリスト。先頭が最新営業日。
    """

    stock_id: int
    prices_desc: list[PriceEntity]


@dataclass(frozen=True)
class MoversOutput:
    """1 銘柄分の集計結果。"""

    stock_id: int
    date: datetime.date
    close_price: Decimal
    prev_close: Decimal | None
    change_pct: Decimal | None  # 例: Decimal("21.2800")
    volume: int | None
    volume_ratio_20d: Decimal | None  # 例: Decimal("3.80")
    is_limit_up: bool
    is_limit_down: bool


def compute_one(input_: MoversInput, target_date: datetime.date | None = None) -> MoversOutput | None:
    """1 銘柄の movers 集計結果を返す。

    target_date が指定された場合は、その日付の PriceEntity を当日として扱う。
    指定がなければ prices_desc の先頭（最新）を当日とする。
    対象日のレコードが見つからない場合は None。
    """
    if not input_.prices_desc:
        return None

    if target_date is not None:
        today_idx = _find_index_by_date(input_.prices_desc, target_date)
        if today_idx is None:
            return None
    else:
        today_idx = 0

    today = input_.prices_desc[today_idx]
    prev = input_.prices_desc[today_idx + 1] if today_idx + 1 < len(input_.prices_desc) else None

    change_pct = _compute_change_pct(today.close_price, prev.close_price if prev else None)
    volume_ratio = _compute_volume_ratio(input_.prices_desc[today_idx:])

    return MoversOutput(
        stock_id=input_.stock_id,
        date=_parse_date(today.date),
        close_price=today.close_price,
        prev_close=prev.close_price if prev else None,
        change_pct=change_pct,
        volume=today.volume,
        volume_ratio_20d=volume_ratio,
        is_limit_up=today.is_limit_up,
        is_limit_down=today.is_limit_down,
    )


def _find_index_by_date(prices_desc: list[PriceEntity], target_date: datetime.date) -> int | None:
    target_str = target_date.isoformat()
    for i, p in enumerate(prices_desc):
        if p.date == target_str:
            return i
    return None


def _compute_change_pct(today_close: Decimal, prev_close: Decimal | None) -> Decimal | None:
    if prev_close is None or prev_close <= 0:
        return None
    return ((today_close - prev_close) / prev_close * Decimal(100)).quantize(Decimal("0.0001"))


def _compute_volume_ratio(prices_from_today: list[PriceEntity]) -> Decimal | None:
    """当日出来高 / 過去 20 営業日平均出来高（当日含めない）。"""
    if len(prices_from_today) < 2:
        return None
    today_volume = prices_from_today[0].volume
    if today_volume is None or today_volume <= 0:
        return None
    past_volumes = [p.volume for p in prices_from_today[1 : 1 + _VOLUME_AVG_WINDOW] if p.volume and p.volume > 0]
    if len(past_volumes) < _VOLUME_AVG_WINDOW // 2:
        return None
    avg = Decimal(sum(past_volumes)) / Decimal(len(past_volumes))
    if avg <= 0:
        return None
    return (Decimal(today_volume) / avg).quantize(Decimal("0.01"))


def _parse_date(date_str: str) -> datetime.date:
    return datetime.date.fromisoformat(date_str)
