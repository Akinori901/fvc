"""管理者ロール専用 OpenAI APIキーの取得。

優先順位:
1. 環境変数 OPENAI_ADMIN_API_KEY（ローカル開発時の上書き）
2. SSM Parameter Store（OPENAI_ADMIN_KEY_SSM_PARAMETER で指定されたパラメータ名から取得）
3. None（未設定 = 管理者キー機能無効）

Lambda コンテナの存続期間（最大 15 分）キャッシュされる（lru_cache）。
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache

logger = logging.getLogger(__name__)

# Terraform で初回作成した時のダミー値（実値が投入されたかの判定に使う）
_PLACEHOLDER_VALUE = "PLACEHOLDER_SET_VIA_AWS_CONSOLE"


@lru_cache(maxsize=1)
def get_admin_openai_api_key() -> str | None:
    """管理者ロール用 OpenAI APIキーを取得する。

    Lambda コンテナの生存期間中はキャッシュされる。
    """
    # ローカル開発: 直接環境変数から取得
    direct = os.environ.get("OPENAI_ADMIN_API_KEY")
    if direct:
        return direct

    # 本番: SSM Parameter Store
    param_name = os.environ.get("OPENAI_ADMIN_KEY_SSM_PARAMETER")
    if not param_name:
        return None

    try:
        import boto3
    except ImportError:
        logger.warning("boto3 が利用できないため、管理者キーは取得しない")
        return None

    try:
        client = boto3.client("ssm")
        response = client.get_parameter(Name=param_name, WithDecryption=True)
        value: str = response["Parameter"]["Value"]
        if value == _PLACEHOLDER_VALUE:
            logger.info("SSM パラメータがプレースホルダー値のため、管理者キーは未設定扱い")
            return None
        return value
    except Exception as exc:  # noqa: BLE001 - boto3 例外含む全て握りつぶして None 返却
        logger.warning("SSM から管理者キー取得に失敗: %s", exc)
        return None


def reset_cache_for_tests() -> None:
    """テストから lru_cache をリセットするためのヘルパ。"""
    get_admin_openai_api_key.cache_clear()
