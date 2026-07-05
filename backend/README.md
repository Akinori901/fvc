# Backend

Django 6.0 + Django REST Framework による REST API サーバー。
Clean Architecture + UseCase / Service 分離構成を採用。

---

## Swagger UI による API 仕様確認

Docker 起動後、ブラウザで以下にアクセスすると Swagger UI でAPI仕様を確認できます。

```
http://localhost:18081
```

API 仕様は `openapi/api/` ディレクトリで管理されています。

```
openapi/api/
├── index.yaml              # メインエントリーポイント（タグ定義・サーバー設定）
├── components/
│   ├── common/
│   │   ├── schemas.yaml    # 共通スキーマ（ページネーション・日付型等）
│   │   ├── errors.yaml     # エラーレスポンス定義
│   │   ├── parameters.yaml # 共通クエリパラメータ
│   │   └── success.yaml    # 共通成功レスポンス
└── paths/                  # エンドポイント別定義
```

---

## API エンドポイント一覧

### 認証

| メソッド | パス | 説明 |
|---------|------|------|
| POST | `/api/auth/login/` | ログイン（access / refresh トークン取得） |
| POST | `/api/auth/logout/` | ログアウト |
| POST | `/api/auth/token/refresh/` | アクセストークンのリフレッシュ |
| GET | `/api/auth/user/` | ログイン中ユーザー情報取得 |

### 銘柄管理

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/api/stocks/` | 銘柄一覧取得 |
| POST | `/api/stocks/` | 銘柄作成 |
| GET | `/api/stocks/{code}/` | 銘柄詳細取得 |
| PUT | `/api/stocks/{code}/` | 銘柄更新 |
| DELETE | `/api/stocks/{code}/` | 銘柄削除 |
| GET | `/api/stocks/{code}/financials/` | 財務データ一覧 |
| POST | `/api/stocks/{code}/financials/` | 財務データ登録 |
| GET | `/api/stocks/{code}/prices/` | 株価一覧 |
| GET | `/api/stocks/{code}/valuations/` | 銘柄別算出履歴 |

### スクリーニング・同期

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/api/stocks/screening/` | スクリーニング実行 |
| POST | `/api/stocks/sync/` | データ同期トリガー |
| GET | `/api/stocks/sync/logs/` | 同期ログ一覧 |

### 適正価格算出

| メソッド | パス | 説明 |
|---------|------|------|
| POST | `/api/valuations/calculate/` | 適正株価算出 |
| GET | `/api/valuations/` | 算出履歴一覧 |
| GET | `/api/valuations/{id}/` | 算出結果詳細 |

### ポートフォリオ・ウォッチリスト

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/api/portfolio/` | ポートフォリオ一覧 |
| POST | `/api/portfolio/` | ポートフォリオ登録 |
| PUT | `/api/portfolio/{id}/` | ポートフォリオ更新 |
| DELETE | `/api/portfolio/{id}/` | ポートフォリオ削除 |
| GET | `/api/watchlist/` | ウォッチリスト一覧 |
| POST | `/api/watchlist/` | ウォッチリスト追加 |
| DELETE | `/api/watchlist/{id}/` | ウォッチリスト削除 |

### 設定

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/api/settings/api-configs/` | API設定一覧 |
| POST | `/api/settings/api-configs/` | API設定作成 |
| GET | `/api/settings/api-configs/{provider}/` | API設定詳細 |
| PUT | `/api/settings/api-configs/{provider}/` | API設定更新 |

---

## 認証

**SimpleJWT + dj-rest-auth + django-allauth** による JWT 認証。

| 項目 | 値 |
|------|-----|
| アクセストークン有効期限 | 30分 |
| リフレッシュトークン有効期限 | 7日 |
| リフレッシュ時のローテーション | 有効（refresh_token は使い捨て） |
| デフォルト認証クラス | `IsAuthenticated`（全エンドポイント） |

フロントエンドはアクセストークンを `Authorization: Bearer {token}` ヘッダーで送信し、401 応答時にリフレッシュトークンで自動再取得します。

---

## J-Quants データ連携

J-Quants は日本証券業協会が提供する日本株専用のデータプラットフォームです。

### プラン別機能差異

| 機能 | Free | Light | Standard | Premium |
|------|------|-------|----------|---------|
| 銘柄マスタ同期 | ○ | ○ | ○ | ○ |
| 財務データ同期（当期） | ○ | ○ | ○ | ○ |
| 財務データ（複数年分） | △ | ○ | ○ | ○ |
| 株価（直近12週のみ） | ○ | △ | × | × |
| 株価（全期間） | × | ○ | ○ | ○ |

**Free プランの主な制約**

- 株価データは **直近12週分** のみ取得可能（過去データは取得不可）
- 財務データは **上場銘柄の当期分のみ**（複数期の遡り取得は不可）
- リフレッシュトークン方式による認証（APIキーを設定画面で登録）

本アプリの設定画面でプランを選択すると、利用可能な同期機能が切り替わります。

### 5桁コード正規化

J-Quants API は証券コードを **5桁形式**（末尾に `0` を付与）で返します。
本アプリ内部では **4桁コード** で統一しているため、以下の変換を行っています。

```
J-Quants から受信: "12340"  →  内部コード: "1234"
内部コード: "1234"  →  J-Quants API 呼び出し時: "12340"
```

変換は `apps/stocks/infrastructure/external/jquants_client.py` で実装。

### データ同期フロー

