"""DI Container — 依存関係の解決を一元管理するファクトリ関数群。

全てのファクトリ関数はローカルインポートを使用し、循環参照を回避する。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.ai.application.usecases.analyze_stock_usecase import AnalyzeStockUseCase
    from apps.ai.application.usecases.get_ai_config_usecase import GetAiConfigUseCase
    from apps.ai.application.usecases.save_ai_config_usecase import SaveAiConfigUseCase
    from apps.ai.infrastructure.repositories.django_ai_repositories import (
        DjangoAiAnalysisLogRepository,
        DjangoAiConfigRepository,
        DjangoAiDecisionRepository,
    )
    from apps.auth_cognito.application.services.admin_user_create_service import (
        AdminUserCreateService,
    )
    from apps.auth_cognito.application.services.admin_user_lifecycle_service import (
        AdminUserLifecycleService,
    )
    from apps.auth_cognito.application.services.admin_user_query_service import (
        AdminUserQueryService,
    )
    from apps.auth_cognito.application.services.allowed_email_service import (
        AllowedEmailService,
    )
    from apps.auth_cognito.application.services.cognito_invite_service import (
        CognitoInviteService,
    )
    from apps.auth_cognito.application.services.cognito_jwt_verifier_service import (
        CognitoJwtVerifierService,
    )
    from apps.auth_cognito.application.services.cognito_link_admin_service import (
        CognitoLinkAdminService,
    )
    from apps.auth_cognito.application.services.cognito_user_pool_admin_service import (
        CognitoUserPoolAdminService,
    )
    from apps.auth_cognito.application.services.jit_provision_service import (
        JitProvisionService,
    )
    from apps.auth_cognito.application.services.jwks_cache_service import (
        JwksCacheService,
    )
    from apps.auth_cognito.application.usecases.add_allowed_email_usecase import (
        AddAllowedEmailUseCase,
    )
    from apps.auth_cognito.application.usecases.create_admin_user_usecase import (
        CreateAdminUserUseCase,
    )
    from apps.auth_cognito.application.usecases.delete_admin_user_usecase import (
        DeleteAdminUserUseCase,
    )
    from apps.auth_cognito.application.usecases.delete_cognito_link_usecase import (
        DeleteCognitoLinkUseCase,
    )
    from apps.auth_cognito.application.usecases.delete_cognito_user_usecase import (
        DeleteCognitoUserUseCase,
    )
    from apps.auth_cognito.application.usecases.disable_admin_user_usecase import (
        DisableAdminUserUseCase,
    )
    from apps.auth_cognito.application.usecases.disable_cognito_user_usecase import (
        DisableCognitoUserUseCase,
    )
    from apps.auth_cognito.application.usecases.enable_admin_user_usecase import (
        EnableAdminUserUseCase,
    )
    from apps.auth_cognito.application.usecases.enable_cognito_user_usecase import (
        EnableCognitoUserUseCase,
    )
    from apps.auth_cognito.application.usecases.list_admin_users_usecase import (
        ListAdminUsersUseCase,
    )
    from apps.auth_cognito.application.usecases.list_cognito_users_usecase import (
        ListCognitoUsersUseCase,
    )
    from apps.auth_cognito.application.usecases.remove_allowed_email_usecase import (
        RemoveAllowedEmailUseCase,
    )
    from apps.auth_cognito.infrastructure.repositories.boto3_cognito_userpool_repository import (
        Boto3CognitoUserPoolRepository,
    )
    from apps.auth_cognito.infrastructure.repositories.django_cognito_repositories import (
        DjangoCognitoLinkRepository,
        DjangoUserAllowedEmailRepository,
    )
    from apps.chat.application.services.chat_orchestration_service import (
        ChatOrchestrationService,
    )
    from apps.chat.application.services.daily_limit_service import DailyLimitService
    from apps.chat.application.services.llm_client_factory_service import (
        LlmClientFactoryService,
    )
    from apps.chat.application.services.tool_definition_service import (
        ToolDefinitionService,
    )
    from apps.chat.application.usecases.delete_chat_session_usecase import (
        DeleteChatSessionUseCase,
    )
    from apps.chat.application.usecases.get_chat_status_usecase import (
        GetChatStatusUseCase,
    )
    from apps.chat.application.usecases.list_chat_messages_usecase import (
        ListChatMessagesUseCase,
    )
    from apps.chat.application.usecases.list_chat_sessions_usecase import (
        ListChatSessionsUseCase,
    )
    from apps.chat.application.usecases.send_chat_message_usecase import (
        SendChatMessageUseCase,
    )
    from apps.chat.infrastructure.repositories.django_chat_repositories import (
        DjangoChatMessageRepository,
        DjangoChatSessionRepository,
    )
    from apps.fx.application.services.fred_client_service import FredClientService
    from apps.fx.application.services.fx_analysis_service import FxAnalysisService
    from apps.fx.application.services.fx_data_sync_service import FxDataSyncService
    from apps.fx.application.usecases.get_fx_analysis_usecase import GetFxAnalysisUseCase
    from apps.fx.application.usecases.sync_fx_data_usecase import SyncFxDataUseCase
    from apps.fx.infrastructure.repositories import (
        DjangoFxRateRepository,
        DjangoInterestRateRepository,
        DjangoMacroIndicatorRepository,
    )
    from apps.goals.application.usecases.delete_goal_usecase import DeleteGoalUseCase
    from apps.goals.application.usecases.get_goal_progress_usecase import GetGoalProgressUseCase
    from apps.goals.application.usecases.list_goals_usecase import ListGoalsUseCase
    from apps.goals.application.usecases.reorder_goals_usecase import ReorderGoalsUseCase
    from apps.goals.application.usecases.save_goal_usecase import SaveGoalUseCase
    from apps.goals.infrastructure.repositories import DjangoFinancialGoalRepository
    from apps.industry_metrics.infrastructure.repositories import (
        DjangoIndustryMetricsRepository,
    )
    from apps.mcp.application.services.api_key_generator_service import ApiKeyGeneratorService
    from apps.mcp.application.services.news_source_url_builder_service import NewsSourceUrlBuilderService
    from apps.mcp.application.services.tool_invocation_service import ToolInvocationService
    from apps.mcp.application.usecases.authenticate_api_key_usecase import AuthenticateApiKeyUseCase
    from apps.mcp.application.usecases.issue_api_key_usecase import IssueApiKeyUseCase
    from apps.mcp.application.usecases.list_api_keys_usecase import ListApiKeysUseCase
    from apps.mcp.application.usecases.revoke_api_key_usecase import RevokeApiKeyUseCase
    from apps.mcp.application.usecases.tools.get_earnings_calendar_usecase import (
        GetEarningsCalendarToolUseCase,
    )
    from apps.mcp.application.usecases.tools.get_fx_analysis_tool_usecase import GetFxAnalysisToolUseCase
    from apps.mcp.application.usecases.tools.get_margin_balance_usecase import GetMarginBalanceToolUseCase
    from apps.mcp.application.usecases.tools.get_menu_usecase import GetMenuToolUseCase
    from apps.mcp.application.usecases.tools.get_my_dividends_calendar_usecase import (
        GetMyDividendsCalendarToolUseCase,
    )
    from apps.mcp.application.usecases.tools.get_my_holdings_alerts_usecase import (
        GetMyHoldingsAlertsToolUseCase,
    )
    from apps.mcp.application.usecases.tools.get_my_holdings_news_usecase import GetMyHoldingsNewsToolUseCase
    from apps.mcp.application.usecases.tools.get_my_holdings_usecase import GetMyHoldingsToolUseCase
    from apps.mcp.application.usecases.tools.get_my_margin_positions_usecase import (
        GetMyMarginPositionsToolUseCase,
    )
    from apps.mcp.application.usecases.tools.get_my_pnl_usecase import GetMyPnlToolUseCase
    from apps.mcp.application.usecases.tools.get_my_portfolio_summary_usecase import (
        GetMyPortfolioSummaryToolUseCase,
    )
    from apps.mcp.application.usecases.tools.get_my_watchlist_usecase import GetMyWatchlistToolUseCase
    from apps.mcp.application.usecases.tools.get_price_distribution_3m_usecase import (
        GetPriceDistribution3mToolUseCase,
    )
    from apps.mcp.application.usecases.tools.get_price_movers_usecase import GetPriceMoversToolUseCase
    from apps.mcp.application.usecases.tools.get_screening_candidates_usecase import (
        GetScreeningCandidatesToolUseCase,
    )
    from apps.mcp.application.usecases.tools.get_sell_candidates_usecase import GetSellCandidatesToolUseCase
    from apps.mcp.application.usecases.tools.get_stock_financials_usecase import GetStockFinancialsToolUseCase
    from apps.mcp.application.usecases.tools.get_stock_opportunity_tags_usecase import (
        GetStockOpportunityTagsToolUseCase,
    )
    from apps.mcp.application.usecases.tools.get_stock_risk_tags_usecase import GetStockRiskTagsToolUseCase
    from apps.mcp.application.usecases.tools.get_stock_summary_usecase import GetStockSummaryToolUseCase
    from apps.mcp.application.usecases.tools.save_ai_decision_usecase import SaveAiDecisionToolUseCase
    from apps.mcp.application.usecases.tools.search_stock_news_sources_usecase import (
        SearchStockNewsSourcesToolUseCase,
    )
    from apps.mcp.application.usecases.tools.search_ticker_usecase import SearchTickerToolUseCase
    from apps.mcp.infrastructure.repositories import DjangoMcpApiKeyRepository
    from apps.news.application.services.google_news_rss_client_service import GoogleNewsRssClientService
    from apps.news.application.services.news_importance_service import NewsImportanceService
    from apps.news.application.services.news_matching_service import NewsMatchingService
    from apps.news.application.services.news_sync_service import NewsSyncService
    from apps.news.application.usecases.list_news_usecase import ListNewsUseCase
    from apps.news.application.usecases.list_stock_news_usecase import ListStockNewsUseCase
    from apps.news.application.usecases.sync_news_usecase import SyncNewsUseCase
    from apps.news.infrastructure.repositories import (
        DjangoNewsAiAnalysisRepository,
        DjangoNewsArticleRepository,
        DjangoNewsKeywordRepository,
        DjangoNewsStockLinkRepository,
    )
    from apps.paper_trading.application.services.paper_trading_service import PaperTradingService
    from apps.paper_trading.application.usecases.execute_trade_usecase import ExecuteTradeUseCase
    from apps.paper_trading.application.usecases.get_trade_history_usecase import GetTradeHistoryUseCase
    from apps.paper_trading.application.usecases.list_positions_usecase import ListPositionsUseCase
    from apps.paper_trading.application.usecases.reset_paper_trading_usecase import ResetPaperTradingUseCase
    from apps.paper_trading.infrastructure.repositories import (
        DjangoPaperPositionRepository,
        DjangoPaperTradeRepository,
    )
    from apps.portfolios.application.services.dynamic_valuation_service import (
        DynamicPortfolioValuationService,
    )
    from apps.portfolios.application.usecases.simulation_usecase import PortfolioSimulationUseCase
    from apps.stocks.application.services.dividend_sync_service import DividendSyncService
    from apps.stocks.application.services.financial_sync_service import FinancialSyncService
    from apps.stocks.application.services.market_data_provider_resolver import MarketDataProviderResolver
    from apps.stocks.application.services.price_sync_service import PriceSyncService
    from apps.stocks.application.services.stock_sync_service import StockSyncService
    from apps.stocks.application.usecases.compute_daily_movers_usecase import (
        ComputeDailyMoversUseCase,
    )
    from apps.stocks.application.usecases.etf_screening_usecase import EtfScreeningUseCase
    from apps.stocks.application.usecases.get_stock_technicals_usecase import GetStockTechnicalsUseCase
    from apps.stocks.application.usecases.recommendation_usecase import RecommendationUseCase
    from apps.stocks.application.usecases.reit_screening_usecase import ReitScreeningUseCase
    from apps.stocks.application.usecases.screening_preset_usecase import (
        DeleteScreeningPresetUseCase,
        ListScreeningPresetsUseCase,
        SaveScreeningPresetUseCase,
    )
    from apps.stocks.application.usecases.screening_usecase import ScreeningUseCase
    from apps.stocks.application.usecases.sync_market_data_usecase import SyncMarketDataUseCase
    from apps.stocks.application.usecases.sync_shareholders_usecase import SyncShareholdersUseCase
    from apps.stocks.domain.repositories import MarketDataProvider
    from apps.stocks.infrastructure.repositories import (
        DjangoApiConfigRepository,
        DjangoDailyMoversRepository,
        DjangoDividendRepository,
        DjangoFinancialRepository,
        DjangoMarginRepository,
        DjangoOwnerShareholderRepository,
        DjangoPriceRepository,
        DjangoScreeningPresetRepository,
        DjangoShareholderRawRepository,
        DjangoStockRepository,
        DjangoSyncLogRepository,
    )


# ============================================================
# Repository
# ============================================================


def stock_repository() -> DjangoStockRepository:
    from apps.stocks.infrastructure.repositories import DjangoStockRepository

    return DjangoStockRepository()


def financial_repository() -> DjangoFinancialRepository:
    from apps.stocks.infrastructure.repositories import DjangoFinancialRepository

    return DjangoFinancialRepository()


def price_repository() -> DjangoPriceRepository:
    from apps.stocks.infrastructure.repositories import DjangoPriceRepository

    return DjangoPriceRepository()


def dividend_repository() -> DjangoDividendRepository:
    from apps.stocks.infrastructure.repositories import DjangoDividendRepository

    return DjangoDividendRepository()


def margin_repository() -> DjangoMarginRepository:
    from apps.stocks.infrastructure.repositories import DjangoMarginRepository

    return DjangoMarginRepository()


def daily_movers_repository() -> DjangoDailyMoversRepository:
    from apps.stocks.infrastructure.repositories import DjangoDailyMoversRepository

    return DjangoDailyMoversRepository()


def api_config_repository() -> DjangoApiConfigRepository:
    from apps.stocks.infrastructure.repositories import DjangoApiConfigRepository

    return DjangoApiConfigRepository()


def sync_log_repository() -> DjangoSyncLogRepository:
    from apps.stocks.infrastructure.repositories import DjangoSyncLogRepository

    return DjangoSyncLogRepository()


def owner_shareholder_repository() -> DjangoOwnerShareholderRepository:
    from apps.stocks.infrastructure.repositories import DjangoOwnerShareholderRepository

    return DjangoOwnerShareholderRepository()


def screening_preset_repository() -> DjangoScreeningPresetRepository:
    from apps.stocks.infrastructure.repositories import DjangoScreeningPresetRepository

    return DjangoScreeningPresetRepository()


def shareholder_raw_repository() -> DjangoShareholderRawRepository:
    from apps.stocks.infrastructure.repositories import DjangoShareholderRawRepository

    return DjangoShareholderRawRepository()


def industry_metrics_repository() -> DjangoIndustryMetricsRepository:
    from apps.industry_metrics.infrastructure.repositories import DjangoIndustryMetricsRepository

    return DjangoIndustryMetricsRepository()


# ============================================================
# External Provider Factory
# ============================================================


def _jquants_factory(api_key: str, plan: str = "standard") -> MarketDataProvider:
    from apps.stocks.infrastructure.external.jquants_client import JQuantsClient

    return JQuantsClient(api_key=api_key, plan=plan)


def _jquants_factory_with_plan(api_key: str) -> MarketDataProvider:
    """API設定からプランを読んで JQuantsClient を生成するファクトリ。"""
    from apps.stocks.infrastructure.repositories import DjangoApiConfigRepository

    config = DjangoApiConfigRepository().find_by_provider("jquants")
    plan = config.plan if config else "standard"
    return _jquants_factory(api_key=api_key, plan=plan)


def _yfinance_factory() -> MarketDataProvider:
    from apps.stocks.infrastructure.external.yfinance_client import YfinanceClient

    return YfinanceClient()


# ============================================================
# Service
# ============================================================


def jquants_provider(market_type: str = "JP") -> MarketDataProvider:
    """J-Quants プロバイダーを直接取得する（管理コマンド用）。"""
    from apps.stocks.infrastructure.repositories import DjangoApiConfigRepository

    config = DjangoApiConfigRepository().find_by_provider("jquants")
    if config is None or not config.is_enabled or not config.api_key:
        raise RuntimeError("J-Quants API が設定されていません（m_api_configs を確認してください）")
    return _jquants_factory_with_plan(api_key=config.api_key)


def market_data_provider_resolver() -> MarketDataProviderResolver:
    from apps.stocks.application.services.market_data_provider_resolver import MarketDataProviderResolver

    return MarketDataProviderResolver(
        api_config_repo=api_config_repository(),
        jquants_factory=_jquants_factory_with_plan,
        yfinance_factory=_yfinance_factory,
    )


def stock_sync_service() -> StockSyncService:
    from apps.stocks.application.services.stock_sync_service import StockSyncService

    return StockSyncService(stock_repo=stock_repository())


def financial_sync_service() -> FinancialSyncService:
    from apps.stocks.application.services.financial_sync_service import FinancialSyncService

    return FinancialSyncService(
        stock_repo=stock_repository(),
        financial_repo=financial_repository(),
        fallback_provider=_yfinance_factory(),
    )


def price_sync_service() -> PriceSyncService:
    from apps.stocks.application.services.price_sync_service import PriceSyncService

    return PriceSyncService(
        stock_repo=stock_repository(),
        price_repo=price_repository(),
    )


def dividend_sync_service() -> DividendSyncService:
    from apps.stocks.application.services.dividend_sync_service import DividendSyncService

    return DividendSyncService(
        stock_repo=stock_repository(),
        dividend_repo=dividend_repository(),
    )


# ============================================================
# UseCase
# ============================================================


def sync_market_data_usecase() -> SyncMarketDataUseCase:
    from apps.stocks.application.usecases.sync_market_data_usecase import SyncMarketDataUseCase

    return SyncMarketDataUseCase(
        provider_resolver=market_data_provider_resolver(),
        stock_sync_service=stock_sync_service(),
        financial_sync_service=financial_sync_service(),
        price_sync_service=price_sync_service(),
        sync_log_repo=sync_log_repository(),
        dividend_sync_service=dividend_sync_service(),
    )


def etf_screening_usecase() -> EtfScreeningUseCase:
    from apps.stocks.application.usecases.etf_screening_usecase import EtfScreeningUseCase

    return EtfScreeningUseCase(
        stock_repo=stock_repository(),
        financial_repo=financial_repository(),
        dividend_repo=dividend_repository(),
        price_repo=price_repository(),
    )


def reit_screening_usecase() -> ReitScreeningUseCase:
    from apps.stocks.application.usecases.reit_screening_usecase import ReitScreeningUseCase

    return ReitScreeningUseCase(
        stock_repo=stock_repository(),
        financial_repo=financial_repository(),
        dividend_repo=dividend_repository(),
        price_repo=price_repository(),
    )


def recommendation_usecase() -> RecommendationUseCase:
    from apps.stocks.application.usecases.recommendation_usecase import RecommendationUseCase

    return RecommendationUseCase(
        stock_repo=stock_repository(),
        financial_repo=financial_repository(),
        price_repo=price_repository(),
        dividend_repo=dividend_repository(),
    )


def get_stock_technicals_usecase() -> GetStockTechnicalsUseCase:
    from apps.stocks.application.usecases.get_stock_technicals_usecase import (
        GetStockTechnicalsUseCase,
    )

    return GetStockTechnicalsUseCase(
        stock_repo=stock_repository(),
        price_repo=price_repository(),
    )


# ============================================================
# AI 機能
# ============================================================


def ai_config_repository() -> DjangoAiConfigRepository:
    from apps.ai.infrastructure.repositories.django_ai_repositories import DjangoAiConfigRepository

    return DjangoAiConfigRepository()


def ai_analysis_log_repository() -> DjangoAiAnalysisLogRepository:
    from apps.ai.infrastructure.repositories.django_ai_repositories import DjangoAiAnalysisLogRepository

    return DjangoAiAnalysisLogRepository()


def get_ai_config_usecase() -> GetAiConfigUseCase:
    from apps.ai.application.usecases.get_ai_config_usecase import GetAiConfigUseCase

    return GetAiConfigUseCase(ai_config_repo=ai_config_repository())


def save_ai_config_usecase() -> SaveAiConfigUseCase:
    from apps.ai.application.usecases.save_ai_config_usecase import SaveAiConfigUseCase

    return SaveAiConfigUseCase(ai_config_repo=ai_config_repository())


def analyze_stock_usecase() -> AnalyzeStockUseCase:
    from apps.ai.application.services.prompt_builder_service import PromptBuilderService
    from apps.ai.application.usecases.analyze_stock_usecase import AnalyzeStockUseCase
    from apps.stocks.application.usecases.screening_usecase import ScreeningUseCase

    # 画面の「スクリーニング指標」と同じ計算結果を AI プロンプトに渡すため、
    # Web 画面・MCP サマリと同一構成の ScreeningUseCase を注入する。
    screening = ScreeningUseCase(
        stock_repo=stock_repository(),
        financial_repo=financial_repository(),
        margin_repo=margin_repository(),
        price_repo=price_repository(),
        dividend_repo=dividend_repository(),
        owner_repo=owner_shareholder_repository(),
    )
    return AnalyzeStockUseCase(
        ai_config_repo=ai_config_repository(),
        ai_log_repo=ai_analysis_log_repository(),
        stock_repo=stock_repository(),
        financial_repo=financial_repository(),
        price_repo=price_repository(),
        screening_usecase=screening,
        prompt_builder=PromptBuilderService(),
        fx_repo=fx_rate_repository(),
        interest_repo=interest_rate_repository(),
    )


# ============================================================
# FX 分析
# ============================================================


def fx_rate_repository() -> DjangoFxRateRepository:
    from apps.fx.infrastructure.repositories import DjangoFxRateRepository

    return DjangoFxRateRepository()


def interest_rate_repository() -> DjangoInterestRateRepository:
    from apps.fx.infrastructure.repositories import DjangoInterestRateRepository

    return DjangoInterestRateRepository()


def macro_indicator_repository() -> DjangoMacroIndicatorRepository:
    from apps.fx.infrastructure.repositories import DjangoMacroIndicatorRepository

    return DjangoMacroIndicatorRepository()


def _fred_client() -> FredClientService:
    """FRED API クライアントを生成（m_api_configs から API キー取得）。"""
    from apps.fx.application.services.fred_client_service import FredClientService
    from apps.stocks.infrastructure.repositories import DjangoApiConfigRepository

    config = DjangoApiConfigRepository().find_by_provider("fred")
    if config is None or not config.api_key:
        raise RuntimeError("FRED API が設定されていません（m_api_configs に provider='fred' を登録してください）")
    return FredClientService(api_key=config.api_key)


def fx_data_sync_service() -> FxDataSyncService:
    from apps.fx.application.services.fx_data_sync_service import FxDataSyncService

    return FxDataSyncService(
        fx_rate_repo=fx_rate_repository(),
        interest_rate_repo=interest_rate_repository(),
        macro_indicator_repo=macro_indicator_repository(),
        fred_client=_fred_client(),
    )


def fx_analysis_service() -> FxAnalysisService:
    from apps.fx.application.services.fx_analysis_service import FxAnalysisService

    return FxAnalysisService(
        fx_rate_repo=fx_rate_repository(),
        interest_rate_repo=interest_rate_repository(),
        macro_indicator_repo=macro_indicator_repository(),
    )


def get_fx_analysis_usecase() -> GetFxAnalysisUseCase:
    from apps.fx.application.usecases.get_fx_analysis_usecase import GetFxAnalysisUseCase

    return GetFxAnalysisUseCase(analysis_service=fx_analysis_service())


def sync_fx_data_usecase() -> SyncFxDataUseCase:
    from apps.fx.application.usecases.sync_fx_data_usecase import SyncFxDataUseCase

    return SyncFxDataUseCase(sync_service=fx_data_sync_service())


# ============================================================
# 仮想売買
# ============================================================


def paper_trade_repository() -> DjangoPaperTradeRepository:
    from apps.paper_trading.infrastructure.repositories import DjangoPaperTradeRepository

    return DjangoPaperTradeRepository()


def paper_position_repository() -> DjangoPaperPositionRepository:
    from apps.paper_trading.infrastructure.repositories import DjangoPaperPositionRepository

    return DjangoPaperPositionRepository()


def paper_trading_service() -> PaperTradingService:
    from apps.paper_trading.application.services.paper_trading_service import PaperTradingService

    return PaperTradingService(
        trade_repo=paper_trade_repository(),
        position_repo=paper_position_repository(),
    )


def execute_trade_usecase() -> ExecuteTradeUseCase:
    from apps.paper_trading.application.usecases.execute_trade_usecase import ExecuteTradeUseCase

    return ExecuteTradeUseCase(
        trading_service=paper_trading_service(),
        stock_repo=stock_repository(),
    )


def list_positions_usecase() -> ListPositionsUseCase:
    from apps.paper_trading.application.usecases.list_positions_usecase import ListPositionsUseCase

    return ListPositionsUseCase(
        position_repo=paper_position_repository(),
        stock_repo=stock_repository(),
    )


def get_trade_history_usecase() -> GetTradeHistoryUseCase:
    from apps.paper_trading.application.usecases.get_trade_history_usecase import GetTradeHistoryUseCase

    return GetTradeHistoryUseCase(
        trade_repo=paper_trade_repository(),
        stock_repo=stock_repository(),
    )


def reset_paper_trading_usecase() -> ResetPaperTradingUseCase:
    from apps.paper_trading.application.usecases.reset_paper_trading_usecase import ResetPaperTradingUseCase

    return ResetPaperTradingUseCase(
        trade_repo=paper_trade_repository(),
        position_repo=paper_position_repository(),
    )


# ============================================================
# EDINET 大株主連携
# ============================================================


def sync_shareholders_usecase() -> SyncShareholdersUseCase:
    from apps.stocks.application.services.owner_match_service import OwnerMatchService
    from apps.stocks.application.services.shareholder_parse_service import ShareholderParseService
    from apps.stocks.application.usecases.sync_shareholders_usecase import SyncShareholdersUseCase
    from apps.stocks.infrastructure.external.edinet_client import EdinetClientService
    from apps.stocks.infrastructure.repositories import DjangoApiConfigRepository

    config = DjangoApiConfigRepository().find_by_provider("edinet")
    if config is None or not config.api_key:
        raise RuntimeError("EDINET API が設定されていません（m_api_configs に provider='edinet' を登録してください）")

    return SyncShareholdersUseCase(
        edinet_client=EdinetClientService(api_key=config.api_key),
        parse_service=ShareholderParseService(),
        match_service=OwnerMatchService(),
        stock_repo=stock_repository(),
        owner_repo=owner_shareholder_repository(),
        raw_repo=shareholder_raw_repository(),
    )


# ============================================================
# スクリーニングプリセット
# ============================================================


def list_screening_presets_usecase() -> ListScreeningPresetsUseCase:
    from apps.stocks.application.usecases.screening_preset_usecase import ListScreeningPresetsUseCase

    return ListScreeningPresetsUseCase(preset_repo=screening_preset_repository())


def save_screening_preset_usecase() -> SaveScreeningPresetUseCase:
    from apps.stocks.application.usecases.screening_preset_usecase import SaveScreeningPresetUseCase

    return SaveScreeningPresetUseCase(preset_repo=screening_preset_repository())


def delete_screening_preset_usecase() -> DeleteScreeningPresetUseCase:
    from apps.stocks.application.usecases.screening_preset_usecase import DeleteScreeningPresetUseCase

    return DeleteScreeningPresetUseCase(preset_repo=screening_preset_repository())


# ============================================================
# ポートフォリオシミュレーション
# ============================================================


def portfolio_simulation_usecase() -> PortfolioSimulationUseCase:
    from apps.portfolios.application.services.simulation_service import SimulationService
    from apps.portfolios.application.usecases.simulation_usecase import PortfolioSimulationUseCase
    from apps.portfolios.infrastructure.repositories import (
        DjangoAccountSnapshotRepository,
        DjangoFamilyMemberRepository,
        DjangoPortfolioAccountRepository,
    )

    return PortfolioSimulationUseCase(
        snapshot_repo=DjangoAccountSnapshotRepository(),
        account_repo=DjangoPortfolioAccountRepository(),
        member_repo=DjangoFamilyMemberRepository(),
        financial_repo=financial_repository(),
        simulation_service=SimulationService(),
    )


def dynamic_portfolio_valuation_service() -> DynamicPortfolioValuationService:
    from apps.portfolios.application.services.dynamic_valuation_service import (
        DynamicPortfolioValuationService,
    )

    return DynamicPortfolioValuationService()


# ─────────────────────────────────────
# 目標管理 (apps.goals)
# ─────────────────────────────────────


def _goal_repository() -> DjangoFinancialGoalRepository:
    from apps.goals.infrastructure.repositories import DjangoFinancialGoalRepository

    return DjangoFinancialGoalRepository()


def goals_list_usecase() -> ListGoalsUseCase:
    from apps.goals.application.usecases.list_goals_usecase import ListGoalsUseCase

    return ListGoalsUseCase(_goal_repository())


def goals_save_usecase() -> SaveGoalUseCase:
    from apps.goals.application.usecases.save_goal_usecase import SaveGoalUseCase

    return SaveGoalUseCase(_goal_repository())


def goals_delete_usecase() -> DeleteGoalUseCase:
    from apps.goals.application.usecases.delete_goal_usecase import DeleteGoalUseCase

    return DeleteGoalUseCase(_goal_repository())


def goals_reorder_usecase() -> ReorderGoalsUseCase:
    from apps.goals.application.usecases.reorder_goals_usecase import ReorderGoalsUseCase

    return ReorderGoalsUseCase(_goal_repository())


def goals_progress_usecase() -> GetGoalProgressUseCase:
    from apps.goals.application.services.goal_progress_service import GoalProgressService
    from apps.goals.application.usecases.get_goal_progress_usecase import GetGoalProgressUseCase
    from apps.portfolios.infrastructure.repositories import (
        DjangoAccountSnapshotRepository,
        DjangoFamilyMemberRepository,
        DjangoPortfolioAccountRepository,
    )

    return GetGoalProgressUseCase(
        goal_repo=_goal_repository(),
        member_repo=DjangoFamilyMemberRepository(),
        account_repo=DjangoPortfolioAccountRepository(),
        snapshot_repo=DjangoAccountSnapshotRepository(),
        service=GoalProgressService(),
    )


# ============================================================
# ニュース機能 (apps.news)
# ============================================================


def news_article_repository() -> DjangoNewsArticleRepository:
    from apps.news.infrastructure.repositories import DjangoNewsArticleRepository

    return DjangoNewsArticleRepository()


def news_stock_link_repository() -> DjangoNewsStockLinkRepository:
    from apps.news.infrastructure.repositories import DjangoNewsStockLinkRepository

    return DjangoNewsStockLinkRepository()


def news_ai_analysis_repository() -> DjangoNewsAiAnalysisRepository:
    from apps.news.infrastructure.repositories import DjangoNewsAiAnalysisRepository

    return DjangoNewsAiAnalysisRepository()


def news_keyword_repository() -> DjangoNewsKeywordRepository:
    from apps.news.infrastructure.repositories import DjangoNewsKeywordRepository

    return DjangoNewsKeywordRepository()


def _google_news_rss_client() -> GoogleNewsRssClientService:
    from apps.news.application.services.google_news_rss_client_service import GoogleNewsRssClientService

    return GoogleNewsRssClientService()


def _news_matching_service() -> NewsMatchingService:
    from apps.news.application.services.news_matching_service import NewsMatchingService

    return NewsMatchingService()


def _news_importance_service() -> NewsImportanceService:
    from apps.news.application.services.news_importance_service import NewsImportanceService

    return NewsImportanceService()


def _news_sync_service() -> NewsSyncService:
    from apps.news.application.services.news_sync_service import NewsSyncService

    return NewsSyncService(
        article_repo=news_article_repository(),
        stock_link_repo=news_stock_link_repository(),
    )


def sync_news_usecase() -> SyncNewsUseCase:
    from apps.news.application.usecases.sync_news_usecase import SyncNewsUseCase

    return SyncNewsUseCase(
        google_news_client=_google_news_rss_client(),
        matching_service=_news_matching_service(),
        importance_service=_news_importance_service(),
        sync_service=_news_sync_service(),
        stock_repo=stock_repository(),
    )


def list_news_usecase() -> ListNewsUseCase:
    from apps.news.application.usecases.list_news_usecase import ListNewsUseCase

    return ListNewsUseCase(article_repo=news_article_repository())


def list_stock_news_usecase() -> ListStockNewsUseCase:
    from apps.news.application.usecases.list_stock_news_usecase import ListStockNewsUseCase

    return ListStockNewsUseCase(
        article_repo=news_article_repository(),
        stock_repo=stock_repository(),
    )


# ============================================================
# MCP / 外部AI連携 (apps.mcp)
# ============================================================


def _mcp_api_key_repository() -> DjangoMcpApiKeyRepository:
    from apps.mcp.infrastructure.repositories import DjangoMcpApiKeyRepository

    return DjangoMcpApiKeyRepository()


def _mcp_api_key_generator_service() -> ApiKeyGeneratorService:
    from apps.mcp.application.services.api_key_generator_service import ApiKeyGeneratorService

    return ApiKeyGeneratorService()


def _mcp_news_source_url_builder_service() -> NewsSourceUrlBuilderService:
    from apps.mcp.application.services.news_source_url_builder_service import NewsSourceUrlBuilderService

    return NewsSourceUrlBuilderService()


def issue_api_key_usecase() -> IssueApiKeyUseCase:
    from apps.mcp.application.usecases.issue_api_key_usecase import IssueApiKeyUseCase

    return IssueApiKeyUseCase(
        api_key_repo=_mcp_api_key_repository(),
        generator=_mcp_api_key_generator_service(),
    )


def revoke_api_key_usecase() -> RevokeApiKeyUseCase:
    from apps.mcp.application.usecases.revoke_api_key_usecase import RevokeApiKeyUseCase

    return RevokeApiKeyUseCase(api_key_repo=_mcp_api_key_repository())


def list_api_keys_usecase() -> ListApiKeysUseCase:
    from apps.mcp.application.usecases.list_api_keys_usecase import ListApiKeysUseCase

    return ListApiKeysUseCase(api_key_repo=_mcp_api_key_repository())


def authenticate_api_key_usecase() -> AuthenticateApiKeyUseCase:
    from apps.mcp.application.usecases.authenticate_api_key_usecase import AuthenticateApiKeyUseCase

    return AuthenticateApiKeyUseCase(
        api_key_repo=_mcp_api_key_repository(),
        generator=_mcp_api_key_generator_service(),
    )


def get_stock_summary_tool_usecase() -> GetStockSummaryToolUseCase:
    from apps.mcp.application.usecases.tools.get_stock_summary_usecase import GetStockSummaryToolUseCase
    from apps.stocks.application.usecases.screening_usecase import ScreeningUseCase

    screening = ScreeningUseCase(
        stock_repo=stock_repository(),
        financial_repo=financial_repository(),
        margin_repo=margin_repository(),
        price_repo=price_repository(),
        dividend_repo=dividend_repository(),
        owner_repo=owner_shareholder_repository(),
    )
    return GetStockSummaryToolUseCase(screening_usecase=screening)


def get_stock_financials_tool_usecase() -> GetStockFinancialsToolUseCase:
    from apps.mcp.application.usecases.tools.get_stock_financials_usecase import GetStockFinancialsToolUseCase

    return GetStockFinancialsToolUseCase(
        stock_repo=stock_repository(),
        financial_repo=financial_repository(),
    )


def get_my_holdings_tool_usecase() -> GetMyHoldingsToolUseCase:
    from apps.mcp.application.usecases.tools.get_my_holdings_usecase import GetMyHoldingsToolUseCase
    from apps.portfolios.infrastructure.repositories import (
        DjangoAccountSnapshotRepository,
        DjangoFamilyMemberRepository,
        DjangoPortfolioAccountRepository,
    )

    return GetMyHoldingsToolUseCase(
        account_repo=DjangoPortfolioAccountRepository(),
        snapshot_repo=DjangoAccountSnapshotRepository(),
        member_repo=DjangoFamilyMemberRepository(),
        valuation_service=dynamic_portfolio_valuation_service(),
    )


def get_menu_tool_usecase() -> GetMenuToolUseCase:
    from apps.mcp.application.usecases.tools.get_menu_usecase import GetMenuToolUseCase

    return GetMenuToolUseCase(holdings_usecase=get_my_holdings_tool_usecase())


def get_my_watchlist_tool_usecase() -> GetMyWatchlistToolUseCase:
    from apps.mcp.application.usecases.tools.get_my_watchlist_usecase import GetMyWatchlistToolUseCase
    from apps.portfolios.infrastructure.repositories import DjangoWatchlistRepository

    return GetMyWatchlistToolUseCase(watchlist_repo=DjangoWatchlistRepository())


def get_fx_analysis_tool_usecase() -> GetFxAnalysisToolUseCase:
    from apps.mcp.application.usecases.tools.get_fx_analysis_tool_usecase import GetFxAnalysisToolUseCase

    return GetFxAnalysisToolUseCase(fx_usecase=get_fx_analysis_usecase())


def get_earnings_calendar_tool_usecase() -> GetEarningsCalendarToolUseCase:
    from apps.mcp.application.usecases.tools.get_earnings_calendar_usecase import (
        GetEarningsCalendarToolUseCase,
    )

    return GetEarningsCalendarToolUseCase(jquants_provider_factory=jquants_provider)


def search_stock_news_sources_tool_usecase() -> SearchStockNewsSourcesToolUseCase:
    from apps.mcp.application.usecases.tools.search_stock_news_sources_usecase import (
        SearchStockNewsSourcesToolUseCase,
    )

    return SearchStockNewsSourcesToolUseCase(
        stock_repo=stock_repository(),
        url_builder=_mcp_news_source_url_builder_service(),
    )


def search_ticker_tool_usecase() -> SearchTickerToolUseCase:
    from apps.mcp.application.usecases.tools.search_ticker_usecase import SearchTickerToolUseCase

    return SearchTickerToolUseCase(stock_repo=stock_repository())


def get_my_portfolio_summary_tool_usecase() -> GetMyPortfolioSummaryToolUseCase:
    from apps.mcp.application.usecases.tools.get_my_portfolio_summary_usecase import (
        GetMyPortfolioSummaryToolUseCase,
    )
    from apps.portfolios.infrastructure.repositories import (
        DjangoAccountSnapshotRepository,
        DjangoFamilyMemberRepository,
        DjangoPortfolioAccountRepository,
    )

    return GetMyPortfolioSummaryToolUseCase(
        account_repo=DjangoPortfolioAccountRepository(),
        snapshot_repo=DjangoAccountSnapshotRepository(),
        member_repo=DjangoFamilyMemberRepository(),
        valuation_service=dynamic_portfolio_valuation_service(),
    )


def get_my_pnl_tool_usecase() -> GetMyPnlToolUseCase:
    from apps.mcp.application.usecases.tools.get_my_pnl_usecase import GetMyPnlToolUseCase
    from apps.portfolios.application.services.dynamic_valuation_service import DjangoStockPriceSource
    from apps.portfolios.infrastructure.repositories import (
        DjangoAccountSnapshotRepository,
        DjangoPortfolioAccountRepository,
    )

    return GetMyPnlToolUseCase(
        account_repo=DjangoPortfolioAccountRepository(),
        snapshot_repo=DjangoAccountSnapshotRepository(),
        stock_repo=stock_repository(),
        price_source=DjangoStockPriceSource(),
    )


def get_margin_balance_tool_usecase() -> GetMarginBalanceToolUseCase:
    from apps.mcp.application.usecases.tools.get_margin_balance_usecase import GetMarginBalanceToolUseCase

    return GetMarginBalanceToolUseCase(
        stock_repo=stock_repository(),
        margin_repo=margin_repository(),
    )


def get_my_holdings_news_tool_usecase() -> GetMyHoldingsNewsToolUseCase:
    from apps.mcp.application.usecases.tools.get_my_holdings_news_usecase import GetMyHoldingsNewsToolUseCase
    from apps.portfolios.infrastructure.repositories import (
        DjangoAccountSnapshotRepository,
        DjangoWatchlistRepository,
    )

    return GetMyHoldingsNewsToolUseCase(
        snapshot_repo=DjangoAccountSnapshotRepository(),
        watchlist_repo=DjangoWatchlistRepository(),
        article_repo=news_article_repository(),
    )


def _build_full_screening_usecase() -> ScreeningUseCase:
    """ScreeningUseCase を完全な依存付きで構築する内部ヘルパー。"""
    from apps.stocks.application.usecases.screening_usecase import ScreeningUseCase

    return ScreeningUseCase(
        stock_repo=stock_repository(),
        financial_repo=financial_repository(),
        margin_repo=margin_repository(),
        price_repo=price_repository(),
        dividend_repo=dividend_repository(),
        owner_repo=owner_shareholder_repository(),
    )


def get_screening_candidates_tool_usecase() -> GetScreeningCandidatesToolUseCase:
    from apps.mcp.application.usecases.tools.get_screening_candidates_usecase import (
        GetScreeningCandidatesToolUseCase,
    )

    return GetScreeningCandidatesToolUseCase(screening_usecase=_build_full_screening_usecase())


def get_sell_candidates_tool_usecase() -> GetSellCandidatesToolUseCase:
    from apps.mcp.application.usecases.tools.get_sell_candidates_usecase import GetSellCandidatesToolUseCase
    from apps.portfolios.infrastructure.repositories import DjangoAccountSnapshotRepository

    return GetSellCandidatesToolUseCase(
        snapshot_repo=DjangoAccountSnapshotRepository(),
        screening_usecase=_build_full_screening_usecase(),
    )


def get_stock_risk_tags_tool_usecase() -> GetStockRiskTagsToolUseCase:
    from apps.mcp.application.usecases.tools.get_stock_risk_tags_usecase import GetStockRiskTagsToolUseCase

    return GetStockRiskTagsToolUseCase(screening_usecase=_build_full_screening_usecase())


def get_stock_opportunity_tags_tool_usecase() -> GetStockOpportunityTagsToolUseCase:
    from apps.mcp.application.usecases.tools.get_stock_opportunity_tags_usecase import (
        GetStockOpportunityTagsToolUseCase,
    )

    return GetStockOpportunityTagsToolUseCase(
        screening_usecase=_build_full_screening_usecase(),
        technicals_usecase=get_stock_technicals_usecase(),
    )


def compute_daily_movers_usecase() -> ComputeDailyMoversUseCase:
    from apps.stocks.application.usecases.compute_daily_movers_usecase import ComputeDailyMoversUseCase

    return ComputeDailyMoversUseCase(
        stock_repo=stock_repository(),
        price_repo=price_repository(),
        movers_repo=daily_movers_repository(),
    )


def get_price_movers_tool_usecase() -> GetPriceMoversToolUseCase:
    from apps.mcp.application.usecases.tools.get_price_movers_usecase import GetPriceMoversToolUseCase
    from apps.portfolios.infrastructure.repositories import (
        DjangoAccountSnapshotRepository,
        DjangoWatchlistRepository,
    )

    return GetPriceMoversToolUseCase(
        movers_repo=daily_movers_repository(),
        stock_repo=stock_repository(),
        snapshot_repo=DjangoAccountSnapshotRepository(),
        watchlist_repo=DjangoWatchlistRepository(),
    )


def get_my_margin_positions_tool_usecase() -> GetMyMarginPositionsToolUseCase:
    from apps.mcp.application.usecases.tools.get_my_margin_positions_usecase import (
        GetMyMarginPositionsToolUseCase,
    )
    from apps.portfolios.application.services.dynamic_valuation_service import DjangoStockPriceSource
    from apps.portfolios.infrastructure.repositories import (
        DjangoAccountSnapshotRepository,
        DjangoPortfolioAccountRepository,
    )

    return GetMyMarginPositionsToolUseCase(
        account_repo=DjangoPortfolioAccountRepository(),
        snapshot_repo=DjangoAccountSnapshotRepository(),
        price_source=DjangoStockPriceSource(),
    )


def get_my_dividends_calendar_tool_usecase() -> GetMyDividendsCalendarToolUseCase:
    from apps.mcp.application.usecases.tools.get_my_dividends_calendar_usecase import (
        GetMyDividendsCalendarToolUseCase,
    )
    from apps.portfolios.infrastructure.repositories import DjangoAccountSnapshotRepository

    return GetMyDividendsCalendarToolUseCase(
        snapshot_repo=DjangoAccountSnapshotRepository(),
        stock_repo=stock_repository(),
        dividend_repo=dividend_repository(),
    )


def ai_decision_repository() -> DjangoAiDecisionRepository:
    from apps.ai.infrastructure.repositories.django_ai_repositories import DjangoAiDecisionRepository

    return DjangoAiDecisionRepository()


def save_ai_decision_tool_usecase() -> SaveAiDecisionToolUseCase:
    from apps.mcp.application.usecases.tools.save_ai_decision_usecase import SaveAiDecisionToolUseCase

    return SaveAiDecisionToolUseCase(
        decision_repo=ai_decision_repository(),
        stock_repo=stock_repository(),
        summary_usecase=get_stock_summary_tool_usecase(),
    )


def get_price_distribution_3m_tool_usecase() -> GetPriceDistribution3mToolUseCase:
    from apps.mcp.application.usecases.tools.get_price_distribution_3m_usecase import (
        GetPriceDistribution3mToolUseCase,
    )

    return GetPriceDistribution3mToolUseCase(
        stock_repo=stock_repository(),
        price_repo=price_repository(),
        screening_usecase=_build_full_screening_usecase(),
    )


def get_my_holdings_alerts_tool_usecase() -> GetMyHoldingsAlertsToolUseCase:
    from apps.mcp.application.usecases.tools.get_my_holdings_alerts_usecase import (
        GetMyHoldingsAlertsToolUseCase,
    )
    from apps.portfolios.infrastructure.repositories import (
        DjangoAccountSnapshotRepository,
        DjangoPortfolioAccountRepository,
        DjangoWatchlistRepository,
    )

    return GetMyHoldingsAlertsToolUseCase(
        snapshot_repo=DjangoAccountSnapshotRepository(),
        account_repo=DjangoPortfolioAccountRepository(),
        watchlist_repo=DjangoWatchlistRepository(),
        stock_repo=stock_repository(),
        price_repo=price_repository(),
        movers_repo=daily_movers_repository(),
        screening_usecase=_build_full_screening_usecase(),
        earnings_calendar_tool_usecase=get_earnings_calendar_tool_usecase(),
    )


def tool_invocation_service() -> ToolInvocationService:
    from apps.mcp.application.services.tool_invocation_service import ToolInvocationService

    return ToolInvocationService()


# ─────────────────────────────────────────────────────────────
# apps/chat (マルチクライアントAIチャット連携)
# ─────────────────────────────────────────────────────────────


def chat_session_repository() -> DjangoChatSessionRepository:
    from apps.chat.infrastructure.repositories.django_chat_repositories import (
        DjangoChatSessionRepository,
    )

    return DjangoChatSessionRepository()


def chat_message_repository() -> DjangoChatMessageRepository:
    from apps.chat.infrastructure.repositories.django_chat_repositories import (
        DjangoChatMessageRepository,
    )

    return DjangoChatMessageRepository()


def chat_daily_limit_service() -> DailyLimitService:
    from apps.chat.application.services.daily_limit_service import DailyLimitService

    return DailyLimitService(message_repo=chat_message_repository())


def chat_llm_client_factory() -> LlmClientFactoryService:
    from apps.chat.application.services.llm_client_factory_service import (
        LlmClientFactoryService,
    )

    return LlmClientFactoryService()


def chat_tool_definition_service() -> ToolDefinitionService:
    from apps.chat.application.services.tool_definition_service import (
        ToolDefinitionService,
    )

    return ToolDefinitionService()


def chat_orchestration_service() -> ChatOrchestrationService:
    from apps.chat.application.services.chat_orchestration_service import (
        ChatOrchestrationService,
    )

    return ChatOrchestrationService()


def send_chat_message_usecase() -> SendChatMessageUseCase:
    from apps.chat.application.usecases.send_chat_message_usecase import (
        SendChatMessageUseCase,
    )

    return SendChatMessageUseCase(
        ai_config_repo=ai_config_repository(),
        session_repo=chat_session_repository(),
        message_repo=chat_message_repository(),
        daily_limit_service=chat_daily_limit_service(),
        llm_client_factory=chat_llm_client_factory(),
        tool_definition_service=chat_tool_definition_service(),
        chat_orchestration_service=chat_orchestration_service(),
        tool_invocation_service=tool_invocation_service(),
    )


def list_chat_sessions_usecase() -> ListChatSessionsUseCase:
    from apps.chat.application.usecases.list_chat_sessions_usecase import (
        ListChatSessionsUseCase,
    )

    return ListChatSessionsUseCase(session_repo=chat_session_repository())


def list_chat_messages_usecase() -> ListChatMessagesUseCase:
    from apps.chat.application.usecases.list_chat_messages_usecase import (
        ListChatMessagesUseCase,
    )

    return ListChatMessagesUseCase(
        session_repo=chat_session_repository(),
        message_repo=chat_message_repository(),
    )


def delete_chat_session_usecase() -> DeleteChatSessionUseCase:
    from apps.chat.application.usecases.delete_chat_session_usecase import (
        DeleteChatSessionUseCase,
    )

    return DeleteChatSessionUseCase(session_repo=chat_session_repository())


def get_chat_status_usecase() -> GetChatStatusUseCase:
    from apps.chat.application.usecases.get_chat_status_usecase import (
        GetChatStatusUseCase,
    )

    return GetChatStatusUseCase(
        ai_config_repo=ai_config_repository(),
        daily_limit_service=chat_daily_limit_service(),
    )


# ============================================================
# Cognito OAuth 認証 (apps.auth_cognito)
# ============================================================


def cognito_link_repository() -> DjangoCognitoLinkRepository:
    from apps.auth_cognito.infrastructure.repositories.django_cognito_repositories import (
        DjangoCognitoLinkRepository,
    )

    return DjangoCognitoLinkRepository()


def user_allowed_email_repository() -> DjangoUserAllowedEmailRepository:
    from apps.auth_cognito.infrastructure.repositories.django_cognito_repositories import (
        DjangoUserAllowedEmailRepository,
    )

    return DjangoUserAllowedEmailRepository()


def cognito_jwks_cache_service() -> JwksCacheService:
    from django.conf import settings

    from apps.auth_cognito.application.services.jwks_cache_service import JwksCacheService

    return JwksCacheService(jwks_url=settings.COGNITO_JWKS_URL)


def cognito_jwt_verifier_service() -> CognitoJwtVerifierService:
    from django.conf import settings

    from apps.auth_cognito.application.services.cognito_jwt_verifier_service import (
        CognitoJwtVerifierService,
    )

    return CognitoJwtVerifierService(
        jwks_cache=cognito_jwks_cache_service(),
        issuer=settings.COGNITO_JWT_ISSUER,
        allowed_client_ids=settings.COGNITO_ALLOWED_CLIENT_IDS,
    )


def jit_provision_service() -> JitProvisionService:
    from apps.auth_cognito.application.services.jit_provision_service import JitProvisionService

    return JitProvisionService(
        link_repo=cognito_link_repository(),
        allowed_repo=user_allowed_email_repository(),
    )


def cognito_userpool_repository() -> Boto3CognitoUserPoolRepository:
    import boto3
    from django.conf import settings

    from apps.auth_cognito.infrastructure.repositories.boto3_cognito_userpool_repository import (
        Boto3CognitoUserPoolRepository,
    )

    client = boto3.client("cognito-idp", region_name=settings.COGNITO_REGION)
    return Boto3CognitoUserPoolRepository(client=client, user_pool_id=settings.COGNITO_USER_POOL_ID)


def cognito_invite_service() -> CognitoInviteService:
    from apps.auth_cognito.application.services.cognito_invite_service import (
        CognitoInviteService,
    )

    return CognitoInviteService(userpool_repo=cognito_userpool_repository())


def admin_user_query_service() -> AdminUserQueryService:
    from apps.auth_cognito.application.services.admin_user_query_service import (
        AdminUserQueryService,
    )

    return AdminUserQueryService(
        cognito_link_repo=cognito_link_repository(),
        allowed_email_repo=user_allowed_email_repository(),
    )


def admin_user_create_service() -> AdminUserCreateService:
    from apps.auth_cognito.application.services.admin_user_create_service import (
        AdminUserCreateService,
    )

    return AdminUserCreateService()


def allowed_email_service() -> AllowedEmailService:
    from apps.auth_cognito.application.services.allowed_email_service import (
        AllowedEmailService,
    )

    return AllowedEmailService(allowed_repo=user_allowed_email_repository())


def cognito_link_admin_service() -> CognitoLinkAdminService:
    from apps.auth_cognito.application.services.cognito_link_admin_service import (
        CognitoLinkAdminService,
    )

    return CognitoLinkAdminService(link_repo=cognito_link_repository())


def admin_user_lifecycle_service() -> AdminUserLifecycleService:
    from apps.auth_cognito.application.services.admin_user_lifecycle_service import (
        AdminUserLifecycleService,
    )

    return AdminUserLifecycleService()


def cognito_user_pool_admin_service() -> CognitoUserPoolAdminService:
    from apps.auth_cognito.application.services.cognito_user_pool_admin_service import (
        CognitoUserPoolAdminService,
    )

    return CognitoUserPoolAdminService(
        userpool_repo=cognito_userpool_repository(),
        link_repo=cognito_link_repository(),
    )


def list_admin_users_usecase() -> ListAdminUsersUseCase:
    from apps.auth_cognito.application.usecases.list_admin_users_usecase import (
        ListAdminUsersUseCase,
    )

    return ListAdminUsersUseCase(admin_user_query_service=admin_user_query_service())


def create_admin_user_usecase() -> CreateAdminUserUseCase:
    from apps.auth_cognito.application.usecases.create_admin_user_usecase import (
        CreateAdminUserUseCase,
    )

    return CreateAdminUserUseCase(
        admin_user_create_service=admin_user_create_service(),
        allowed_email_service=allowed_email_service(),
        invite_service=cognito_invite_service(),
    )


def add_allowed_email_usecase() -> AddAllowedEmailUseCase:
    from apps.auth_cognito.application.usecases.add_allowed_email_usecase import (
        AddAllowedEmailUseCase,
    )

    return AddAllowedEmailUseCase(allowed_email_service=allowed_email_service())


def remove_allowed_email_usecase() -> RemoveAllowedEmailUseCase:
    from apps.auth_cognito.application.usecases.remove_allowed_email_usecase import (
        RemoveAllowedEmailUseCase,
    )

    return RemoveAllowedEmailUseCase(allowed_email_service=allowed_email_service())


def delete_cognito_link_usecase() -> DeleteCognitoLinkUseCase:
    from apps.auth_cognito.application.usecases.delete_cognito_link_usecase import (
        DeleteCognitoLinkUseCase,
    )

    return DeleteCognitoLinkUseCase(cognito_link_admin_service=cognito_link_admin_service())


def list_cognito_users_usecase() -> ListCognitoUsersUseCase:
    from apps.auth_cognito.application.usecases.list_cognito_users_usecase import (
        ListCognitoUsersUseCase,
    )

    return ListCognitoUsersUseCase(
        cognito_userpool_repo=cognito_userpool_repository(),
        cognito_link_repo=cognito_link_repository(),
    )


def disable_admin_user_usecase() -> DisableAdminUserUseCase:
    from apps.auth_cognito.application.usecases.disable_admin_user_usecase import (
        DisableAdminUserUseCase,
    )

    return DisableAdminUserUseCase(lifecycle_service=admin_user_lifecycle_service())


def enable_admin_user_usecase() -> EnableAdminUserUseCase:
    from apps.auth_cognito.application.usecases.enable_admin_user_usecase import (
        EnableAdminUserUseCase,
    )

    return EnableAdminUserUseCase(lifecycle_service=admin_user_lifecycle_service())


def delete_admin_user_usecase() -> DeleteAdminUserUseCase:
    from apps.auth_cognito.application.usecases.delete_admin_user_usecase import (
        DeleteAdminUserUseCase,
    )

    return DeleteAdminUserUseCase(lifecycle_service=admin_user_lifecycle_service())


def disable_cognito_user_usecase() -> DisableCognitoUserUseCase:
    from apps.auth_cognito.application.usecases.disable_cognito_user_usecase import (
        DisableCognitoUserUseCase,
    )

    return DisableCognitoUserUseCase(service=cognito_user_pool_admin_service())


def enable_cognito_user_usecase() -> EnableCognitoUserUseCase:
    from apps.auth_cognito.application.usecases.enable_cognito_user_usecase import (
        EnableCognitoUserUseCase,
    )

    return EnableCognitoUserUseCase(service=cognito_user_pool_admin_service())


def delete_cognito_user_usecase() -> DeleteCognitoUserUseCase:
    from apps.auth_cognito.application.usecases.delete_cognito_user_usecase import (
        DeleteCognitoUserUseCase,
    )

    return DeleteCognitoUserUseCase(service=cognito_user_pool_admin_service())
