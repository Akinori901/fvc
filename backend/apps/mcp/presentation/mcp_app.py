"""MCP Streamable HTTP サーバ。

FastMCP インスタンスを定義し、23 個のツールを登録する。
Django ASGI ルートで `/mcp` 配下にマウントされる。

認証: `Authorization: Bearer fvc_mcp_xxxxx` ヘッダを各 HTTP リクエストで送る。
リクエストごとに認証 → user_id を context に保存 → ツール実行時に取り出す。
"""

from __future__ import annotations

import logging
from contextvars import ContextVar
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

logger = logging.getLogger(__name__)

# リクエストごとの user_id を保持する ContextVar
_current_user_id: ContextVar[int | None] = ContextVar("mcp_current_user_id", default=None)

# DNS rebinding 対策のホスト許可リスト
# - localhost:18000 / 8000: ローカル開発（ホスト / コンテナ内）
# - backend:8000: docker network 内（verify_mcp.py スクリプトから）
# - *.cloudfront.net: 本番（CloudFront）
# - 独自ドメイン取得時はここに追加
_ALLOWED_HOSTS = [
    "localhost:8000",
    "localhost:18000",
    "127.0.0.1:8000",
    "127.0.0.1:18000",
    "backend:8000",
    "d3dz1e2hexhvbr.cloudfront.net",
]

mcp_server = FastMCP(
    "fair-value-calculator",
    stateless_http=True,
    json_response=True,
    streamable_http_path="/",  # Starlette Mount("/mcp", ...) と組み合わせて /mcp で配信
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=_ALLOWED_HOSTS,
    ),
)


def set_current_user_id(user_id: int | None) -> None:
    """ASGI middleware から呼ぶ。リクエストごとの user_id を設定。"""
    _current_user_id.set(user_id)


async def _invoke(tool_name: str, params: dict[str, Any]) -> dict[str, Any]:
    """共通ディスパッチャ。

    Django ORM は同期なので、async コンテキストから安全に呼ぶために
    `sync_to_async(thread_sensitive=True)` でワーカースレッドに逃がす。
    `_current_user_id` ContextVar はスレッド間で引き継がれないので、
    sync 関数に明示的に渡す。
    """
    from asgiref.sync import sync_to_async

    from config import container

    user_id = _current_user_id.get()

    def _call_sync() -> dict[str, Any]:
        service = container.tool_invocation_service()
        return service.invoke(tool_name=tool_name, params=params, user_id=user_id)

    return await sync_to_async(_call_sync, thread_sensitive=True)()


# ─────────────────────────────────────────────────────────────
# ツール登録
# ─────────────────────────────────────────────────────────────


@mcp_server.tool()
async def get_menu(level: str = "root", context: str | None = None) -> dict[str, Any]:
    """会話メニュー (root → 中間 → 葉) を返す。対話の起点はこれを呼ぶ。

    LLM はこのツールを使ってユーザーに段階的な選択肢を提示する。
    各 option の `next_menu` があれば再度 get_menu を呼び、
    `next_tool` があればその MCP ツールを `params` で呼ぶ。
    返却 `display_markdown` をそのままユーザーに見せると最も自然に機能する。

    Args:
        level: メニュー階層。既定 "root"。"portfolio" / "stock_analysis_kind" /
               "pick_stock" / "etf_analysis" / "reit_analysis" / "holdings_ops" 等
        context: 直前メニュー option の params を JSON 文字列で渡す
                 (例: '{"then_tool":"get_stock_summary"}')。葉の動的展開時に使う
    """
    return await _invoke("get_menu", {"level": level, "context": context})


@mcp_server.tool()
async def get_stock_summary(code: str) -> dict[str, Any]:
    """銘柄サマリ（価格・PBR・フェアバリュー・implied_growth・52週レンジ位置・配当）を返す。

    Args:
        code: 証券コード（例: "7203"）
    """
    return await _invoke("get_stock_summary", {"code": code})


