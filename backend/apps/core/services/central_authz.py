"""共通認証基盤（qol-auth-console）への問い合わせ。

「この人が FVC を使ってよいか」「どの役割か」を中央に聞く。

--- なぜ中央に聞くのか ---

ロールが Django の `is_superuser` にしか無いと、変更のたびに
`manage.py` か Django admin を触ることになる。認証コンソールの画面から
一箇所で管理できるようにするのがこの層の目的。

--- 移行中の扱い（重要）---

**既存の `is_superuser` と中央の「どちらかで許可されれば通す」**。
中央が落ちても既存側で救われるので、移行中に管理画面から締め出されない。
中央だけで判定するのは、運用が安定してからにする。

--- 失敗したときの方針 ---

中央に届かない・エラーが返る場合は `None` を返す（拒否ではない）。
呼び出し側は「中央の判断が得られなかった」として既存の判定に委ねる。

拒否（`allowed: false`）と障害（`None`）を区別するのが肝心で、
混ぜると中央の障害時に全員が締め出される。

移植元: task-scope の同名モジュール。FVC はスコープの概念が無い
（各自が自分のデータを見るだけ）ため、scopes の解決は持たない。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

_CACHE_PREFIX = "central_authz:"
APP_KEY = "fair-value-calculator"


@dataclass(frozen=True)
class CentralAuthz:
    """中央が返した認可の結果。"""

    allowed: bool
    role: str

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


def fetch(email: str) -> CentralAuthz | None:
    """中央に認可を問い合わせる。

    戻り値:
        CentralAuthz: 中央が判断できた（allowed の真偽は中身を見る）
        None: 中央が未設定・到達できない・エラー（＝判断が得られなかった）

    キャッシュ:
        権限判定は API のたびに走るため、毎回問い合わせるとレイテンシが乗る。
        既定 60 秒。権限変更の反映が最大 60 秒遅れるが、
        **締め出しではなく開放が遅れる方向**なので許容する。
        即時に止めたいときは Cognito 側でユーザーを無効化する。
    """
    base = getattr(settings, "CENTRAL_AUTHZ_URL", "")
    if not base:
        return None  # 未設定 = 中央を使わない（移行前の状態）

    email = (email or "").strip().lower()
    if not email:
        return None

    key = f"{_CACHE_PREFIX}{email}"
    cached = cache.get(key)
    if cached is not None:
        # 「中央に聞いたが判断できなかった」もキャッシュする。
        # 中央が落ちている間、毎リクエストでタイムアウトを待つのを避ける。
        return cached if isinstance(cached, CentralAuthz) else None

    ttl = getattr(settings, "CENTRAL_AUTHZ_CACHE_TTL", 60)
    timeout = getattr(settings, "CENTRAL_AUTHZ_TIMEOUT", 3.0)

    try:
        resp = httpx.get(
            f"{base.rstrip('/')}/api/authz",
            params={"email": email, "app": APP_KEY},
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()
    except (httpx.HTTPError, ValueError):
        # ここで例外を投げると権限判定が 500 になる。
        # 中央の障害で管理画面に入れなくなるのは避けたいので、
        # 「判断が得られなかった」として既存の判定に委ねる。
        logger.warning("中央の認可に問い合わせできませんでした: %s", email, exc_info=True)
        cache.set(key, "unavailable", ttl)
        return None

    result = CentralAuthz(
        allowed=bool(data.get("allowed")),
        role=str(data.get("role") or "member"),
    )
    cache.set(key, result, ttl)
    return result


def invalidate(email: str) -> None:
    """キャッシュを捨てる。権限変更を即座に反映したいときに使う。"""
    cache.delete(f"{_CACHE_PREFIX}{(email or '').strip().lower()}")
