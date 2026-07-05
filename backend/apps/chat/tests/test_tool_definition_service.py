"""ToolDefinitionService のテスト。

主な検証観点:
1. Phase 1 ツール 10 個全てに共通スキーマが定義されている
2. OpenAI / Gemini のラッパー形式が正しい
3. user_id=None で USER_REQUIRED_TOOLS が除外される
4. apps/mcp の ALL_TOOLS と Phase 1 ツール名が一致する（タイポ検出）
"""

from __future__ import annotations

import pytest

from apps.chat.application.services.tool_definition_service import (
    ToolDefinitionService,
)
from apps.mcp.application.services.tool_invocation_service import ALL_TOOLS


class TestToolDefinitionServiceAvailableCoverage:
    """Function Calling で公開する全ツールに定義があることを保証。"""

    def test_all_available_tools_have_schema_for_openai(self) -> None:
        service = ToolDefinitionService()
        tools = service.build_tools_for_provider(provider="openai", user_id=42)
        names = {t["function"]["name"] for t in tools}
        assert names == set(service.list_available_tool_names())

    def test_available_tool_count_matches_mcp_all_tools(self) -> None:
        """MCP ALL_TOOLS と公開ツール数が一致する。乖離した場合は CI で検出する。"""
        service = ToolDefinitionService()
        assert set(service.list_available_tool_names()) == set(ALL_TOOLS), (
            "tool_definition_service の _AVAILABLE_TOOLS と apps/mcp の ALL_TOOLS が乖離。"
            "ツールを追加/削除した際は両方を同期させる必要があります。"
        )


class TestToolDefinitionServiceProviderFormats:
    def test_openai_format_has_function_wrapper(self) -> None:
        service = ToolDefinitionService()
        tools = service.build_tools_for_provider(provider="openai", user_id=1)
        for tool in tools:
            assert tool["type"] == "function"
            assert "name" in tool["function"]
            assert "description" in tool["function"]
            assert "parameters" in tool["function"]
            assert tool["function"]["parameters"]["type"] == "object"

    def test_openai_admin_uses_same_format_as_openai(self) -> None:
        service = ToolDefinitionService()
        openai_tools = service.build_tools_for_provider(provider="openai", user_id=1)
        admin_tools = service.build_tools_for_provider(provider="openai_admin", user_id=1)
        assert openai_tools == admin_tools

    def test_gemini_format_uses_function_declarations(self) -> None:
        service = ToolDefinitionService()
        tools = service.build_tools_for_provider(provider="gemini", user_id=1)
        # Gemini は配列要素 1 個に function_declarations をまとめる
        assert len(tools) == 1
        decls = tools[0]["function_declarations"]
        assert len(decls) == len(service.list_available_tool_names())
        for d in decls:
            assert "name" in d
            assert "description" in d
            assert "parameters" in d

    def test_unknown_provider_raises(self) -> None:
        service = ToolDefinitionService()
        with pytest.raises(ValueError, match="Unknown provider"):
            service.build_tools_for_provider(provider="anthropic", user_id=1)


class TestToolDefinitionServiceUserRequiredFilter:
    def test_anonymous_user_excludes_my_holdings(self) -> None:
        """user_id=None なら保有情報系ツールは含まれない（公開公開コンテキスト）。"""
        service = ToolDefinitionService()
        tools = service.build_tools_for_provider(provider="openai", user_id=None)
        names = {t["function"]["name"] for t in tools}
        assert "get_my_holdings" not in names
        assert "get_my_portfolio_summary" not in names
        # 公開ツールは残る
        assert "get_stock_summary" in names
        assert "get_fx_analysis" in names

    def test_authenticated_user_includes_holdings_tools(self) -> None:
        service = ToolDefinitionService()
        tools = service.build_tools_for_provider(provider="openai", user_id=42)
        names = {t["function"]["name"] for t in tools}
        assert "get_my_holdings" in names
        assert "get_my_portfolio_summary" in names

    def test_anonymous_gemini_also_excluded(self) -> None:
        service = ToolDefinitionService()
        tools = service.build_tools_for_provider(provider="gemini", user_id=None)
        names = {d["name"] for d in tools[0]["function_declarations"]}
        assert "get_my_holdings" not in names


class TestToolDefinitionServiceMcpConsistency:
    """公開ツール名と MCP ALL_TOOLS の整合性を保証する。

    リネームやタイポを検出するためのガード。乖離した場合は CI で fail させる。
    """

    def test_all_available_names_exist_in_mcp_all_tools(self) -> None:
        service = ToolDefinitionService()
        for name in service.list_available_tool_names():
            assert name in ALL_TOOLS, f"Tool '{name}' not in MCP ALL_TOOLS (renamed?)"


class TestToolDefinitionServiceSchemaQuality:
    """各ツールスキーマの品質を保証。"""

    def test_required_fields_are_subset_of_properties(self) -> None:
        service = ToolDefinitionService()
        tools = service.build_tools_for_provider(provider="openai", user_id=1)
        for tool in tools:
            params = tool["function"]["parameters"]
            properties = set(params.get("properties", {}).keys())
            required = set(params.get("required", []))
            assert required.issubset(properties), (
                f"{tool['function']['name']}: required={required} not subset of properties={properties}"
            )

    def test_all_properties_have_type_and_description(self) -> None:
        service = ToolDefinitionService()
        tools = service.build_tools_for_provider(provider="openai", user_id=1)
        for tool in tools:
            name = tool["function"]["name"]
            properties = tool["function"]["parameters"].get("properties", {})
            for prop_name, prop_schema in properties.items():
                assert "type" in prop_schema, f"{name}.{prop_name}: missing 'type'"
                assert "description" in prop_schema, f"{name}.{prop_name}: missing 'description'"
