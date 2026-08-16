"""スクリーニング（銘柄一覧）スナップショット生成コマンド。

ScreeningUseCase をフィルタ無し・全件で実行し、growth_rate 非依存の計算結果を
t_screening_snapshots に保存する。一覧APIは本テーブルを SELECT し、リクエスト時の
growth_rate から適正株価・評価ゾーン・総合評価スコアだけを軽量に再計算する。
平日の株価同期後に EventBridge 経由で Worker Lambda 上で実行される。
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any

from django.core.management.base import BaseCommand
from django.db import transaction

if TYPE_CHECKING:
    from apps.stocks.application.usecases.screening_usecase import ScreeningResult

_DEFAULT_GROWTH_RATE = Decimal("0.03")


def _s(v: Any) -> str | None:
    return str(v) if v is not None else None


def _to_metrics(r: ScreeningResult) -> dict[str, Any]:
    """個別カラム以外の指標を JSON にまとめる（Decimal は文字列化）。"""
    return {
        "latest_price": _s(r.latest_price),
        "bps": _s(r.bps),
        "eps": _s(r.eps),
        "current_pbr": _s(r.current_pbr),
        "implied_growth_rate": _s(r.implied_growth_rate),
        "eps_growth_yoy": _s(r.eps_growth_yoy),
        "eps_cagr_3y": _s(r.eps_cagr_3y),
        "revenue_growth_yoy": _s(r.revenue_growth_yoy),
        "op_income_growth_yoy": _s(r.op_income_growth_yoy),
        "company_forecast_growth_rate": _s(r.company_forecast_growth_rate),
        "long_balance": r.long_balance,
        "short_balance": r.short_balance,
        "long_balance_change_pct": _s(r.long_balance_change_pct),
        "long_balance_trend": r.long_balance_trend,
        "price_position_52w": _s(r.price_position_52w),
        "distance_from_52w_high": _s(r.distance_from_52w_high),
        "volume_ratio_20d": _s(r.volume_ratio_20d),
        "ma_25_deviation": _s(r.ma_25_deviation),
        "avg_turnover_20d": _s(r.avg_turnover_20d),
        "payout_ratio": _s(r.payout_ratio),
        "consecutive_dividend_years": r.consecutive_dividend_years,
        "progressive_dividend_years": r.progressive_dividend_years,
        "dividend_score": r.dividend_score,
        "fcf": r.fcf,
        "prev_fcf": r.prev_fcf,
        "fcf_margin": _s(r.fcf_margin),
        "fcf_score": r.fcf_score,
        "owner_ratio": _s(r.owner_ratio),
        "owner_match_type": r.owner_match_type,
        "not_calculable_reason": r.not_calculable_reason,
        "is_manual_financial": r.is_manual_financial,
    }


class Command(BaseCommand):
    help = "スクリーニング（銘柄一覧）スナップショットを生成・保存する"

    def handle(self, *args: Any, **options: Any) -> None:
        from apps.stocks.models import ScreeningSnapshot, Stock
        from config.container import _build_full_screening_usecase

        self.stdout.write("スクリーニングスナップショット生成を開始します...")
        usecase = _build_full_screening_usecase()
        # ScreeningResult は code を持つが stock_id を持たないため、code→id を引けるようにする
        code_to_id: dict[str, int] = dict(Stock.objects.values_list("code", "id"))

        objs: list[ScreeningSnapshot] = []
        for market_type in ("JP", "US"):
            results = usecase.execute(
                growth_rate=_DEFAULT_GROWTH_RATE,
                market_type=market_type,
                include_inactive=True,  # 上場廃止も保存（一覧側で is_active フィルタ）
                compute_buy_signals=True,  # 絞り込まず買い時シグナルを全計算
            )
            for r in results:
                stock_id = code_to_id.get(r.code)
                if stock_id is None:
                    continue
                objs.append(
                    ScreeningSnapshot(
                        stock_id=stock_id,
                        code=r.code,
                        name=r.name,
                        sector=r.sector or "",
                        market_type=market_type,
                        is_active=r.is_active,
                        roe=r.roe,
                        sl_ratio=r.sl_ratio,
                        roe_trend=r.roe_trend,
                        dividend_yield=r.dividend_yield,
                        fcf_yield=r.fcf_yield,
                        momentum_signal=r.momentum_signal,
                        liquidity_level=r.liquidity_level,
                        is_owner_managed=r.is_owner_managed,
                        ma_golden_cross=r.ma_golden_cross,
                        price_cross_ma25=r.price_cross_ma25,
                        price_cross_ma75=r.price_cross_ma75,
                        macd_golden_cross=r.macd_golden_cross,
                        rsi_rebound=r.rsi_rebound,
                        pullback_buy=r.pullback_buy,
                        metrics=_to_metrics(r),
                    )
                )
            self.stdout.write(f"  {market_type}: {len(results)}件 計算")

        with transaction.atomic():
            ScreeningSnapshot.objects.all().delete()
            ScreeningSnapshot.objects.bulk_create(objs, batch_size=500)

        self.stdout.write(self.style.SUCCESS(f"完了: {len(objs)}件保存"))
