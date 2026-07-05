FROM python:3.13-slim

# mysqlclient ビルドに必要なシステム依存
RUN apt-get update && apt-get install -y --no-install-recommends \
    default-libmysqlclient-dev \
    build-essential \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# uv インストール
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# 依存インストール（キャッシュ活用のため先にコピー）
COPY pyproject.toml ./
RUN uv sync --extra dev

# ソースコードコピー（開発時はvolumeマウントで上書き）
COPY . .

EXPOSE 8000

# 開発サーバー起動（ASGI = uvicorn、ホットリロード有効）
# - Django REST API ＋ MCP Streamable HTTP（/mcp）を同一プロセスで提供するため ASGI を使う
CMD ["uv", "run", "uvicorn", "config.asgi:application", "--host", "0.0.0.0", "--port", "8000", "--reload"]
