"""銘柄テクニカル指標 API ビュー。"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from config import container

if TYPE_CHECKING:
    from decimal import Decimal

    from rest_framework.request import Request

    from apps.stocks.domain.stock_technical_indicators import (
        IndicatorLatest,
        IndicatorSeries,
    )


_ALLOWED_PERIODS = {"1m", "3m", "6m", "1y", "all"}


def _d(v: Decimal | None) -> str | None:
    return str(v) if v is not None else None


def _series_to_dict(s: IndicatorSeries) -> dict[str, Any]:
    return {
        "date": s.date,
        "close": str(s.close),
        "ma_25": _d(s.ma_25),
        "ma_75": _d(s.ma_75),
        "ma_200": _d(s.ma_200),
        "bb_upper": _d(s.bb_upper),
        "bb_middle": _d(s.bb_middle),
        "bb_lower": _d(s.bb_lower),
        "rsi_14": _d(s.rsi_14),
        "macd": _d(s.macd),
        "macd_signal": _d(s.macd_signal),
        "macd_hist": _d(s.macd_hist),
        "stoch_k": _d(s.stoch_k),
        "stoch_d": _d(s.stoch_d),
        "atr_14": _d(s.atr_14),
    }


def _latest_to_dict(latest: IndicatorLatest) -> dict[str, Any]:
    return {
        "ma_25": _d(latest.ma_25),
        "ma_75": _d(latest.ma_75),
        "ma_200": _d(latest.ma_200),
        "ma_25_deviation_pct": _d(latest.ma_25_deviation_pct),
        "ma_75_deviation_pct": _d(latest.ma_75_deviation_pct),
        "ma_200_deviation_pct": _d(latest.ma_200_deviation_pct),
        "bb_upper": _d(latest.bb_upper),
        "bb_middle": _d(latest.bb_middle),
        "bb_lower": _d(latest.bb_lower),
        "bb_position": _d(latest.bb_position),
        "bb_signal": latest.bb_signal,
        "rsi_14": _d(latest.rsi_14),
        "rsi_signal": latest.rsi_signal,
        "macd": _d(latest.macd),
        "macd_signal": _d(latest.macd_signal),
        "macd_hist": _d(latest.macd_hist),
        "macd_cross": latest.macd_cross,
        "stoch_k": _d(latest.stoch_k),
        "stoch_d": _d(latest.stoch_d),
        "stoch_signal": latest.stoch_signal,
        "atr_14": _d(latest.atr_14),
        "atr_pct": _d(latest.atr_pct),
        "momentum_25d_pct": _d(latest.momentum_25d_pct),
        "momentum_signal": latest.momentum_signal,
    }


class StockTechnicalView(APIView):
    """GET /api/stocks/{code}/technical/?period=1y — 銘柄テクニカル指標。"""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request, code: str) -> Response:
        period = request.query_params.get("period", "1y")
        if period not in _ALLOWED_PERIODS:
            return Response(
                {"detail": f"period は {sorted(_ALLOWED_PERIODS)} のいずれかを指定してください"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        usecase = container.get_stock_technicals_usecase()
        indicators = usecase.execute(code, period=period)

        if indicators is None:
            return Response(
                {"detail": f"銘柄が見つかりません: {code}"},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            {
                "code": code,
                "data_points": indicators.data_points,
                "insufficient_data": indicators.insufficient_data,
                "atr_approximation": indicators.atr_approximation,
                "latest": _latest_to_dict(indicators.latest) if indicators.latest else None,
                "series": [_series_to_dict(s) for s in indicators.series],
            }
        )
