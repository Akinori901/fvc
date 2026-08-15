"""割安株スクリーニングユースケース。"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

from apps.stocks.domain.dividend_metrics import compute_dividend_metrics
from apps.stocks.domain.fcf_metrics import compute_fcf_metrics
from apps.stocks.domain.growth_metrics import compute_growth_metrics
from apps.stocks.domain.margin_trend_metrics import compute_margin_trend_metrics
from apps.stocks.domain.technical_metrics import compute_technical_metrics
from apps.valuations.domain.entities import MARKET_COST_OF_CAPITAL, FairValueCalculation, growth_rate_label

if TYPE_CHECKING:
    from apps.stocks.domain.entities import DividendEntity
    from apps.stocks.domain.repositories import (
        DividendRepository,
        FinancialRepository,
        MarginRepository,
        OwnerShareholderRepository,
        PriceRepository,
        StockRepository,
    )

logger = logging.getLogger(__name__)

# Gordon Growth Model の評価対象外市場区分（ETF・REIT・TOKYO PRO等）
# これらは株式固有の ROE/BPS/EPS 指標で評価できない
_NON_EQUITY_MARKETS = frozenset({"その他", "TOKYO PRO MARKET"})


@dataclass
class ScreeningResult:
    """スクリーニング結果。計算不可の場合は計算フィールドが None になる。"""

    code: str
    name: str
    sector: str
    latest_price: Decimal | None
    latest_price_date: str | None
    bps: Decimal | None
    eps: Decimal | None
    roe: Decimal | None
    fair_pbr: Decimal | None
    fair_value: Decimal | None
    discount_rate: Decimal | None
    evaluation_zone: str | None
    current_pbr: Decimal | None
    implied_growth_rate: Decimal | None
    growth_rate_label: str | None
    company_forecast_growth_rate: Decimal | None = None
    is_active: bool = True
    not_calculable_reason: str | None = None  # 計算不可の場合の理由コード
    is_manual_financial: bool = False  # 手動入力財務データを使用中か
    # 業績成長指標
    eps_growth_yoy: Decimal | None = None
    eps_cagr_3y: Decimal | None = None
    roe_trend: str | None = None  # "improving" / "declining" / "stable"
    revenue_growth_yoy: Decimal | None = None
    op_income_growth_yoy: Decimal | None = None
    # 信用取引残高
    sl_ratio: Decimal | None = None  # 信売比率
    long_balance: int | None = None  # 信用買残（株数）
    short_balance: int | None = None  # 信用売残（株数）
    long_balance_change: int | None = None  # 信用買残変化
    # 信用買残トレンド（指定期間の増減）
    long_balance_change_pct: Decimal | None = None  # 指定期間の信用買残変化率 (%)
    long_balance_trend: str | None = None  # "increasing" / "decreasing" / "flat"
    # テクニカル指標（52週高値効果）
    price_position_52w: Decimal | None = None  # 52週レンジ内の位置 (0.0〜1.0)
    near_52w_high: bool | None = None  # 52週高値近接フラグ (5%以内)
    distance_from_52w_high: Decimal | None = None  # 52週高値からの乖離率
    volume_ratio_20d: Decimal | None = None  # 出来高比率 (5日平均/20日平均)
    ma_25_deviation: Decimal | None = None  # 25日移動平均乖離率
    momentum_signal: str | None = None  # "strong_buy" / "buy" / "neutral" / "caution" / "sell"
    # 流動性指標
    avg_turnover_20d: Decimal | None = None  # 売買代金20日平均（円）
    liquidity_level: str | None = None  # "high" / "medium" / "low" / "very_low"
    # 配当評価
    dividend_yield: Decimal | None = None  # 配当利回り (%)
    payout_ratio: Decimal | None = None  # 配当性向 (%)
    consecutive_dividend_years: int | None = None  # 連続配当年数
    progressive_dividend_years: int | None = None  # 累進配当年数
    dividend_score: int | None = None  # 配当スコア (-2 ~ +2)
    # FCF指標
    fcf: int | None = None  # FCF（百万円）
    fcf_yield: Decimal | None = None  # FCF利回り (%)
    fcf_margin: Decimal | None = None  # FCFマージン (%)
    fcf_score: int | None = None  # FCFスコア (-2 ~ +2)
    # オーナー経営指標
    is_owner_managed: bool = False
    owner_ratio: Decimal | None = None  # 代表者関連の持ち株比率合計 (%)
    owner_match_type: str | None = None  # "exact" / "family" / "company"
    # 買い時テクニカルシグナル（データ不足時は False = 非該当）
    ma_golden_cross: bool = False  # 25日線が75日線を上抜け
    price_cross_ma25: bool = False  # 終値が25日線を上抜け
    price_cross_ma75: bool = False  # 終値が75日線を上抜け
    macd_golden_cross: bool = False  # MACDがシグナル線を上抜け
    rsi_rebound: bool = False  # RSI(14)が30以下から反発
    pullback_buy: bool = False  # 上昇トレンド中の押し目買い


_LIQUIDITY_ORDER: dict[str, int] = {"high": 3, "medium": 2, "low": 1, "very_low": 0}
_MOMENTUM_ORDER: dict[str, int] = {"strong_buy": 4, "buy": 3, "neutral": 2, "caution": 1, "sell": 0}


def _trend_weeks(months: int) -> int:
    """信用買残トレンドの評価に必要な週数（余裕を持たせて +2 週分取得する）。"""
    return int(months * 4.345) + 2


def _get_liquidity_level(avg_turnover: Decimal | None) -> str | None:
    """売買代金20日平均から流動性レベルを判定。"""
    if avg_turnover is None:
        return None
    if avg_turnover >= 1_000_000_000:  # 10億円
        return "high"
    if avg_turnover >= 100_000_000:  # 1億円
        return "medium"
    if avg_turnover >= 10_000_000:  # 1000万円
        return "low"
    return "very_low"


def _get_not_calculable_reason(
    can_calculate: bool,
    latest_price: Decimal | None,
    financial: object | None,
    bps: Decimal | None,
    roe: Decimal | None,
    growth_rate: Decimal,
) -> str:
    """計算不可理由コードを返す。"""
    if not can_calculate:
        return "growth_ge_cost"
    if latest_price is None:
        return "no_price"
    if financial is None:
        return "no_financial"
    if bps is None or bps <= 0:
        return "bps_invalid"
    if roe is None or roe <= 0:
        return "roe_not_positive"
    return "roe_le_growth"


def _get_evaluation_zone(discount_rate: Decimal) -> str:
    """乖離率から評価ゾーンを判定。"""
    if discount_rate >= Decimal("0.4"):
        return "very_cheap"
    if discount_rate >= Decimal("0.2"):
        return "cheap"
    if discount_rate >= Decimal("-0.2"):
        return "fair"
    if discount_rate >= Decimal("-0.5"):
        return "expensive"
    return "very_expensive"


class ScreeningUseCase:
    """全銘柄をスクリーニングし、割安度で並べて返す。"""

    def __init__(
        self,
        stock_repo: StockRepository,
        financial_repo: FinancialRepository,
        margin_repo: MarginRepository | None = None,
        price_repo: PriceRepository | None = None,
        dividend_repo: DividendRepository | None = None,
        owner_repo: OwnerShareholderRepository | None = None,
    ) -> None:
        self._stock_repo = stock_repo
        self._financial_repo = financial_repo
        self._margin_repo = margin_repo
        self._price_repo = price_repo
        self._dividend_repo = dividend_repo
        self._owner_repo = owner_repo

    def execute(
        self,
        growth_rate: Decimal,
        market_type: str = "JP",
        sector: str | None = None,
        min_discount: Decimal | None = None,
        include_inactive: bool = False,
        min_eps_growth_yoy: Decimal | None = None,
        min_eps_cagr_3y: Decimal | None = None,
        roe_trend_filter: str | None = None,  # "improving" のみ絞り込む場合
        min_roe: Decimal | None = None,
        max_sl_ratio: Decimal | None = None,  # 信売比率の上限フィルター
        min_dividend_yield: Decimal | None = None,
        max_payout_ratio: Decimal | None = None,
        min_consecutive_dividend_years: int | None = None,
        min_progressive_dividend_years: int | None = None,
        min_liquidity_level: str | None = None,  # "high"/"medium"/"low"/"very_low"
        min_momentum_signal: str | None = None,  # "strong_buy"/"buy"/"neutral"/"caution"/"sell"
        owner_managed_only: bool = False,
        min_fcf_yield: Decimal | None = None,
        margin_trend_months: int | None = None,  # 信用買残トレンドの評価期間（月）
        long_balance_trend: str | None = None,  # "increasing" / "decreasing"
        margin_trend_threshold_pct: Decimal | None = None,  # 変化率の閾値（絶対値, %）
        # 買い時テクニカルシグナル（ON の時だけ該当銘柄に絞り込む）
        ma_golden_cross_only: bool = False,
        price_cross_ma25_only: bool = False,
        price_cross_ma75_only: bool = False,
        macd_golden_cross_only: bool = False,
        rsi_rebound_only: bool = False,
        pullback_buy_only: bool = False,
        code: str | None = None,  # 単一銘柄モード: 指定された場合は対象銘柄のみ計算
    ) -> list[ScreeningResult]:
        """スクリーニングを実行。

        - 計算可能な銘柄は discount_rate 降順で先頭に並ぶ。
        - データ不足で計算できない銘柄は末尾に追加される（discount_rate = None）。
        - min_discount が指定された場合は discount_rate が None の銘柄を除外する。
        - include_inactive=True の場合は上場廃止銘柄も含む。
        - min_eps_growth_yoy / min_eps_cagr_3y / roe_trend_filter / min_roe: 成長フィルター。
        - max_sl_ratio: 信売比率の上限フィルター。
        - margin_trend_months / long_balance_trend / margin_trend_threshold_pct:
          信用買残トレンドフィルター。指定期間の買残変化率で増加・減少を絞り込む。
          期間分のデータが無い銘柄は判定不能として除外される。
        - code: 指定された場合、その1銘柄のみ計算する（StockDetailView などからの呼び出し用）。
        """
        if code is not None:
            target = self._stock_repo.find_by_code(code)
            stocks = [target] if target is not None else []
        else:
            stocks = self._stock_repo.find_by_market_type(market_type, active_only=not include_inactive)

        cost_of_capital = MARKET_COST_OF_CAPITAL.get(market_type, MARKET_COST_OF_CAPITAL["JP"])
        can_calculate = growth_rate < cost_of_capital

        # 買い時テクニカルシグナル: 必要な系列だけ計算し、利用時のみ日足を多めに取得する
        need_ma = ma_golden_cross_only or price_cross_ma25_only or price_cross_ma75_only or pullback_buy_only
        need_macd = macd_golden_cross_only
        need_rsi = rsi_rebound_only
        any_buy_signal = need_ma or need_macd or need_rsi
        # 75日MA + クロス直前20日下 + 5日窓 に足る日数（利用時のみ）。通常は既存どおり25本。
        price_limit = 120 if any_buy_signal else 25

        # 一括取得（N+1 問題の解消: ~10,500 クエリ → 7 クエリ）
        # 単一銘柄モード（code 指定時）は対象銘柄分のみ取得して全銘柄スキャンを避ける
        if code is not None and stocks and stocks[0].id is not None:
            sid = stocks[0].id
            single_fin = self._financial_repo.find_latest_by_stock_id(sid)
            all_financials = {sid: single_fin} if single_fin else {}
            all_recent = {sid: self._financial_repo.find_recent_by_stock_id(sid, limit=4)}
            single_margin = self._margin_repo.find_latest_by_stock_id(sid) if self._margin_repo else None
            all_margins = {sid: single_margin} if single_margin else {}
            all_recent_margins = {}
            if self._margin_repo and margin_trend_months:
                recent_m = self._margin_repo.find_recent_by_stock_id(sid, limit=_trend_weeks(margin_trend_months))
                all_recent_margins = {sid: recent_m} if recent_m else {}
            try:
                hl = self._price_repo.find_52w_high_low(sid) if self._price_repo else None
                all_52w = {sid: hl} if hl else {}
                recent_prices = self._price_repo.find_by_stock_id(sid, limit=price_limit) if self._price_repo else []
                all_recent_prices = {sid: recent_prices} if recent_prices else {}
            except Exception:
                import logging

                logging.getLogger(__name__).warning("テクニカル指標の取得に失敗。フォールバック。", exc_info=True)
                all_52w = {}
                all_recent_prices = {}
        else:
            all_financials = self._financial_repo.find_all_latest()
            all_recent = self._financial_repo.find_all_recent(limit=4)
            all_margins = self._margin_repo.find_all_latest() if self._margin_repo else {}
            all_recent_margins = {}
            if self._margin_repo and margin_trend_months:
                try:
                    all_recent_margins = self._margin_repo.find_all_recent(weeks=_trend_weeks(margin_trend_months))
                except Exception:
                    import logging

                    logging.getLogger(__name__).warning("信用残高履歴の取得に失敗。フォールバック。", exc_info=True)
            try:
                all_52w = self._price_repo.find_all_52w_high_low() if self._price_repo else {}
                all_recent_prices = (
                    self._price_repo.find_all_recent_prices(limit=price_limit) if self._price_repo else {}
                )
            except Exception:
                import logging

                logging.getLogger(__name__).warning("テクニカル指標の取得に失敗。フォールバック。", exc_info=True)
                all_52w = {}
                all_recent_prices = {}

        # 配当データの取得
        stock_ids = [s.id for s in stocks if s.id is not None and s.market not in _NON_EQUITY_MARKETS]

        all_annual_totals: dict[int, Decimal] = {}
        all_dividends: dict[int, list[DividendEntity]] = {}
        if self._dividend_repo and stock_ids:
            try:
                if code is not None:
                    sid = stock_ids[0]
                    annual = self._dividend_repo.find_annual_total(sid)
                    all_annual_totals = {sid: annual} if annual is not None else {}
                    divs = self._dividend_repo.find_by_stock_id(sid, limit=500)
                    all_dividends = {sid: divs} if divs else {}
                else:
                    all_annual_totals = self._dividend_repo.find_all_annual_totals(stock_ids)
                    all_dividends = self._dividend_repo.find_all_by_stock_ids(stock_ids)
            except Exception:
                logger.warning("配当データの取得に失敗。フォールバック。", exc_info=True)

        # オーナー経営データの取得
        all_owners: dict[int, list[object]] = {}
        if self._owner_repo and stock_ids:
            try:
                all_owners = self._owner_repo.find_latest_by_stock_ids(stock_ids)  # type: ignore[assignment]
            except Exception:
                logger.warning("オーナー経営データの取得に失敗。フォールバック。", exc_info=True)

        results: list[ScreeningResult] = []
        for stock in stocks:
            # 市場区分フィルター（ETF・REIT・TOKYO PRO等は Gordon Growth Model の対象外）
            if stock.market in _NON_EQUITY_MARKETS:
                continue
            # セクターフィルター
            if sector and stock.sector != sector:
                continue
            # DB整合性（id なし銘柄は財務データ取得不可）
            if stock.id is None:
                continue

            financial = all_financials.get(stock.id)
            roe = financial.computed_roe if financial else None

            # 成長指標の計算（直近4件の財務データ使用）
            recent_financials = all_recent.get(stock.id, [])
            gm = compute_growth_metrics(recent_financials)

            # 信用残高の取得
            margin = all_margins.get(stock.id)

            # テクニカル指標（52週高値効果）
            tm = compute_technical_metrics(
                latest_price=stock.latest_price,
                high_low=all_52w.get(stock.id),
                recent_prices=all_recent_prices.get(stock.id, []),
                need_ma=need_ma,
                need_macd=need_macd,
                need_rsi=need_rsi,
            )

            # 配当メトリクスの計算
            dm = compute_dividend_metrics(
                dividends=all_dividends.get(stock.id, []),
                annual_total=all_annual_totals.get(stock.id),
                latest_price=stock.latest_price,
                eps=financial.eps if financial else None,
            )

            # FCFメトリクスの計算
            _market_cap: Decimal | None = None
            if stock.latest_price is not None and financial is not None and financial.total_shares:
                _market_cap = stock.latest_price * Decimal(financial.total_shares)
            _prev_fcf: int | None = None
            if len(recent_financials) >= 2 and recent_financials[1].free_cash_flow is not None:  # noqa: PLR2004
                _prev_fcf = recent_financials[1].free_cash_flow
            fm = compute_fcf_metrics(
                latest_fcf=financial.free_cash_flow if financial else None,
                prev_fcf=_prev_fcf,
                market_cap=_market_cap,
                revenue=financial.revenue if financial else None,
            )

            # 信用買残トレンド指標
            mtm = compute_margin_trend_metrics(
                recent_margins=all_recent_margins.get(stock.id, []),
                months=margin_trend_months or 0,
            )

            # オーナー経営指標
            owner_list = all_owners.get(stock.id, [])
            is_owner = bool(owner_list)
            _owner_ratio: Decimal | None = None
            _owner_type: str | None = None
            if owner_list:
                _owner_ratio = Decimal(0)
                for _o in owner_list:
                    _owner_ratio += getattr(_o, "ownership_ratio", Decimal(0))
                # 最も確度の高い match_type を選出
                _type_priority = {"exact": 0, "family": 1, "company": 2}
                _owner_type = min(
                    (getattr(o, "match_type", "company") for o in owner_list),
                    key=lambda t: _type_priority.get(t, 99),
                )

            # 成長フィルター（データがある場合のみ適用）
            if (
                min_eps_growth_yoy is not None
                and gm.eps_growth_yoy is not None
                and gm.eps_growth_yoy < min_eps_growth_yoy
            ):
                continue
            if min_eps_cagr_3y is not None and gm.eps_cagr_3y is not None and gm.eps_cagr_3y < min_eps_cagr_3y:
                continue
            if roe_trend_filter is not None and gm.roe_trend is not None and gm.roe_trend != roe_trend_filter:
                continue
            if min_roe is not None and roe is not None and roe < min_roe:
                continue
            # 信売比率フィルター（データがある場合のみ適用）
            if (
                max_sl_ratio is not None
                and margin is not None
                and margin.sl_ratio is not None
                and margin.sl_ratio > max_sl_ratio
            ):
                continue
            # 配当フィルター
            if min_dividend_yield is not None and (dm.dividend_yield is None or dm.dividend_yield < min_dividend_yield):
                continue
            if max_payout_ratio is not None and (dm.payout_ratio is not None and dm.payout_ratio > max_payout_ratio):
                continue
            if min_consecutive_dividend_years is not None and (
                dm.consecutive_dividend_years is None or dm.consecutive_dividend_years < min_consecutive_dividend_years
            ):
                continue
            if min_progressive_dividend_years is not None and (
                dm.progressive_dividend_years is None or dm.progressive_dividend_years < min_progressive_dividend_years
            ):
                continue
            # 流動性フィルター
            _liq = _get_liquidity_level(tm.avg_turnover_20d)
            if min_liquidity_level is not None and (
                _liq is None or _LIQUIDITY_ORDER.get(_liq, -1) < _LIQUIDITY_ORDER.get(min_liquidity_level, -1)
            ):
                continue
            # モメンタムフィルター
            if min_momentum_signal is not None and (
                tm.momentum_signal is None
                or _MOMENTUM_ORDER.get(tm.momentum_signal, -1) < _MOMENTUM_ORDER.get(min_momentum_signal, -1)
            ):
                continue
            # FCFフィルター
            if min_fcf_yield is not None and (fm.fcf_yield is None or fm.fcf_yield < min_fcf_yield):
                continue
            # オーナー経営フィルター
            if owner_managed_only and not is_owner:
                continue
            # 信用買残トレンドフィルター
            # （期間分のデータが無い銘柄は判定できないため除外する）
            if long_balance_trend is not None:
                if mtm.long_balance_change_pct is None:
                    continue
                if long_balance_trend == "decreasing":
                    threshold = -(margin_trend_threshold_pct or Decimal(0))
                    if mtm.long_balance_change_pct > threshold:
                        continue
                elif long_balance_trend == "increasing":
                    threshold = margin_trend_threshold_pct or Decimal(0)
                    if mtm.long_balance_change_pct < threshold:
                        continue

            # 買い時テクニカルシグナルフィルター（ON の時、該当しない銘柄を除外）
            # データ不足の銘柄は tm 側が False を返すため確実に除外される
            if ma_golden_cross_only and not tm.ma_golden_cross:
                continue
            if price_cross_ma25_only and not tm.price_cross_ma25:
                continue
            if price_cross_ma75_only and not tm.price_cross_ma75:
                continue
            if macd_golden_cross_only and not tm.macd_golden_cross:
                continue
            if rsi_rebound_only and not tm.rsi_rebound:
                continue
            if pullback_buy_only and not tm.pullback_buy:
                continue

            # 株式分割調整済みBPS（adj_factor は手動入力データでは 1.0 のまま）
            effective_bps = (
                financial.bps * financial.adj_factor if financial is not None and financial.bps is not None else None
            )

            # 現在PBR（ROE とは独立して計算可能）
            current_pbr = (
                (stock.latest_price / effective_bps).quantize(Decimal("0.0001"))
                if stock.latest_price is not None and effective_bps is not None and effective_bps > 0
                else None
            )

            # 市場折込成長率（現在PBR と ROE があれば計算可能 — Fix B）
            # PBR < 1 かつ計算値 >= r: 符号反転により発生。市場がROEの持続性を疑うシグナルとして表示
            # PBR > 1 かつ計算値 >= r: ROE < r の企業（価値破壊）でラベルなし表示
            implied_gr: Decimal | None = None
            gr_label: str | None = None
            if current_pbr is not None and roe is not None:
                try:
                    if abs(current_pbr - Decimal("1")) >= Decimal("0.05"):
                        _implied = ((current_pbr * cost_of_capital - roe) / (current_pbr - Decimal("1"))).quantize(
                            Decimal("0.0001")
                        )
                        implied_gr = _implied
                        if current_pbr < Decimal("1") and _implied >= cost_of_capital:
                            # PBR < 1 かつ計算値 >= 資本コスト:
                            # 市場がROEの持続性を疑っているシグナル（"かなり強気" とは別の意味）
                            gr_label = "ROE持続性に疑念"
                        elif _implied < cost_of_capital:
                            gr_label = growth_rate_label(implied_gr)
                        # PBR > 1 かつ _implied >= r の場合は gr_label = None のまま
                except Exception:
                    pass

            # 計算可否の判定
            # Fix C: roe > growth_rate 制約を除去 → ROE が正であればゴードンモデルを実行
            # （ROE < growth_rate の場合 fair_pbr が負になるが、それも有効な評価情報）
            # ROE ≦ 0 の赤字企業はゴードンモデル不適用のため除外
            calculable = (
                can_calculate
                and stock.latest_price is not None
                and financial is not None
                and effective_bps is not None
                and effective_bps > 0
                and roe is not None
                and roe > 0
            )

            if calculable:
                assert stock.latest_price is not None
                assert financial is not None
                assert effective_bps is not None
                assert roe is not None

                calc = FairValueCalculation(
                    growth_rate=growth_rate,
                    bps=effective_bps,
                    current_price=stock.latest_price,
                    roe=roe,
                    cost_of_capital=cost_of_capital,
                )

                # Fix C: fair_value が正のときのみ乖離率・評価を計算
                # ROE < 成長率 の場合 fair_pbr が負 → 適正株価が負になり乖離率は定義不能
                # Fix D: fair_value ≤ 0 でも「いかなる正の価格も割高」= very_expensive と断言
                if calc.fair_value > 0:
                    discount_rate_val: Decimal | None = calc.discount_rate
                    evaluation_zone_val: str | None = _get_evaluation_zone(calc.discount_rate)
                else:
                    discount_rate_val = None
                    evaluation_zone_val = "very_expensive"

                # min_discount フィルター（fair_value > 0 のときのみ適用）
                if min_discount is not None and (discount_rate_val is None or discount_rate_val < min_discount):
                    continue

                results.append(
                    ScreeningResult(
                        code=stock.code,
                        name=stock.name,
                        sector=stock.sector,
                        latest_price=stock.latest_price,
                        latest_price_date=str(stock.latest_price_date),
                        bps=effective_bps,
                        eps=financial.eps,
                        roe=roe,
                        fair_pbr=calc.fair_pbr,
                        fair_value=calc.fair_value,
                        discount_rate=discount_rate_val,
                        evaluation_zone=evaluation_zone_val,
                        current_pbr=current_pbr,
                        implied_growth_rate=implied_gr,
                        growth_rate_label=gr_label,
                        company_forecast_growth_rate=financial.company_forecast_growth_rate,
                        is_active=stock.is_active,
                        is_manual_financial=financial.is_manual,
                        eps_growth_yoy=gm.eps_growth_yoy,
                        eps_cagr_3y=gm.eps_cagr_3y,
                        roe_trend=gm.roe_trend,
                        revenue_growth_yoy=gm.revenue_growth_yoy,
                        op_income_growth_yoy=gm.op_income_growth_yoy,
                        sl_ratio=margin.sl_ratio if margin else None,
                        long_balance=margin.long_balance if margin else None,
                        short_balance=margin.short_balance if margin else None,
                        long_balance_change=margin.long_balance_change if margin else None,
                        long_balance_change_pct=mtm.long_balance_change_pct,
                        long_balance_trend=mtm.long_balance_trend,
                        price_position_52w=tm.price_position_52w,
                        near_52w_high=tm.near_52w_high,
                        distance_from_52w_high=tm.distance_from_52w_high,
                        volume_ratio_20d=tm.volume_ratio_20d,
                        ma_25_deviation=tm.ma_25_deviation,
                        momentum_signal=tm.momentum_signal,
                        avg_turnover_20d=tm.avg_turnover_20d,
                        liquidity_level=_get_liquidity_level(tm.avg_turnover_20d),
                        dividend_yield=dm.dividend_yield,
                        payout_ratio=dm.payout_ratio,
                        consecutive_dividend_years=dm.consecutive_dividend_years,
                        progressive_dividend_years=dm.progressive_dividend_years,
                        dividend_score=dm.dividend_score,
                        fcf=fm.fcf,
                        fcf_yield=fm.fcf_yield,
                        fcf_margin=fm.fcf_margin,
                        fcf_score=fm.fcf_score,
                        is_owner_managed=is_owner,
                        owner_ratio=_owner_ratio,
                        owner_match_type=_owner_type,
                        ma_golden_cross=tm.ma_golden_cross,
                        price_cross_ma25=tm.price_cross_ma25,
                        price_cross_ma75=tm.price_cross_ma75,
                        macd_golden_cross=tm.macd_golden_cross,
                        rsi_rebound=tm.rsi_rebound,
                        pullback_buy=tm.pullback_buy,
                    )
                )
            else:
                # 計算不可の場合：min_discount フィルターが指定されていれば除外
                if min_discount is not None:
                    continue

                reason = _get_not_calculable_reason(
                    can_calculate=can_calculate,
                    latest_price=stock.latest_price,
                    financial=financial,
                    bps=effective_bps,
                    roe=roe,
                    growth_rate=growth_rate,
                )
                results.append(
                    ScreeningResult(
                        code=stock.code,
                        name=stock.name,
                        sector=stock.sector,
                        latest_price=stock.latest_price,
                        latest_price_date=str(stock.latest_price_date) if stock.latest_price_date else None,
                        bps=effective_bps,
                        eps=financial.eps if financial else None,
                        roe=roe,
                        fair_pbr=None,
                        fair_value=None,
                        discount_rate=None,
                        evaluation_zone=None,
                        current_pbr=current_pbr,
                        implied_growth_rate=implied_gr,
                        growth_rate_label=gr_label,
                        company_forecast_growth_rate=financial.company_forecast_growth_rate if financial else None,
                        is_active=stock.is_active,
                        not_calculable_reason=reason,
                        is_manual_financial=financial.is_manual if financial else False,
                        eps_growth_yoy=gm.eps_growth_yoy,
                        eps_cagr_3y=gm.eps_cagr_3y,
                        roe_trend=gm.roe_trend,
                        revenue_growth_yoy=gm.revenue_growth_yoy,
                        op_income_growth_yoy=gm.op_income_growth_yoy,
                        sl_ratio=margin.sl_ratio if margin else None,
                        long_balance=margin.long_balance if margin else None,
                        short_balance=margin.short_balance if margin else None,
                        long_balance_change=margin.long_balance_change if margin else None,
                        long_balance_change_pct=mtm.long_balance_change_pct,
                        long_balance_trend=mtm.long_balance_trend,
                        price_position_52w=tm.price_position_52w,
                        near_52w_high=tm.near_52w_high,
                        distance_from_52w_high=tm.distance_from_52w_high,
                        volume_ratio_20d=tm.volume_ratio_20d,
                        ma_25_deviation=tm.ma_25_deviation,
                        momentum_signal=tm.momentum_signal,
                        avg_turnover_20d=tm.avg_turnover_20d,
                        liquidity_level=_get_liquidity_level(tm.avg_turnover_20d),
                        dividend_yield=dm.dividend_yield,
                        payout_ratio=dm.payout_ratio,
                        consecutive_dividend_years=dm.consecutive_dividend_years,
                        progressive_dividend_years=dm.progressive_dividend_years,
                        dividend_score=dm.dividend_score,
                        fcf=fm.fcf,
                        fcf_yield=fm.fcf_yield,
                        fcf_margin=fm.fcf_margin,
                        fcf_score=fm.fcf_score,
                        is_owner_managed=is_owner,
                        owner_ratio=_owner_ratio,
                        owner_match_type=_owner_type,
                        ma_golden_cross=tm.ma_golden_cross,
                        price_cross_ma25=tm.price_cross_ma25,
                        price_cross_ma75=tm.price_cross_ma75,
                        macd_golden_cross=tm.macd_golden_cross,
                        rsi_rebound=tm.rsi_rebound,
                        pullback_buy=tm.pullback_buy,
                    )
                )

        # discount_rate が None の銘柄は末尾へ
        results.sort(
            key=lambda r: (r.discount_rate is None, -(r.discount_rate or Decimal(0))),
        )
        calculable_count = sum(1 for r in results if r.discount_rate is not None)
        logger.info("スクリーニング完了: %d 銘柄（計算可能: %d 銘柄）", len(results), calculable_count)
        return results