```
POST /api/stocks/sync/
  ↓
SyncMarketDataUseCase.execute(sync_type, market)
  ↓ @transaction.atomic
MarketDataProviderResolver  → ApiConfig から有効プロバイダーを動的選択
  ↓
[sync_type=stocks]     StockSyncService     → fetch_stock_list()    → upsert
[sync_type=financials] FinancialSyncService → fetch_financials()    → bulk_save
[sync_type=prices]     PriceSyncService     → fetch_prices()        → bulk_save（増分同期）
  ↓
SyncLog に成功/失敗・件数・エラー詳細を記録
```

**増分同期**：株価データは `t_stock_prices` テーブルの最新日付以降のみ取得するため、
2回目以降の同期は差分のみ処理されます。

---

## yfinance データ連携

J-Quants が利用できない場合や米国株向けのフォールバックとして yfinance を使用。

- JP株: 証券コードに `.T` サフィックスを付与してYahoo Financeからデータ取得（例: `1234.T`）
- US株: ティッカーをそのまま使用（例: `AAPL`）
- `fetch_stock_list()` は yfinance 非対応のため空リストを返す（銘柄一覧は手動登録または J-Quants を利用）

---

## クリーンアーキテクチャ構成

### 各層の責務

| 層 | 責務 | 禁止事項 |
|----|------|---------|
| Presentation | HTTP の入出力・バリデーション | Service の直接呼び出し |
| UseCase | Service の組み合わせ・トランザクション管理 | ORM の直接使用 |
| Service | 単一責任のビジネスロジック | 他の Service の呼び出し |
| Domain | エンティティ・値オブジェクト・リポジトリABC | Django/DRF の import |
| Infrastructure | ORM実装・外部API | ビジネスロジックの記述 |

### DI コンテナ（`config/container.py`）

全ての依存解決は DI コンテナで一元管理します。
View では以下のように UseCase を取得します：

```python
from config import container

class ValuationCalculateView(APIView):
    def post(self, request):
        usecase = container.valuation_service()
        result = usecase.calculate_fair_value(dto)
        ...
```

循環インポート防止のため、コンテナ内ではローカルインポートを使用しています。

---

## 適正株価算出ロジック

現在の実装（`apps/valuations/domain/entities.py`）：

```python
fair_pbr = 1 + growth_rate * 10
fair_value = bps * fair_pbr
discount_rate = (fair_value - current_price) / fair_value
is_undervalued = current_price < fair_value
```

> **将来計画**：ゴードン成長モデル `理論PBR = (ROE - g) / (r - g)` への移行を予定。
> 詳細は `docs/design/app-specification.md` を参照。

---

## データベース構成

### テーブル一覧

| テーブル名 | 種別 | 説明 |
|----------|------|------|
| `m_stocks` | マスタ | 銘柄マスタ（コード・名称・市場・業種） |
| `t_stock_financials` | トランザクション | 財務データ（BPS・EPS・ROE・純資産）年度別 |
| `t_stock_prices` | トランザクション | 日足株価（終値・PBR・出来高） |
| `t_valuations` | トランザクション | 適正価格算出結果 |
| `m_api_configs` | マスタ | 外部API設定（J-Quants・yfinanceのAPIキー・プラン） |
| `t_sync_logs` | トランザクション | データ同期実行ログ（成功/失敗・件数・エラー詳細） |
| `t_watchlist_items` | トランザクション | ウォッチリスト |
| `t_portfolio_items` | トランザクション | ポートフォリオ（保有株・口座種別） |

`m_stocks` には `latest_price` / `latest_price_date` のキャッシュカラムがあり、
一覧表示時の株価参照を高速化しています。

---

## 管理コマンド

`make` コマンド経由で実行（内部で `docker compose exec backend python manage.py ...` を呼び出し）。

| コマンド | 説明 |
|---------|------|
| `make sync-stocks` | 銘柄マスタを外部APIから同期 |
| `make sync-financials` | 財務データを外部APIから同期 |
| `make sync-prices` | 株価データを外部APIから同期（増分） |
| `make sync-all` | 上記3つを順番に実行 |
| `make cleanup-prices` | 古い株価データを削除 |
| `make seed` | 初期データ投入（admin/admin1234） |
| `make createsuperuser` | Django admin スーパーユーザー作成 |

---

## テスト

```bash
# コンテナ内で pytest を実行
make test-backend

# カバレッジ計測（コンテナ内で直接実行）
docker compose exec backend pytest --cov=apps --cov-report=term-missing
```

テスト設定：`DJANGO_SETTINGS_MODULE=config.settings.testing`（`backend/config/settings/testing.py`）。

テストは以下の粒度で記述します：

| 対象 | ファイル配置 | 内容 |
|------|------------|------|
| Domain Entity | `apps/{app}/tests/test_entities.py` | ビジネスロジック・計算結果の検証 |
| Service | `apps/{app}/tests/test_services.py` | モックリポジトリを使ったサービス単体テスト |
| UseCase | `apps/{app}/tests/test_usecases.py` | トランザクション・オーケストレーション検証 |
| API | `apps/{app}/tests/test_views.py` | エンドポイントの入出力・認証・エラーハンドリング |

---

## コード品質

```bash
make lint          # Ruff によるリント
make format        # Ruff による自動フォーマット
make type-check    # mypy による型チェック（strict mode）
```

- **Ruff**: `target-version = "py313"`, `line-length = 120`
- **mypy**: `strict = true`, Django/DRF 型スタブ使用
