"""LLM Function Calling 用のツール定義サービス。

apps/mcp の ALL_TOOLS と同じツールを LLM Function Calling 用にも公開する。
OpenAI / Gemini の両形式に変換可能。

両 provider とも JSON Schema ベースだが、ラッパー構造が異なる:
- OpenAI: [{type: "function", function: {name, description, parameters}}, ...]
- Gemini: [{function_declarations: [{name, description, parameters}, ...]}]

USER_REQUIRED_TOOLS（保有情報系）は、未認証時に除外する。
本サービスは「認証済みユーザーかどうか」のフラグを受け取り、それに応じて返却する。

設計書: docs/design/multi-client-ai-chat.md §6.3
"""

from __future__ import annotations

from typing import Any

# Function Calling で公開するツール一覧。
# apps/mcp の ALL_TOOLS と同一になるよう保つ（test_tool_definition_service で検証）。
_AVAILABLE_TOOLS = (
    # 公開系（誰でも呼べる）
    "get_menu",
    "get_stock_summary",
    "get_stock_financials",
    "get_stock_risk_tags",
    "get_stock_opportunity_tags",
    "get_screening_candidates",
    "get_price_movers",
    "get_fx_analysis",
    "search_stock_news_sources",
    "search_ticker",
    "get_earnings_calendar",
    "get_margin_balance",
    "get_price_distribution_3m",
    # 認証必須系
    "get_my_holdings",
    "get_my_portfolio_summary",
    "get_my_watchlist",
    "get_my_pnl",
    "get_my_holdings_news",
    "get_my_margin_positions",
    "get_my_holdings_alerts",
    "get_my_dividends_calendar",
    "get_sell_candidates",
    "save_ai_decision",
)

# 認証が必須なツール（user_id が None の場合は除外する）
# apps/mcp の USER_REQUIRED_TOOLS と同期する。
_USER_REQUIRED_TOOLS = frozenset(
    {
        "get_my_holdings",
        "get_my_portfolio_summary",
        "get_my_watchlist",
        "get_my_pnl",
        "get_my_holdings_news",
        "get_my_margin_positions",
        "get_my_holdings_alerts",
        "get_my_dividends_calendar",
        "get_sell_candidates",
        "save_ai_decision",
    }
)

