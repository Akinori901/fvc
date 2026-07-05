"""会話型メニュー UseCase。

LLM クライアント (ChatGPT Custom GPT / Claude Desktop 等) に
階層メニューを返し、ユーザーを段階的に各ツール呼び出しへ誘導する。

中間ノード:  `options[].next_menu` で次の get_menu レベルを指示。
葉ノード:    `options[].next_tool` で既存 MCP ツール名と params を指示。
動的な葉:    `dynamic_source` で保有株一覧などを実行時に展開。
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, NotRequired, TypedDict

from apps.mcp.domain.exceptions import McpToolNotFoundError

if TYPE_CHECKING:
    from apps.mcp.application.usecases.tools.get_my_holdings_usecase import (
        GetMyHoldingsToolUseCase,
    )


class MenuOption(TypedDict, total=False):
    id: str
    label: str
    hint: str
    next_menu: str
    next_tool: str
    params: dict[str, Any]


class MenuDef(TypedDict, total=False):
    title: str
    options: list[MenuOption]
    dynamic_source: NotRequired[str]
    requires_auth: NotRequired[bool]


# 動的展開時に返す保有株一覧の最大件数 (これを超えたら "もっと見る" を末尾に追加)
_DYNAMIC_HOLDINGS_LIMIT = 30


MENU_DEFINITIONS: dict[str, MenuDef] = {
    "root": {
        "title": "何をしたいですか?",
        "options": [
            {
                "id": "portfolio",
                "label": "ポートフォリオ全体",
                "next_menu": "portfolio",
                "hint": "総資産・損益・資産クラス別",
            },
            {
                "id": "stock_analysis",
                "label": "個別株の分析",
                "next_menu": "stock_analysis_kind",
                "hint": "保有株または任意銘柄",
            },
            {
                "id": "etf_analysis",
                "label": "ETF の分析",
                "next_menu": "etf_analysis",
            },
            {
                "id": "reit_analysis",
                "label": "REIT の分析",
                "next_menu": "reit_analysis",
            },
            {
                "id": "fx_analysis",
                "label": "FX (USD/JPY) 分析",
                "next_tool": "get_fx_analysis",
                "params": {},
            },
            {
                "id": "holdings_ops",
                "label": "保有株の管理 (売却候補/アラート/損益)",
                "next_menu": "holdings_ops",
            },
            {
                "id": "screening",
                "label": "買い候補スクリーニング",
                "next_tool": "get_screening_candidates",
                "params": {},
            },
        ],
    },
    "portfolio": {
        "title": "ポートフォリオで何を見ますか?",
        "options": [
            {
                "id": "summary",
                "label": "総合サマリ (総資産・損益・資産クラス別)",
                "next_tool": "get_my_portfolio_summary",
                "params": {},
            },
            {
                "id": "holdings",
                "label": "保有銘柄一覧 (口座別)",
                "next_tool": "get_my_holdings",
                "params": {},
            },
            {
                "id": "dividends",
                "label": "今後 3 ヶ月の配当予定",
                "next_tool": "get_my_dividends_calendar",
                "params": {"months_ahead": 3},
            },
        ],
        "requires_auth": True,
    },
    "stock_analysis_kind": {
        "title": "個別株で何を知りたいですか?",
        "options": [
            {
                "id": "evaluation",
                "label": "今の評価 (適正株価とのギャップ)",
                "next_menu": "pick_stock",
                "params": {"then_tool": "get_stock_summary"},
            },
            {
                "id": "financials",
                "label": "過去 5 年の財務 (売上・営業利益・EPS・ROE)",
                "next_menu": "pick_stock",
                "params": {"then_tool": "get_stock_financials"},
            },
            {
                "id": "chart",
                "label": "3 ヶ月後の価格分布 (モンテカルロ)",
                "next_menu": "pick_stock",
                "params": {"then_tool": "get_price_distribution_3m"},
            },
            {
                "id": "risk",
                "label": "リスクタグ (信用過熱・流動性低・過大評価)",
                "next_menu": "pick_stock",
                "params": {"then_tool": "get_stock_risk_tags"},
            },
            {
                "id": "opportunity",
                "label": "機会タグ (連続増配・52w 下端・売られすぎ)",
                "next_menu": "pick_stock",
                "params": {"then_tool": "get_stock_opportunity_tags"},
            },
        ],
    },
    "pick_stock": {
        "title": "どの銘柄を分析しますか?",
        "options": [],  # 動的展開
        "dynamic_source": "holdings",
        "requires_auth": True,
    },
    "etf_analysis": {
        "title": "ETF の分析 - どう進めますか?",
        "options": [
            {
                "id": "search",
                "label": "ETF を名前/コードで検索",
                "next_tool": "search_ticker",
                "params": {"instrument_type": "etf"},
                "hint": "query にキーワードを入れて呼んでください",
            },
        ],
    },
    "reit_analysis": {
        "title": "REIT の分析 - どう進めますか?",
        "options": [
            {
                "id": "search",
                "label": "REIT を名前/コードで検索",
                "next_tool": "search_ticker",
                "params": {"instrument_type": "reit"},
                "hint": "query にキーワードを入れて呼んでください",
            },
        ],
    },
    "holdings_ops": {
        "title": "保有株の管理 - 何を見ますか?",
        "options": [
            {
                "id": "sell_candidates",
                "label": "売却候補 (保守的 3 条件 AND)",
                "next_tool": "get_sell_candidates",
                "params": {},
            },
            {
                "id": "alerts",
                "label": "アラート (決算近・信用期限近・ストップ高安 など)",
                "next_tool": "get_my_holdings_alerts",
                "params": {},
            },
            {
                "id": "pnl",
                "label": "銘柄単位の含み損益",
                "next_tool": "get_my_pnl",
                "params": {},
            },
            {
                "id": "news",
                "label": "保有 + ウォッチ銘柄のニュース",
                "next_tool": "get_my_holdings_news",
                "params": {},
            },
        ],
        "requires_auth": True,
    },
}


class GetMenuToolUseCase:
    """階層メニューを返す。葉では既存ツールへ橋渡し。"""

    def __init__(self, holdings_usecase: GetMyHoldingsToolUseCase) -> None:
        self._holdings_usecase = holdings_usecase

    def execute(
        self,
        *,
        level: str = "root",
        context: str | None = None,
        user_id: int | None = None,
    ) -> dict[str, Any]:
        if level not in MENU_DEFINITIONS:
            raise McpToolNotFoundError(f"未知のメニュー level: {level}")

        menu = MENU_DEFINITIONS[level]
        if menu.get("requires_auth") and user_id is None:
            raise PermissionError(f"メニュー '{level}' には認証が必要です")

        ctx = _parse_context(context)
        options: list[MenuOption] = list(menu["options"])

        if menu.get("dynamic_source") == "holdings":
            assert user_id is not None  # requires_auth で保証
            options = _build_holdings_options(
                holdings_usecase=self._holdings_usecase,
                user_id=user_id,
                then_tool=ctx.get("then_tool"),
            )

        return {
            "level": level,
            "title": menu["title"],
            "options": options,
            "display_markdown": _render_markdown(menu["title"], options),
        }


def _parse_context(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}
    if not isinstance(parsed, dict):
        return {}
    return parsed


def _build_holdings_options(
    *,
    holdings_usecase: GetMyHoldingsToolUseCase,
    user_id: int,
    then_tool: str | None,
) -> list[MenuOption]:
    """保有株一覧 (上位 N 件) + 末尾「その他 (検索)」を返す。

    same (code, name) は重複排除する。
    then_tool が指定されればそのツール呼び出しを各 option に組み込む。
    """
    holdings = holdings_usecase.execute(user_id=user_id).get("holdings", [])

    seen: set[str] = set()
    pairs: list[tuple[str, str]] = []
    for h in holdings:
        code = h.get("stock_code")
        if not code or h.get("asset_type") != "stock":
            continue
        if code in seen:
            continue
        seen.add(code)
        pairs.append((str(code), str(h.get("name", code))))

    truncated = pairs[:_DYNAMIC_HOLDINGS_LIMIT]
    options: list[MenuOption] = []
    for code, name in truncated:
        option: MenuOption = {
            "id": code,
            "label": f"{code} {name}",
        }
        if then_tool:
            option["next_tool"] = then_tool
            option["params"] = {"code": code}
        options.append(option)

    if len(pairs) > _DYNAMIC_HOLDINGS_LIMIT:
        options.append(
            {
                "id": "more",
                "label": f"その他 ({len(pairs) - _DYNAMIC_HOLDINGS_LIMIT} 件以上) — search_ticker で検索",
                "next_tool": "search_ticker",
                "params": {} if not then_tool else {"_then_tool": then_tool},
                "hint": "query にコードまたは銘柄名を入れて呼んでください",
            }
        )

    options.append(
        {
            "id": "other",
            "label": "保有外の銘柄 (コード入力)",
            "next_tool": "search_ticker",
            "params": {} if not then_tool else {"_then_tool": then_tool},
            "hint": "query に銘柄名/コード/愛称 (例: yutori, 7203, トヨタ) を入れてください",
        }
    )

    return options


def _render_markdown(title: str, options: list[MenuOption]) -> str:
    lines = [f"## {title}", ""]
    for i, opt in enumerate(options, start=1):
        label = opt.get("label", opt.get("id", ""))
        hint = opt.get("hint")
        if hint:
            lines.append(f"{i}. **{label}** — {hint}")
        else:
            lines.append(f"{i}. **{label}**")
    lines.append("")
    lines.append("番号または項目名で選択してください。")
    return "\n".join(lines)