@mcp_server.tool()
async def get_stock_financials(code: str, years: int = 5) -> dict[str, Any]:
    """過去 N 年分の財務データ（売上・営業利益・EPS・ROE・BPS・CF）を返す。

    Args:
        code: 証券コード
        years: 取得年数（デフォルト 5）
    """
    return await _invoke("get_stock_financials", {"code": code, "years": years})


@mcp_server.tool()
async def get_my_holdings() -> dict[str, Any]:
    """ログイン中ユーザーの保有銘柄一覧と評価額を返す（要 API キー認証）。"""
    return await _invoke("get_my_holdings", {})


@mcp_server.tool()
async def get_my_watchlist() -> dict[str, Any]:
    """ログイン中ユーザーのウォッチリスト銘柄一覧を返す（要 API キー認証）。"""
    return await _invoke("get_my_watchlist", {})


@mcp_server.tool()
async def get_fx_analysis() -> dict[str, Any]:
    """USD/JPY のフェアバリュー分析（金利差回帰・テクニカル・PPP）を返す。"""
    return await _invoke("get_fx_analysis", {})


@mcp_server.tool()
async def get_earnings_calendar(codes: str | None = None, days_ahead: int = 30) -> dict[str, Any]:
    """今後の決算予定を返す（J-Quants /equities/earnings-calendar）。

    Args:
        codes: カンマ区切りの証券コード（省略時は全銘柄）
        days_ahead: 何日先まで取得するか（デフォルト 30）
    """
    return await _invoke("get_earnings_calendar", {"codes": codes, "days_ahead": days_ahead})