# provider 非依存の共通スキーマ。各ツールの definition は
# {description: str, parameters: JSON Schema} の形式で保持する。
_COMMON_SCHEMAS: dict[str, dict[str, Any]] = {
    "get_menu": {
        "description": (
            "会話メニュー (root → 中間 → 葉) を返す。対話の起点に使う。"
            "返却 options[].next_menu があれば再度 get_menu を呼び、"
            "next_tool があれば指定 MCP ツールを params で呼ぶ。"
            "display_markdown はそのままユーザーに見せること"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "level": {
                    "type": "string",
                    "description": (
                        "メニュー階層。既定 'root'。"
                        "'portfolio' / 'stock_analysis_kind' / 'pick_stock' / "
                        "'etf_analysis' / 'reit_analysis' / 'holdings_ops' 等"
                    ),
                },
                "context": {
                    "type": "string",
                    "description": (
                        "直前メニュー option の params を JSON 文字列で渡す "
                        '(例: \'{"then_tool":"get_stock_summary"}\')。葉の動的展開時に使う'
                    ),
                },
            },
            "required": [],
        },
    },
    "get_stock_summary": {
        "description": ("銘柄サマリ（価格・PBR・フェアバリュー・implied_growth・52週レンジ位置・配当）を返す"),
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "証券コード（例: '7203'）",
                },
            },
            "required": ["code"],
        },
    },
    "get_stock_financials": {
        "description": "過去 N 年分の財務データ（売上・営業利益・EPS・ROE・BPS・CF）を返す",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "証券コード",
                },
                "years": {
                    "type": "integer",
                    "description": "取得年数（既定 5、最大 20）",
                },
            },
            "required": ["code"],
        },
    },
    "get_stock_risk_tags": {
        "description": ("銘柄の注意タグ（信用過熱・流動性低・過大評価・適正値算出不可など）を返す"),
        "parameters": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "証券コード"},
            },
            "required": ["code"],
        },
    },
    "get_stock_opportunity_tags": {
        "description": ("銘柄の機会タグ（連続増配・52週下端・割安ゾーン・RSI 売られすぎなど）を返す"),
        "parameters": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "証券コード"},
            },
            "required": ["code"],
        },
    },
    "get_screening_candidates": {
        "description": (
            "Gordon Growth + モメンタムによる買い候補スクリーニング結果を返す。各種パラメータで絞り込み可能"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "growth_rate": {
                    "type": "string",
                    "description": "Gordon Growth の g（例 '0.02'。文字列で渡す）",
                },
                "max_pbr_ratio": {
                    "type": "string",
                    "description": "current_pbr ≤ fair_pbr × ratio の上限（例 '1.0'）",
                },
                "min_roe": {
                    "type": "string",
                    "description": "最小 ROE（例 '0.10' = 10%）",
                },
                "include_zones": {
                    "type": "string",
                    "description": ("カンマ区切りの評価ゾーン（例 'very_cheap,cheap,fair'）"),
                },
                "min_momentum_signal": {
                    "type": "string",
                    "description": "モメンタム下限（'bearish'/'neutral'/'bullish'）",
                },
                "limit": {
                    "type": "integer",
                    "description": "最大件数（既定 20）",
                },
                "market_type": {
                    "type": "string",
                    "description": "市場（'JP' / 'US'、既定 'JP'）",
                },
            },
            "required": [],
        },
    },
    "get_price_movers": {
        "description": "急騰急落ランキング（前日比・出来高比・ストップ高安）を返す",
        "parameters": {
            "type": "object",
            "properties": {
                "direction": {
                    "type": "string",
                    "description": "'gainers' / 'losers' / 'both'（既定 'both'）",
                },
                "scope": {
                    "type": "string",
                    "description": "'all' / 'my_watchlist' / 'my_holdings'（既定 'all'）",
                },
                "threshold_pct": {
                    "type": "string",
                    "description": "絶対値 % 以上のみ抽出（例 '5.0'）",
                },
                "limit": {
                    "type": "integer",
                    "description": "各方向の最大件数（既定 20）",
                },
            },
            "required": [],
        },
    },
    "get_fx_analysis": {
        "description": ("USD/JPY のフェアバリュー分析（金利差回帰・テクニカル・PPP）を返す"),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    "search_stock_news_sources": {
        "description": (
            "銘柄に関する信頼できるニュースソースの検索 URL リストを返す。"
            "返却された URL を別途参照して最新情報を取得すること"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "証券コード"},
                "query": {
                    "type": "string",
                    "description": "追加の検索キーワード（省略時は銘柄名）",
                },
            },
            "required": ["code"],
        },
    },
    "get_my_holdings": {
        "description": "ログイン中ユーザーの保有銘柄一覧と評価額を返す（要認証）",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    "get_my_portfolio_summary": {
        "description": (
            "ログイン中ユーザーのポートフォリオ集計を返す（要認証）。"
            "総資産・取得原価・含み損益・資産クラス別・口座別・家族メンバー別を含む"
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    # ────────────────────────────────────────────────────────────────
    # 公開系（追加分）
    # ────────────────────────────────────────────────────────────────
    "search_ticker": {
        "description": (
            "会社名・愛称・コード文字列から銘柄候補を検索する。"
            "「yutori」「トヨタ」のような曖昧な入力をした場合、"
            "まずこのツールで銘柄コードを解決してから get_stock_summary 等を呼ぶこと"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "検索文字列（会社名・愛称・コードなど。NFKC 正規化される）",
                },
                "instrument_type": {
                    "type": "string",
                    "description": "絞り込み: 'all' / 'stock' / 'etf' / 'reit' / 'other'（既定 'all'）",
                },
                "market_type": {
                    "type": "string",
                    "description": "市場（'JP' / 'US'、省略時は両方）",
                },
                "limit": {
                    "type": "integer",
                    "description": "最大件数（既定 10）",
                },
            },
            "required": ["query"],
        },
    },
    "get_earnings_calendar": {
        "description": "今後の決算予定を返す（J-Quants /equities/earnings-calendar）",
        "parameters": {
            "type": "object",
            "properties": {
                "codes": {
                    "type": "string",
                    "description": "カンマ区切りの証券コード（省略時は全銘柄）",
                },
                "days_ahead": {
                    "type": "integer",
                    "description": "何日先まで取得するか（既定 30）",
                },
            },
            "required": [],
        },
    },
    "get_margin_balance": {
        "description": "銘柄の信用残（買残・売残・信用倍率・直近 4 週履歴）を返す",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "証券コード"},
            },
            "required": ["code"],
        },
    },
    "get_price_distribution_3m": {
        "description": (
            "N 営業日後の株価分布予測 (Historical Bootstrap モンテカルロ)。"
            "過去 lookback_days 日の日次リターンを復元抽出してパス× simulation_runs 回試行し、"
            "パーセンタイル (p10/p25/p50/p75/p90) と現在価格・fair_value 超過確率を返す。"
            "注意: 過去リターンの繰り返しを前提とするためレジーム変化は捉えられない"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "証券コード"},
                "horizon_days": {
                    "type": "integer",
                    "description": "何営業日先か（既定 90 = 約 3 ヶ月）",
                },
                "simulation_runs": {
                    "type": "integer",
                    "description": "シミュレーション回数（既定 10,000）",
                },
                "lookback_days": {
                    "type": "integer",
                    "description": "過去何営業日のリターンを使うか（既定 252 = 1 年）",
                },
            },
            "required": ["code"],
        },
    },
    # ────────────────────────────────────────────────────────────────
    # 認証必須系（追加分）
    # ────────────────────────────────────────────────────────────────
    "get_my_watchlist": {
        "description": "ログイン中ユーザーのウォッチリスト銘柄一覧を返す（要認証）",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    "get_my_pnl": {
        "description": "ログイン中ユーザーの銘柄単位の含み損益を返す（要認証）",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "証券コードを指定すると該当銘柄のみに絞り込む（省略時は全銘柄）",
                },
            },
            "required": [],
        },
    },
    "get_my_holdings_news": {
        "description": ("ログイン中ユーザーの保有 + ウォッチ銘柄に紐づくニュースを返す（要認証）"),
        "parameters": {
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "直近 N 日（既定 7）",
                },
                "min_importance": {
                    "type": "string",
                    "description": "重要度スコアの下限（例 '0.5'。省略時は無条件）",
                },
                "limit": {
                    "type": "integer",
                    "description": "最大件数（既定 20）",
                },
            },
            "required": [],
        },
    },
    "get_my_margin_positions": {
        "description": (
            "ログイン中ユーザーの信用建玉一覧を返す（要認証）。"
            "各建玉について建玉日・期限残・累計金利・現引き必要資金を計算する"
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    "get_my_holdings_alerts": {
        "description": (
            "保有 + ウォッチ銘柄の集約アラートを返す（要認証）。"
            "ストップ高安・決算 3 日以内・信用期限 30 日以内・"
            "リスクタグ高深刻度・52週高値ブレイクアウト近い等"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "severity_min": {
                    "type": "string",
                    "description": "'low' / 'medium' / 'high'（既定 'low' = 全て返す）",
                },
            },
            "required": [],
        },
    },
    "get_my_dividends_calendar": {
        "description": (
            "保有銘柄の今後 N ヶ月の配当予定と受取予定額を返す（要認証）。"
            "ex_dividend_date / record_date / payable_date / "
            "dividend_per_share × quantity = expected_amount を返す"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "months_ahead": {
                    "type": "integer",
                    "description": "何ヶ月先まで見るか（既定 3）",
                },
            },
            "required": [],
        },
    },
    "get_sell_candidates": {
        "description": (
            "保有銘柄から売却候補を保守的判定（3 条件 AND）で抽出する（要認証）。"
            "判定: evaluation_zone == 'very_expensive' AND "
            "momentum_signal in (sell, caution) AND "
            "roe_trend == 'declining'"
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    "save_ai_decision": {
        "description": (
            "AI 投資判断 (buy/sell/hold/watch) と根拠を保存する（要認証）。"
            "保存時に get_stock_summary 結果を snapshot_indicators として"
            "同時に記録するため、後から判断時点の指標を振り返れる"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "証券コード"},
                "decision_type": {
                    "type": "string",
                    "description": "'buy' / 'sell' / 'hold' / 'watch'",
                },
                "rationale": {
                    "type": "string",
                    "description": "AI が生成した判断根拠（自由テキスト）",
                },
                "confidence": {
                    "type": "string",
                    "description": "確信度 '0.00'〜'1.00'（任意、文字列で渡す）",
                },
                "ai_model": {
                    "type": "string",
                    "description": "使用 AI モデル名（任意、例 'claude-4.7-opus'）",
                },
            },
            "required": ["code", "decision_type", "rationale"],
        },
    },
}


