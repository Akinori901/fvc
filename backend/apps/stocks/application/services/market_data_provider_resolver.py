"""市場データプロバイダー解決サービス。"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from apps.stocks.domain.repositories import ApiConfigRepository, MarketDataProvider

logger = logging.getLogger(__name__)


class MarketDataProviderResolver:
    """市場タイプとAPI設定から適切なプロバイダーを返す。

    フォールバックロジック:
    - JP市場: m_api_configs で "jquants" が有効 → JQuantsClient、それ以外 → YfinanceClient
    - US市場: 常に YfinanceClient
    """

    def __init__(
        self,
        api_config_repo: ApiConfigRepository,
        jquants_factory: Callable[[str], MarketDataProvider],
        yfinance_factory: Callable[[], MarketDataProvider],
    ) -> None:
        self._api_config_repo = api_config_repo
        self._jquants_factory = jquants_factory
        self._yfinance_factory = yfinance_factory

    def resolve(self, market_type: str) -> MarketDataProvider:
        """指定された市場タイプに対応するプロバイダーを返す。"""
        if market_type == "JP":
            return self._resolve_jp()
        return self._yfinance_factory()

    def resolve_dividend(self, market_type: str) -> MarketDataProvider:
        """配当データ取得用プロバイダーを返す。

        Premium プランの J-Quants であれば J-Quants を使用。
        Standard/未設定の場合は yfinance にフォールバック。
        """
        if market_type == "JP":
            config = self._api_config_repo.find_by_provider("jquants")
            if config and config.is_enabled and config.api_key and config.plan == "premium":
                logger.info("J-Quants Premium で配当データを取得")
                return self._jquants_factory(config.api_key)
        logger.info("yfinance で配当データを取得")
        return self._yfinance_factory()

    def _resolve_jp(self) -> MarketDataProvider:
        """JP市場のプロバイダー解決。"""
        config = self._api_config_repo.find_by_provider("jquants")
        if config and config.is_enabled and config.api_key:
            logger.info("J-Quants プロバイダーを使用（plan=%s）", config.plan)
            return self._jquants_factory(config.api_key)

        logger.info("J-Quants 未設定のため yfinance にフォールバック")
        return self._yfinance_factory()
