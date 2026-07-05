"""ASGI config for fair-value-calculator project.

本番環境(Lambda)では Mangum を経由して ASGI アプリケーションを実行する。

Django REST API（/）と MCP Streamable HTTP（/mcp）を同一プロセスで提供する。

# Lambda での FastMCP lifespan について
- FastMCP の `streamable_http_app()` は内部で `StreamableHTTPSessionManager` の task group を
  ASGI lifespan で起動する。これが起動していないと `RuntimeError: Task group is not initialized.`
  になる。
- Mangum は `lifespan="auto"`（デフォルト）で Lambda コンテナ初期化（cold start）時に
  startup を 1 回だけ呼ぶ。warm 再利用時は task group が活きたまま残る。
- そのため `application` は **モジュールスコープ** で構築する必要がある（ハンドラ内で
  毎回作ると `session_manager.run() can only be called once per instance` で爆発する）。
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

django_app = get_asgi_application()


def _build_composed_app() -> object:
    """Django ASGI と MCP Streamable HTTP を Starlette Mount で合成する。

    エラー時は Django のみを返す（MCP が壊れていても Web 機能は守る）。
    """
    try:
        import contextlib

        from starlette.applications import Starlette
        from starlette.middleware import Middleware
        from starlette.middleware.base import BaseHTTPMiddleware
        from starlette.requests import Request
        from starlette.responses import JSONResponse
        from starlette.routing import Mount

        from apps.mcp.presentation.mcp_app import mcp_server, set_current_user_id

        class McpAuthMiddleware(BaseHTTPMiddleware):
            """`Authorization: Bearer fvc_mcp_...` を解決して ContextVar にセット。"""

            async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
                # Django 初期化はアプリ起動時に完了済み
                from asgiref.sync import sync_to_async

                from config import container

                auth = request.headers.get("authorization", "")
                user_id: int | None = None
                if auth.startswith("Bearer "):
                    raw_key = auth[7:].strip()
                    if raw_key.startswith("fvc_mcp_"):

                        def _resolve() -> int | None:
                            usecase = container.authenticate_api_key_usecase()
                            user = usecase.execute(raw_key)
                            return user.pk if user is not None and getattr(user, "is_active", False) else None

                        user_id = await sync_to_async(_resolve, thread_sensitive=True)()
                        if user_id is None:
                            return JSONResponse({"detail": "Invalid MCP API key"}, status_code=401)

                set_current_user_id(user_id)
                try:
                    return await call_next(request)
                finally:
                    set_current_user_id(None)

        # FastMCP の Streamable HTTP ASGI app
        mcp_http_app = mcp_server.streamable_http_app()

        # FastMCP は task group のライフサイクル管理を ASGI lifespan で行うので、
        # 親 Starlette からそれを引き継ぐ
        @contextlib.asynccontextmanager
        async def lifespan(_app):  # type: ignore[no-untyped-def]
            async with mcp_http_app.router.lifespan_context(mcp_http_app):
                yield

        # mcp_http_app は streamable_http_path="/" 設定なので、/mcp prefix でマウントすると
        # 外部から /mcp でアクセス可能になる。
        composed = Starlette(
            routes=[
                Mount("/mcp", app=mcp_http_app, middleware=[Middleware(McpAuthMiddleware)]),
                Mount("/", app=django_app),  # type: ignore[arg-type]
            ],
            lifespan=lifespan,
        )
        return composed
    except Exception:  # noqa: BLE001
        import logging

        logging.getLogger(__name__).exception("MCP マウントに失敗。Django のみで起動します。")
        return django_app


# Hotfix: Lambda の lifespan で FastMCP の `StreamableHTTPSessionManager.run()` が
# 複数 invocation にまたがって 2 回以上呼ばれて RuntimeError で起動失敗する事象が発生中。
# 一時的に MCP マウントを env フラグでガードし、デフォルトで Django のみを公開する。
# 環境変数 FVC_MCP_MOUNT_ENABLED=1 が設定された場合のみ MCP を合成する。
application = _build_composed_app() if os.environ.get("FVC_MCP_MOUNT_ENABLED") == "1" else django_app

# AWS Lambda ハンドラー（Mangum）
# Lambda のエントリーポイント: config.asgi.handler
# MCP マウント無効時は Django のみのため lifespan="off" で十分。
# 有効時のみ "auto" で FastMCP の task group lifespan を引き継ぐ。
try:
    from mangum import Mangum

    _lifespan_mode = "auto" if os.environ.get("FVC_MCP_MOUNT_ENABLED") == "1" else "off"
    handler = Mangum(application, lifespan=_lifespan_mode)  # type: ignore[arg-type]
except ImportError:
    # ローカル開発時は Mangum 不要
    pass