class ToolDefinitionService:
    """LLM Function Calling 用のツール定義を生成する。"""

    def build_tools_for_provider(
        self,
        provider: str,
        user_id: int | None,
    ) -> list[dict[str, Any]]:
        """provider に応じたツール定義配列を返す。

        Args:
            provider: "openai" / "openai_admin" / "gemini"
            user_id: ログインユーザー ID。None なら USER_REQUIRED_TOOLS を除外。

        Returns:
            provider 固有のラッパー構造に整形されたツール配列。
        """
        allowed_tools = self._filter_allowed_tools(user_id=user_id)

        if provider in ("openai", "openai_admin"):
            return [
                {
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": schema["description"],
                        "parameters": schema["parameters"],
                    },
                }
                for name, schema in allowed_tools
            ]

        if provider == "gemini":
            return [
                {
                    "function_declarations": [
                        {
                            "name": name,
                            "description": schema["description"],
                            "parameters": schema["parameters"],
                        }
                        for name, schema in allowed_tools
                    ]
                }
            ]

        raise ValueError(f"Unknown provider: {provider}")

    def list_available_tool_names(self) -> tuple[str, ...]:
        """公開する全ツール名（除外フィルタ前）。"""
        return _AVAILABLE_TOOLS

    def _filter_allowed_tools(self, user_id: int | None) -> list[tuple[str, dict[str, Any]]]:
        """user_id が None の場合 USER_REQUIRED_TOOLS を除外したリストを返す。

        順序は _AVAILABLE_TOOLS の定義順を保つ。
        """
        result: list[tuple[str, dict[str, Any]]] = []
        for name in _AVAILABLE_TOOLS:
            if user_id is None and name in _USER_REQUIRED_TOOLS:
                continue
            result.append((name, _COMMON_SCHEMAS[name]))
        return result
