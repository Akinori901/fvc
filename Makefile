.PHONY: help up down build logs restart \
       backend-shell frontend-shell mysql \
       migrate makemigrations test-backend lint format format-check type-check quality \
       test-frontend lint-frontend \
       sync-stocks sync-financials sync-prices sync-all \
       cleanup-prices seed setup

# ===========================
# Docker
# ===========================

help: ## コマンド一覧を表示
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

up: ## コンテナ起動
	docker compose up -d

down: ## コンテナ停止
	docker compose down

build: ## コンテナビルド
	docker compose build

logs: ## 全コンテナのログ表示
	docker compose logs -f

logs-backend: ## バックエンドのログ表示
	docker compose logs -f backend

logs-frontend: ## フロントエンドのログ表示
	docker compose logs -f frontend

logs-db: ## DBのログ表示
	docker compose logs -f db

restart: ## 全コンテナ再起動
	docker compose restart

ps: ## コンテナ状態確認
	docker compose ps

# ===========================
# Shell接続
# ===========================

backend-shell: ## バックエンドコンテナに入る
	docker compose exec backend bash

frontend-shell: ## フロントエンドコンテナに入る
	docker compose exec frontend sh

mysql: ## MySQLに接続
	docker compose exec db mysql -ufvc_user -pfvc_password fair_value_calculator

# ===========================
# Backend
# ===========================

migrate: ## マイグレーション実行
	docker compose exec backend uv run python manage.py migrate

makemigrations: ## マイグレーションファイル作成
	docker compose exec backend uv run python manage.py makemigrations

test-backend: ## バックエンドテスト実行
	docker compose exec backend uv run python -m pytest -v

lint: ## Ruff Lint実行
	docker compose exec backend uv run ruff check .

format: ## Ruff Format実行
	docker compose exec backend uv run ruff format .

format-check: ## Ruff Formatチェック（修正なし）
	docker compose exec backend uv run ruff format --check .

type-check: ## mypy型チェック実行
	docker compose exec backend uv run mypy .

quality: lint format-check type-check ## コード品質チェック（lint + format-check + type-check）

createsuperuser: ## Django管理ユーザー作成
	docker compose exec backend uv run python manage.py createsuperuser

collectstatic: ## 静的ファイル収集
	docker compose exec backend uv run python manage.py collectstatic --noinput

shell: ## Django shell起動
	docker compose exec backend uv run python manage.py shell

seed: ## 開発用初期データ投入（admin / admin1234）
	docker compose exec backend uv run python manage.py seed

# ===========================
# Frontend
# ===========================

test-frontend: ## フロントエンドテスト実行
	docker compose exec frontend npm test

lint-frontend: ## フロントエンドLint実行
	docker compose exec frontend npm run lint

build-frontend: ## フロントエンドビルド
	docker compose exec frontend npm run build

# ===========================
# Sync (市場データ同期)
# ===========================

sync-stocks: ## 銘柄マスタ同期 (JP)
	docker compose exec backend uv run python manage.py sync_stocks --market JP

sync-financials: ## 財務データ同期 (JP)
	docker compose exec backend uv run python manage.py sync_financials --market JP

sync-prices: ## 株価同期 (JP)
	docker compose exec backend uv run python manage.py sync_prices --market JP

sync-all: ## 全データ同期 (JP)
	docker compose exec backend uv run python manage.py sync_all --market JP

cleanup-prices: ## 古い株価データ削除（2年以上前）
	docker compose exec backend uv run python manage.py cleanup_old_prices

# ===========================
# MCP
# ===========================

verify-mcp: ## MCPサーバの21ツールを検証 (FVC_MCP_URL/FVC_MCP_API_KEY 環境変数 or 引数指定)
	@if [ -z "$$FVC_MCP_API_KEY" ]; then \
		echo "ERROR: FVC_MCP_API_KEY 環境変数 が未設定です"; \
		echo "  例: export FVC_MCP_API_KEY=fvc_mcp_xxxxx"; \
		echo "  例: export FVC_MCP_URL=http://backend:8000/mcp/  (Docker 内から)"; \
		echo "  例: export FVC_MCP_URL=https://d3dz1e2hexhvbr.cloudfront.net/mcp/  (本番)"; \
		exit 1; \
	fi
	docker compose exec \
		-e FVC_MCP_URL=$${FVC_MCP_URL:-http://backend:8000/mcp/} \
		-e FVC_MCP_API_KEY=$$FVC_MCP_API_KEY \
		backend uv run python /scripts/verify_mcp.py

# ===========================
# Tools (phpMyAdmin / Swagger)
# ===========================

logs-phpmyadmin: ## phpMyAdminのログ表示
	docker compose logs -f phpmyadmin

logs-swagger: ## Swaggerのログ表示
	docker compose logs -f swagger

# ===========================
# Setup
# ===========================

setup: build up migrate seed ## 初期セットアップ（ビルド→起動→マイグレーション→シード）
	@echo ""
	@echo "========================================"
	@echo " Setup complete!"
	@echo " Backend:     http://localhost:18000/api/"
	@echo " Frontend:    http://localhost:3000"
	@echo " Admin:       http://localhost:18000/admin/"
	@echo " phpMyAdmin:  http://localhost:18080"
	@echo " Swagger UI:  http://localhost:18081"
	@echo " MySQL:       localhost:13306"
	@echo ""
	@echo " Login: admin / admin1234"
	@echo "========================================"
