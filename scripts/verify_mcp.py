#!/usr/bin/env python3
"""MCP サーバの動作検証スクリプト。

Claude Desktop と同じ MCP クライアント SDK で接続し、21 ツールの初期化・一覧・
代表的な呼び出しを試して PASS/FAIL を報告する。

使い方:
    # ローカル
    python scripts/verify_mcp.py --url http://localhost:18000/mcp/ --api-key fvc_mcp_xxx

    # 本番
    python scripts/verify_mcp.py --url https://d3dz1e2hexhvbr.cloudfront.net/mcp/ --api-key fvc_mcp_xxx

    # 環境変数経由
    export FVC_MCP_URL=http://localhost:18000/mcp/
    export FVC_MCP_API_KEY=fvc_mcp_xxx
    python scripts/verify_mcp.py

    # 特定のツールだけテスト
    python scripts/verify_mcp.py --only get_stock_summary,get_fx_analysis

    # Docker 経由（mcp SDK が backend 側にしか入っていない場合）
    docker compose exec backend uv run python /app/../scripts/verify_mcp.py \\
        --url http://host.docker.internal:18000/mcp/ --api-key fvc_mcp_xxx
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from dataclasses import dataclass
from typing import Any

# mcp SDK は backend の venv に入っているので、ホスト python では直接 import 不可。
# docker exec or backend コンテナ内 python で実行する想定。
try:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client
except ImportError:
    print(
        "ERROR: mcp Python SDK が見つかりません。\n"
        "  Docker 経由で実行してください:\n"
        "    docker compose exec backend uv run python /app/../scripts/verify_mcp.py ...\n"
        "  または: pip install 'mcp>=1.0,<2.0'",
        file=sys.stderr,
    )
    sys.exit(2)


# ---------------------------------------------------------------------------
# 検証対象ツール定義
# ---------------------------------------------------------------------------


@dataclass
class ToolCase:
    name: str
    args: dict[str, Any]
    expect_keys: tuple[str, ...]  # レスポンスに必ず含まれていてほしいキー


_CASES: list[ToolCase] = [
    ToolCase(
        name="get_stock_summary",
        args={"code": "7203"},
        expect_keys=("code", "name", "fair_value", "evaluation_zone"),
    ),
    ToolCase(
        name="get_stock_financials",
        args={"code": "7203", "years": 3},
        expect_keys=("code", "name", "years"),
    ),
    ToolCase(
        name="get_my_holdings",
        args={},
        expect_keys=("total_value", "holdings"),
    ),
    ToolCase(
        name="get_my_watchlist",
        args={},
        expect_keys=("count", "items"),
    ),
    ToolCase(
        name="get_fx_analysis",
        args={},
        expect_keys=("current_rate", "technicals"),
    ),
    ToolCase(
        name="get_earnings_calendar",
        args={"days_ahead": 14},
        expect_keys=("events",),
    ),
    ToolCase(
        name="search_stock_news_sources",
        args={"code": "7203"},
        expect_keys=("code", "stock_name", "sources"),
    ),
    ToolCase(
        name="get_my_portfolio_summary",
        args={},
        expect_keys=("total_value", "by_asset_class", "by_account"),
    ),
    ToolCase(
        name="get_my_pnl",
        args={},
        expect_keys=("as_of", "holdings"),
    ),
    ToolCase(
        name="get_margin_balance",
        args={"code": "7203"},
        expect_keys=("code", "buy_balance_shares", "history_last_4w"),
    ),
    ToolCase(
        name="get_my_holdings_news",
        args={"days": 7, "limit": 5},
        expect_keys=("count", "articles"),
    ),
    ToolCase(
        name="get_screening_candidates",
        args={"limit": 5},
        expect_keys=("count", "candidates", "filters_applied"),
    ),
    ToolCase(
        name="get_sell_candidates",
        args={},
        expect_keys=("count", "candidates", "judgment_criteria"),
    ),
    ToolCase(
        name="get_stock_risk_tags",
        args={"code": "7203"},
        expect_keys=("code", "name", "risk_tags"),
    ),
    ToolCase(
        name="get_stock_opportunity_tags",
        args={"code": "7203"},
        expect_keys=("code", "name", "opportunity_tags"),
    ),
    ToolCase(
        name="get_price_movers",
        args={"limit": 3},
        expect_keys=("as_of", "gainers", "losers"),
    ),
    ToolCase(
        name="get_my_margin_positions",
        args={},
        expect_keys=("count", "as_of", "positions"),
    ),
    ToolCase(
        name="get_my_holdings_alerts",
        args={"severity_min": "low"},
        expect_keys=("as_of", "alerts_count", "alerts"),
    ),
    ToolCase(
        name="get_my_dividends_calendar",
        args={"months_ahead": 3},
        expect_keys=("as_of", "upcoming", "total_expected_amount"),
    ),
    ToolCase(
        name="save_ai_decision",
        args={
            "code": "7203",
            "decision_type": "watch",
            "rationale": "verify_mcp による検証スクリプトからの自動保存。実投資判断ではありません。",
            "ai_model": "verify-script",
        },
        expect_keys=("id", "stock_code", "decision_type"),
    ),
    ToolCase(
        name="get_price_distribution_3m",
        args={"code": "7203", "simulation_runs": 500, "rng_seed": 42},
        expect_keys=("code", "model", "horizon_days"),
    ),
]


# ---------------------------------------------------------------------------
# 検証本体
# ---------------------------------------------------------------------------


class Result:
    def __init__(self) -> None:
        self.passed: list[str] = []
        self.failed: list[tuple[str, str]] = []
        self.skipped: list[str] = []

    def report(self) -> None:
        total = len(self.passed) + len(self.failed) + len(self.skipped)
        print()
        print("=" * 60)
        print(f"  PASS: {len(self.passed):3d}  /  FAIL: {len(self.failed):3d}  /  SKIP: {len(self.skipped):3d}   ({total} total)")
        print("=" * 60)
        if self.failed:
            print("\nFailures:")
            for name, msg in self.failed:
                print(f"  ✗ {name}: {msg}")

    @property
    def exit_code(self) -> int:
        return 1 if self.failed else 0


async def _verify(
    url: str,
    api_key: str,
    only: set[str] | None = None,
    timeout: float = 30.0,
) -> Result:
    result = Result()
    headers = {"Authorization": f"Bearer {api_key}"}

    print(f"\n→ Connecting to {url}")
    print(f"  Authorization: Bearer {api_key[:12]}...\n")

    try:
        async with streamablehttp_client(url, headers=headers, timeout=timeout) as streams:
            read_stream, write_stream, _ = streams
            async with ClientSession(read_stream, write_stream) as session:
                # initialize
                init = await session.initialize()
                server_name = init.serverInfo.name
                proto_version = init.protocolVersion
                print(f"  ✓ initialize: {server_name} (protocol {proto_version})")
                result.passed.append("initialize")

                # tools/list
                tools_resp = await session.list_tools()
                tool_names = [t.name for t in tools_resp.tools]
                print(f"  ✓ tools/list: {len(tool_names)} tools — {', '.join(tool_names)}")
                result.passed.append("tools/list")

                # 各ツール呼び出し
                for case in _CASES:
                    if only is not None and case.name not in only:
                        result.skipped.append(case.name)
                        continue
                    if case.name not in tool_names:
                        result.failed.append((case.name, "ツール一覧に含まれていません"))
                        continue
                    try:
                        call = await session.call_tool(case.name, case.args)
                    except Exception as exc:  # noqa: BLE001
                        result.failed.append((case.name, f"呼び出しエラー: {exc!r}"))
                        print(f"  ✗ {case.name}: {exc!r}")
                        continue

                    payload = _extract_payload(call)
                    missing = [k for k in case.expect_keys if k not in payload]
                    if missing:
                        result.failed.append((case.name, f"必須キー欠落: {missing}"))
                        print(f"  ✗ {case.name}: 必須キー欠落 {missing}")
                    else:
                        result.passed.append(case.name)
                        # 主要フィールドだけ抜粋表示
                        preview = {k: payload.get(k) for k in case.expect_keys[:2]}
                        print(f"  ✓ {case.name}: {json.dumps(preview, ensure_ascii=False, default=str)[:120]}")

    except Exception as exc:  # noqa: BLE001
        result.failed.append(("connect", f"接続エラー: {exc!r}"))
        print(f"\n  ✗ 接続エラー: {exc!r}", file=sys.stderr)

    return result


def _extract_payload(call_result: Any) -> dict[str, Any]:
    """CallToolResult から structuredContent or content[0].text(json) を取り出す。"""
    if call_result.isError:
        raise RuntimeError(f"tool returned error: {call_result.content}")

    # 1) structuredContent（FastMCP の dict 出力）
    structured = getattr(call_result, "structuredContent", None)
    if structured:
        # structuredContent は {"result": <dict>} でラップされている場合がある
        if isinstance(structured, dict) and set(structured.keys()) == {"result"}:
            return structured["result"]
        return structured  # type: ignore[no-any-return]

    # 2) content[0].text を JSON パース
    for block in call_result.content:
        text = getattr(block, "text", None)
        if text:
            try:
                parsed = json.loads(text)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                pass
    return {}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description="MCP サーバの 21 ツールを順に検証する")
    parser.add_argument(
        "--url",
        default=os.environ.get("FVC_MCP_URL"),
        help="MCP エンドポイント URL（例: http://localhost:18000/mcp/、末尾スラッシュ必須）",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("FVC_MCP_API_KEY"),
        help="MCP API キー（fvc_mcp_xxx）",
    )
    parser.add_argument(
        "--only",
        default=None,
        help="特定のツールだけ検証（カンマ区切り）",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="HTTP タイムアウト秒（デフォルト 30）",
    )

    args = parser.parse_args()

    if not args.url:
        print("ERROR: --url または環境変数 FVC_MCP_URL が必要", file=sys.stderr)
        return 2
    if not args.api_key:
        print("ERROR: --api-key または環境変数 FVC_MCP_API_KEY が必要", file=sys.stderr)
        return 2
    if not args.url.endswith("/"):
        print(
            f"WARN: URL に末尾スラッシュが無いと 404 になる場合があります。'{args.url}/' を試します。",
            file=sys.stderr,
        )
        args.url = args.url + "/"

    only_set: set[str] | None = None
    if args.only:
        only_set = {x.strip() for x in args.only.split(",") if x.strip()}

    result = asyncio.run(_verify(args.url, args.api_key, only=only_set, timeout=args.timeout))
    result.report()
    return result.exit_code


if __name__ == "__main__":
    sys.exit(main())