@mcp_server.tool()
async def search_ticker(
    query: str,
    instrument_type: str = "all",
    market_type: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """会社名・愛称・コード文字列から銘柄候補を検索する。

    ユーザーが「yutori」「トヨタ」のような曖昧な入力をした場合、
    まずこのツールで銘柄コードを解決してから get_stock_summary 等を呼ぶ。

    Args:
        query: 検索文字列（会社名・愛称・コードなど。NFKC 正規化される）
        instrument_type: "all"（既定）/ "stock" / "etf" / "reit" / "other"
        market_type: "JP" / "US" / None（既定、市場で絞らない）
        limit: 最大件数（1〜50、既定 10）
    """
    return await _invoke(
        "search_ticker",
        {
            "query": query,
            "instrument_type": instrument_type,
            "market_type": market_type,
            "limit": limit,
        },
    )


@mcp_server.tool()
async def search_stock_news_sources(code: str, query: str | None = None) -> dict[str, Any]:
    """銘柄に関する信頼できるニュースソースの検索 URL リストを返す。

    返却された URL を WebFetch で読み、最新情報を取得して分析に活用してください。

    Args:
        code: 証券コード
        query: 追加の検索キーワード（省略時は銘柄名）
    """
    return await _invoke("search_stock_news_sources", {"code": code, "query": query})


@mcp_server.tool()
async def get_my_portfolio_summary() -> dict[str, Any]:
    """ログイン中ユーザーのポートフォリオ集計を返す（要 API キー認証）。

    含む情報: 総資産・取得原価・含み損益・前日比（PR3 後対応）・資産クラス別・口座別・家族メンバー別。
    """
    return await _invoke("get_my_portfolio_summary", {})


@mcp_server.tool()
async def get_my_pnl(code: str | None = None) -> dict[str, Any]:
    """ログイン中ユーザーの銘柄単位の含み損益を返す（要 API キー認証）。

    Args:
        code: 証券コードを指定すると該当銘柄のみに絞り込む（省略時は全銘柄）
    """
    return await _invoke("get_my_pnl", {"code": code})


@mcp_server.tool()
async def get_margin_balance(code: str) -> dict[str, Any]:
    """銘柄の信用残（買残・売残・信用倍率・直近 4 週履歴）を返す。

    Args:
        code: 証券コード
    """
    return await _invoke("get_margin_balance", {"code": code})


@mcp_server.tool()
async def get_my_holdings_news(
    days: int = 7,
    min_importance: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """ログイン中ユーザーの保有 + ウォッチ銘柄に紐づくニュースを返す（要 API キー認証）。

    Args:
        days: 直近 N 日（デフォルト 7）
        min_importance: 重要度スコアの下限（例 "0.5"。省略時は無条件）
        limit: 最大件数（デフォルト 20）
    """
    return await _invoke(
        "get_my_holdings_news",
        {"days": days, "min_importance": min_importance, "limit": limit},
    )


@mcp_server.tool()
async def get_screening_candidates(
    growth_rate: str | None = None,
    max_pbr_ratio: str | None = None,
    min_roe: str | None = None,
    include_zones: str | None = None,
    min_momentum_signal: str | None = None,
    exclude_codes: str | None = None,
    limit: int = 20,
    market_type: str = "JP",
) -> dict[str, Any]:
    """買いたい銘柄候補を Gordon Growth ＋ モメンタムでスクリーニングして返す。

    Args:
        growth_rate: Gordon Growth の g（デフォルト "0.02"）
        max_pbr_ratio: current_pbr ≤ fair_pbr × ratio（例 "1.0"）
        min_roe: 最小 ROE（例 "0.10"）
        include_zones: カンマ区切りの評価ゾーン（例 "very_cheap,cheap,fair"）
        min_momentum_signal: モメンタム下限（例 "neutral"）
        exclude_codes: カンマ区切りの除外コード（保有銘柄スキップ用）
        limit: 最大件数（デフォルト 20）
        market_type: 市場（"JP" / "US"）
    """
    return await _invoke(
        "get_screening_candidates",
        {
            "growth_rate": growth_rate,
            "max_pbr_ratio": max_pbr_ratio,
            "min_roe": min_roe,
            "include_zones": include_zones,
            "min_momentum_signal": min_momentum_signal,
            "exclude_codes": exclude_codes,
            "limit": limit,
            "market_type": market_type,
        },
    )


@mcp_server.tool()
async def get_sell_candidates() -> dict[str, Any]:
    """保有銘柄から売却候補を保守的判定（3 条件 AND）で抽出する（要 API キー認証）。

    判定: evaluation_zone == "very_expensive" AND
          momentum_signal in (sell, caution) AND
          roe_trend == "declining"
    """
    return await _invoke("get_sell_candidates", {})


@mcp_server.tool()
async def get_stock_risk_tags(code: str) -> dict[str, Any]:
    """銘柄の注意タグ（信用過熱・流動性低・過大評価・適正値算出不可）を返す。

    Args:
        code: 証券コード
    """
    return await _invoke("get_stock_risk_tags", {"code": code})


@mcp_server.tool()
async def get_stock_opportunity_tags(code: str) -> dict[str, Any]:
    """銘柄の機会タグ（連続増配・52w 下端・割安ゾーン・RSI 売られすぎ）を返す。

    Args:
        code: 証券コード
    """
    return await _invoke("get_stock_opportunity_tags", {"code": code})


@mcp_server.tool()
async def get_price_movers(
    direction: str = "both",
    scope: str = "all",
    threshold_pct: str | None = None,
    min_volume_ratio: str | None = None,
    include_limit_hits: bool = True,
    limit: int = 20,
    date: str | None = None,
) -> dict[str, Any]:
    """急騰急落ランキングを返す（前日比・出来高比・ストップ高安）。

    Args:
        direction: "gainers" / "losers" / "both"（デフォルト both）
        scope: "all" / "my_watchlist" / "my_holdings"（後者 2 つは要 API キー認証）
        threshold_pct: 絶対値 % 以上のみ抽出（デフォルト "5.0"）
        min_volume_ratio: 出来高 20 日平均比の下限（例 "1.5"）
        include_limit_hits: ストップ高/安は閾値無視で含める（デフォルト true）
        limit: 各方向の最大件数（デフォルト 20）
        date: 集計日（YYYY-MM-DD、省略時は最新）
    """
    return await _invoke(
        "get_price_movers",
        {
            "direction": direction,
            "scope": scope,
            "threshold_pct": threshold_pct,
            "min_volume_ratio": min_volume_ratio,
            "include_limit_hits": include_limit_hits,
            "limit": limit,
            "date": date,
        },
    )


@mcp_server.tool()
async def get_my_margin_positions() -> dict[str, Any]:
    """ログイン中ユーザーの信用建玉一覧を返す（要 API キー認証）。

    各建玉について建玉日・期限残・累計金利・現引き必要資金を計算する。
    """
    return await _invoke("get_my_margin_positions", {})


@mcp_server.tool()
async def get_my_holdings_alerts(severity_min: str = "low") -> dict[str, Any]:
    """保有 + ウォッチ銘柄の集約アラートを返す（要 API キー認証）。

    アラート種別: stop_high_today / stop_low_today / earnings_within_3d /
    margin_expiry_within_30d / risk_tag_high_severity / near_52w_high_breakout

    Args:
        severity_min: "low" / "medium" / "high"（デフォルト low = 全て返す）
    """
    return await _invoke("get_my_holdings_alerts", {"severity_min": severity_min})


@mcp_server.tool()
async def get_my_dividends_calendar(months_ahead: int = 3) -> dict[str, Any]:
    """保有銘柄の今後 N ヶ月の配当予定と受取予定額を返す（要 API キー認証）。

    各保有銘柄について ex_dividend_date / record_date / payable_date /
    dividend_per_share × quantity = expected_amount を返す。

    データソースは t_dividends（J-Quants Premium または yfinance 由来）。
    record_date / payable_date は J-Quants Premium のみで充足。

    Args:
        months_ahead: 何ヶ月先まで見るか（デフォルト 3）
    """
    return await _invoke("get_my_dividends_calendar", {"months_ahead": months_ahead})


@mcp_server.tool()
async def save_ai_decision(
    code: str,
    decision_type: str,
    rationale: str,
    confidence: str | None = None,
    ai_model: str = "",
) -> dict[str, Any]:
    """AI 投資判断 (buy/sell/hold/watch) と根拠を保存する（要 API キー認証）。

    保存時に get_stock_summary 結果を snapshot_indicators として
    同時に記録するため、後から「判断時点の指標」を振り返れる。

    Args:
        code: 証券コード
        decision_type: "buy" / "sell" / "hold" / "watch"
        rationale: AI が生成した判断根拠（自由テキスト）
        confidence: 確信度 "0.00"〜"1.00"（任意）
        ai_model: 使用 AI モデル名（任意、例 "claude-4.5-sonnet"）
    """
    return await _invoke(
        "save_ai_decision",
        {
            "code": code,
            "decision_type": decision_type,
            "rationale": rationale,
            "confidence": confidence,
            "ai_model": ai_model,
        },
    )


@mcp_server.tool()
async def get_price_distribution_3m(
    code: str,
    horizon_days: int = 90,
    simulation_runs: int = 10000,
    lookback_days: int = 252,
    rng_seed: int | None = None,
) -> dict[str, Any]:
    """N 営業日後の株価分布予測 (Historical Bootstrap モンテカルロ)。

    過去 lookback_days 日の日次リターンを復元抽出してパス× simulation_runs 回試行。
    パーセンタイル (p10/p25/p50/p75/p90) と現在価格・fair_value 超過確率を返す。

    Args:
        code: 証券コード
        horizon_days: 何営業日先か（デフォルト 90 = 約 3 ヶ月）
        simulation_runs: シミュレーション回数（デフォルト 10,000）
        lookback_days: 過去何営業日のリターンを使うか（デフォルト 252 = 1 年）
        rng_seed: 乱数シード（テスト用、省略時は毎回ランダム）

    注意: 「過去リターンの繰り返し」を前提としたモデルのため
    レジーム変化・構造変化は捉えられない。
    """
    return await _invoke(
        "get_price_distribution_3m",
        {
            "code": code,
            "horizon_days": horizon_days,
            "simulation_runs": simulation_runs,
            "lookback_days": lookback_days,
            "rng_seed": rng_seed,
        },
    )
