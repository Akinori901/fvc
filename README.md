# FVC — Fair Value Calculator

**ゴードン成長モデル（残余利益モデル）** に基づき、株式の理論PBR・適正株価を算出し、現在株価との比較で割安・割高の判断材料を提供する個人投資家向けWebアプリケーションです。

> 本リポジトリは非公開の開発リポジトリからリリース時点のスナップショットを公開しているミラーです（コミット履歴はリリース単位）。

## 主な機能

| 機能 | 説明 |
|------|------|
| 適正PBR算出 | ROE・成長率・資本コストから理論PBRを算出 |
| 適正株価算出 | BPS × 適正PBR で理論株価を提示 |
| 株価評価 | 現在株価を「割安〜危険域」の6段階で評価 |
| 逆算分析 | 現在のPBRから市場が織り込む期待成長率を逆算 |
| シナリオ分析 | 成長率別の適正株価レンジを一覧表示 |
| 米国基準比較 | 米国市場基準のPBRと比較しバブル領域を警告 |
| ポートフォリオ管理 | 保有銘柄の評価・スナップショット・ダッシュボード |
| テクニカル指標 | 移動平均等の指標表示とスクリーニング |
| MCP サーバー | AIエージェント（Claude 等）から対話的に利用できる MCP ツール群 |

理論モデルの詳細は [docs/design/app-specification.md](docs/design/app-specification.md) を参照してください。

## アーキテクチャ

**Clean Architecture + UseCase / Service 分離構成**（Django REST Framework + React のモノレポ）。

```
HTTP Request
  → Presentation (View / Serializer)
  → UseCase（オーケストレーション + @transaction.atomic）
  → Service（単一責任のビジネスロジック）
  → Repository ABC（インターフェース）
  → Repository Impl（Django ORM）
  → Model → DB
```

| ルール | 説明 |
|--------|------|
| View → UseCase のみ | View は Service を直接呼び出さない |
| UseCase = オーケストレーション | Service の組み合わせ + `@transaction.atomic` |
| Service = 単一責任 | 他の Service を呼び出さない |
| Domain = 外部依存ゼロ | Django ORM / DRF を import しない |
| DI Container 経由 | 依存解決は `config/container.py` に集約 |

## 技術スタック

| カテゴリ | 技術 |
|---------|------|
| バックエンド | Python / Django / Django REST Framework |
| フロントエンド | React (TypeScript) / Vite |
| DB | MySQL 8.0 |
| コンテナ | Docker / Docker Compose |
| IaC | Terraform（AWS: Lambda / API Gateway / CloudFront / RDS ほか） |
| 認証 | Amazon Cognito (OAuth) |
| CI/CD | GitHub Actions |

## ローカルでの起動

```bash
cp .env.example .env   # 必要な値を設定
make up                # コンテナ起動（backend / frontend / db / phpmyadmin）
make migrate           # マイグレーション
```

- フロントエンド: http://localhost:3000
- API: http://localhost:18000
- その他のコマンドは `make help` を参照

## データソースについて

株価・財務データの取得は利用者自身の環境・手段で行う構成です。各データ提供元の利用規約に従ってください。本リポジトリは市場データそのものを含みません。

## 免責事項

本アプリケーションは株式評価の理論値を計算する**ツール**であり、投資助言・投資勧誘ではありません。算出結果は理論モデルに基づく参考値であり、正確性・完全性を保証しません。投資判断はご自身の責任で行ってください。

## ライセンス

[MIT](LICENSE)
