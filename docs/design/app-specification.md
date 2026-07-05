# アプリケーション仕様設計書: Fair Value Calculator

## 1. 概要

### 1.1 アプリケーションの目的

**ゴードン成長モデル（残余利益モデル）** に基づき、株式の理論PBR（株価純資産倍率）と適正株価を算出する。
現在の株価と比較して **割安・割高の判断材料** を提供する個人投資家向けWebアプリケーション。

### 1.2 提供する主な情報

| 機能 | 説明 |
|------|------|
| 適正PBR算出 | ROE・成長率・資本コストから理論PBRを算出 |
| 適正株価算出 | BPS × 適正PBR で理論株価を提示 |
| 株価評価 | 現在株価を **[割安 / やや割安 / 適正 / やや割高 / 割高 / 危険域]** で評価 |
| 逆算分析 | 現在のPBRから市場が織り込んでいる **期待成長率** を逆算 |
| シナリオ分析 | 成長率別の適正株価レンジを一覧表示 |
| 米国基準比較 | 米国市場基準のPBRと比較し、バブル領域の警告を提供 |

---

## 2. 算出モデル

### 2.1 基本理論: ゴードン成長モデル（残余利益モデル）

世界共通の株式評価モデル。成長率・ROE・資本コストの3要素から理論PBRを導出する。

#### 2.1.1 理論PBR算出式

```
PBR = (ROE - g) / (r - g)
```

| 変数 | 意味 | 例 |
|------|------|----|
| ROE | 自己資本利益率 | 0.15（15%） |
| g | 永続成長率 | 0.05（5%） |
| r | 資本コスト（株主要求利回り） | 0.08（8%） |

**制約条件**: `g < r` であること。`g >= r` の場合、PBRは理論上無限大となる。

#### 2.1.2 適正株価算出式

```
適正株価 = BPS × 理論PBR
```

| 変数 | 意味 |
|------|------|
| BPS | 1株あたり純資産（Book Value Per Share） |

#### 2.1.3 市場織り込み成長率の逆算式

```
g = (PBR × r - ROE) / (PBR - 1)
```

現在のPBRから、市場が織り込んでいる期待成長率を逆算する。
これにより「市場は何%成長を期待しているか」を定量的に把握できる。

#### 2.1.4 成長ゼロ時の基準PBR

```
基準PBR = ROE / r
```

成長率ゼロの場合のベースラインPBR。ここに成長プレミアムが上乗せされる。

### 2.2 資本コスト（r）のデフォルト値

資本コストは `無リスク金利 + リスクプレミアム` で構成される。

| 市場 | 無リスク金利 | リスクプレミアム | 資本コスト(r) | デフォルト値 |
|------|------------|----------------|-------------|------------|
| 日本株 | 0.5〜1.5% | 5〜6% | 6〜9% | **8%** |
| 米国株 | 4〜5% | 5〜6% | 9〜11% | **10%** |

ユーザーはデフォルト値を使用するか、任意の値を入力できる。

### 2.3 市場別のパラメータ比較

| 項目 | 日本株 | 米国株 |
|------|--------|--------|
| 平均ROE | 8〜12% | 15〜25% |
| 永続成長率 | 1〜4% | 3〜6% |
| 平均PBR | 1〜2倍 | 3〜5倍 |
| 資本コスト | 6〜9% | 9〜11% |

---

## 3. 株価評価ゾーン

### 3.1 評価ゾーン定義

現在のPBRと理論PBRの乖離率に基づいて、6段階の評価を行う。

```
乖離率 = (現在PBR - 理論PBR) / 理論PBR × 100
```

| 評価 | 乖離率 | 説明 | カラーコード |
|------|--------|------|------------|
| 割安 | -30%以下 | 理論値を大きく下回る。買い検討 | 🟢 緑 |
| やや割安 | -30% 〜 -10% | やや割安。買い方向 | 🟢 薄緑 |
| 適正 | -10% 〜 +10% | 適正範囲 | 🔵 青 |
| やや割高 | +10% 〜 +30% | やや割高。成長前提なら許容 | 🟡 黄 |
| 割高 | +30% 〜 +50% | 割高。利確検討 | 🟠 橙 |
| 危険域 | +50%超、または米国基準PBR上限超過 | バブル領域。強い警告 | 🔴 赤 |

### 3.2 米国基準によるバブル判定（危険域の追加条件）

日本基準で「やや割高」でも、**米国グロース株基準のPBR上限を超えた場合**は「危険域」と評価する。

```
米国基準PBR = (ROE - g) / (r_us - g)    ※ r_us = 10%
```

**判定ロジック**:
```
if 現在PBR > 米国基準PBR × 2.0:
    評価 = "危険域"
```

米国では高成長株でもPBR 20倍を超えると過熱とされるため、この基準を天井ラインとして利用する。

### 3.3 米国グロース株PBRの経験的レンジ

| 企業タイプ | PBR範囲 |
|-----------|---------|
| 低成長 | 2〜4倍 |
| 普通成長 | 4〜6倍 |
| 高成長 | 6〜10倍 |
| 超高成長 | 10〜20倍 |
| バブル | 20倍以上 |

---

## 4. 機能仕様

### 4.1 UC-01: 適正株価算出（メイン機能）

#### 概要
銘柄を選択し、パラメータを入力して適正PBR・適正株価を算出する。

#### 入力パラメータ

| パラメータ | 型 | 必須 | デフォルト | 説明 |
|-----------|-----|------|-----------|------|
| stock_code | string | ○ | - | 証券コード |
| roe | decimal | ○ | - | ROE（%） |
| growth_rate | decimal | ○ | - | 永続成長率（%） |
| cost_of_capital | decimal | △ | 8.0（日本）/ 10.0（米国） | 資本コスト（%） |
| bps | decimal | ○ | - | 1株あたり純資産（円） |
| current_price | decimal | ○ | - | 現在株価（円） |
| market_type | string | △ | "JP" | 市場タイプ（"JP" / "US"） |

#### 出力

| 項目 | 型 | 説明 |
|------|-----|------|
| fair_pbr | decimal | 理論PBR |
| fair_value | decimal | 適正株価（円） |
| current_pbr | decimal | 現在PBR |
| discount_rate | decimal | 乖離率（%） |
| evaluation | string | 評価ゾーン（割安〜危険域） |
| implied_growth_rate | decimal | 市場織り込み成長率（%） |
| us_fair_pbr | decimal | 米国基準の理論PBR |
| us_bubble_threshold | decimal | 米国基準バブルライン株価（円） |
| base_pbr | decimal | 成長ゼロ時の基準PBR |
| scenarios | array | 成長率別シナリオ一覧 |

#### 成長率別シナリオ（scenarios）

入力された成長率を中心に、複数の成長率シナリオでの適正株価を自動算出する。

| シナリオ成長率 | 説明 |
|--------------|------|
| 0% | 成長なし |
| 2% | 低成長 |
| 3% | 日本企業平均 |
| 4% | やや高成長 |
| 5% | 高成長 |
| 6% | 非常に高成長 |
| 入力値 | ユーザー指定の成長率 |

各シナリオの出力:

```json
{
  "growth_rate": 5.0,
  "fair_pbr": 11.0,
  "fair_value": 3355,
  "evaluation": "割安"
}
```

#### 算出フロー

```
1. 入力バリデーション
   ├─ g >= r の場合 → エラー「成長率が資本コスト以上です。理論PBRは算出不可」
   └─ PBR = 1 の場合（逆算時） → エラー「PBR=1では逆算不可」

2. 理論PBR算出
   fair_pbr = (ROE - g) / (r - g)

3. 適正株価算出
   fair_value = BPS × fair_pbr

4. 現在PBR算出
   current_pbr = current_price / BPS

5. 乖離率算出
   discount_rate = (current_pbr - fair_pbr) / fair_pbr

6. 市場織り込み成長率の逆算
   implied_growth_rate = (current_pbr × r - ROE) / (current_pbr - 1)

7. 評価ゾーン判定
   ├─ 日本基準: 乖離率に基づく6段階評価
   └─ 米国基準: 米国基準PBRの2倍超 → 危険域

8. 米国基準PBR算出
   us_fair_pbr = (ROE - g) / (0.10 - g)

9. 成長率別シナリオ生成
   各成長率でステップ2〜7を繰り返す

10. 結果保存 & レスポンス返却
```

### 4.2 UC-02: 市場織り込み成長率の逆算

#### 概要
現在の株価（PBR）から、市場が織り込んでいる期待成長率を逆算する。

#### 入力

| パラメータ | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| stock_code | string | ○ | 証券コード |
| roe | decimal | ○ | ROE（%） |
| current_price | decimal | ○ | 現在株価（円） |
| bps | decimal | ○ | BPS（円） |
| cost_of_capital | decimal | △ | 資本コスト（%） |

#### 出力

| 項目 | 説明 |
|------|------|
| implied_growth_rate | 市場織り込み成長率（%） |
| growth_rate_evaluation | 成長率の評価（普通/優秀/非常に優秀/かなり強気） |
| current_pbr | 現在PBR |

#### 成長率評価基準

| 永続成長率 | 評価 |
|-----------|------|
| 2〜3% | 普通 |
| 3〜5% | 優秀 |
| 5〜7% | 非常に優秀 |
| 7%以上 | かなり強気 |

### 4.3 UC-03: 銘柄管理

#### 概要
分析対象の銘柄を登録・管理する。財務データ（BPS, ROE等）と株価を紐付ける。

#### 機能一覧

| 機能 | 説明 |
|------|------|
| 銘柄登録 | 証券コード・銘柄名・市場区分・業種を登録 |
| 財務データ登録 | 年度ごとのBPS・EPS・ROE・純資産・発行済株式数を登録 |
| 株価登録 | 日付ごとの終値・PBRを登録 |
| 銘柄一覧 | 登録銘柄の一覧を表示 |
| 銘柄詳細 | 銘柄の財務データ・株価推移・算出履歴を表示 |

### 4.4 UC-04: 算出履歴管理

#### 概要
過去の算出結果を保存し、時系列で振り返る。

#### 機能

| 機能 | 説明 |
|------|------|
| 算出結果保存 | 毎回の算出結果をDBに自動保存 |
| 履歴一覧 | 銘柄別・日付別で過去の算出結果を一覧表示 |
| 評価推移 | 同一銘柄の評価が時系列でどう変化したかを表示 |

---

## 5. データモデル（変更点）

### 5.1 t_valuations テーブル: 拡張カラム

現行のt_valuationsテーブルに以下のカラムを追加する。

| カラム | 型 | 説明 | 新規/変更 |
|-------|-----|------|----------|
| id | BIGINT PK | - | 既存 |
| stock_id | BIGINT FK | 銘柄ID | 既存 |
| calculated_at | DATETIME | 算出日時 | 既存 |
| growth_rate | DECIMAL(8,4) | 入力した永続成長率 | 既存 |
| roe | DECIMAL(8,4) | 使用したROE | **新規** |
| cost_of_capital | DECIMAL(8,4) | 使用した資本コスト | **新規** |
| market_type | VARCHAR(2) | 市場タイプ（JP/US） | **新規** |
| bps | DECIMAL(12,2) | 使用したBPS | **新規** |
| fair_pbr | DECIMAL(8,4) | 算出した理論PBR | 既存 |
| fair_value | DECIMAL(12,2) | 適正株価 | 既存 |
| current_price | DECIMAL(12,2) | 算出時の現在株価 | 既存 |
| current_pbr | DECIMAL(8,4) | 算出時の現在PBR | **新規** |
| discount_rate | DECIMAL(8,4) | 乖離率 | 既存 |
| is_undervalued | BOOLEAN | 割安判定 | 既存 |
| evaluation | VARCHAR(10) | 評価ゾーン（割安〜危険域） | **新規** |
| implied_growth_rate | DECIMAL(8,4) | 市場織り込み成長率 | **新規** |
| us_fair_pbr | DECIMAL(8,4) | 米国基準の理論PBR | **新規** |
| created_at | DATETIME | 作成日時 | 既存 |

### 5.2 m_market_defaults テーブル: 新規

市場別のデフォルトパラメータを管理する。

| カラム | 型 | 説明 |
|-------|-----|------|
| id | BIGINT PK | - |
| market_type | VARCHAR(2) UNIQUE | 市場タイプ（JP/US） |
| name | VARCHAR(50) | 市場名（日本/米国） |
| default_cost_of_capital | DECIMAL(8,4) | デフォルト資本コスト |
| avg_roe_min | DECIMAL(8,4) | 平均ROE下限 |
| avg_roe_max | DECIMAL(8,4) | 平均ROE上限 |
| avg_growth_min | DECIMAL(8,4) | 平均成長率下限 |
| avg_growth_max | DECIMAL(8,4) | 平均成長率上限 |
| avg_pbr_min | DECIMAL(8,4) | 平均PBR下限 |
| avg_pbr_max | DECIMAL(8,4) | 平均PBR上限 |
| created_at | DATETIME | 作成日時 |
| updated_at | DATETIME | 更新日時 |

**初期データ**:

| market_type | name | default_cost_of_capital | avg_roe_min/max | avg_growth_min/max |
|-------------|------|------------------------|-----------------|-------------------|
| JP | 日本 | 0.0800 | 0.0800 / 0.1200 | 0.0100 / 0.0400 |
| US | 米国 | 0.1000 | 0.1500 / 0.2500 | 0.0300 / 0.0600 |

---

## 6. API エンドポイント設計（変更・追加分）

### 6.1 適正株価算出 API（変更）

**POST** `/api/valuations/calculate/`

リクエスト:
```json
{
  "stock_code": "5892",
  "roe": 38.39,
  "growth_rate": 5.0,
  "cost_of_capital": 8.0,
  "bps": 305.6,
  "current_price": 2000,
  "market_type": "JP"
}
```

レスポンス:
```json
{
  "id": 1,
  "stock": {
    "code": "5892",
    "name": "yutori"
  },
  "input_params": {
    "roe": 38.39,
    "growth_rate": 5.0,
    "cost_of_capital": 8.0,
    "bps": 305.6,
    "current_price": 2000,
    "market_type": "JP"
  },
  "results": {
    "fair_pbr": 11.13,
    "fair_value": 3401,
    "current_pbr": 6.54,
    "discount_rate": -41.14,
    "evaluation": "割安",
    "base_pbr": 4.80,
    "implied_growth_rate": 2.53
  },
  "us_comparison": {
    "us_fair_pbr": 6.68,
    "us_bubble_threshold_pbr": 13.36,
    "us_bubble_threshold_price": 4083,
    "is_us_bubble": false
  },
  "scenarios": [
    {"growth_rate": 0.0, "fair_pbr": 4.80, "fair_value": 1466, "evaluation": "割高"},
    {"growth_rate": 2.0, "fair_pbr": 6.07, "fair_value": 1854, "evaluation": "やや割高"},
    {"growth_rate": 3.0, "fair_pbr": 7.08, "fair_value": 2163, "evaluation": "適正"},
    {"growth_rate": 4.0, "fair_pbr": 8.60, "fair_value": 2627, "evaluation": "やや割安"},
    {"growth_rate": 5.0, "fair_pbr": 11.13, "fair_value": 3401, "evaluation": "割安"},
    {"growth_rate": 6.0, "fair_pbr": 16.20, "fair_value": 4949, "evaluation": "割安"}
  ],
  "calculated_at": "2026-02-25T12:00:00Z"
}
```

### 6.2 逆算分析 API（新規）

**POST** `/api/valuations/reverse-calculate/`

リクエスト:
```json
{
  "stock_code": "5892",
  "roe": 38.39,
  "current_price": 2000,
  "bps": 305.6,
  "cost_of_capital": 8.0
}
```

レスポンス:
```json
{
  "stock": {
    "code": "5892",
    "name": "yutori"
  },
  "current_pbr": 6.54,
  "implied_growth_rate": 2.53,
  "growth_rate_evaluation": "普通",
  "interpretation": "市場は永続成長率 約2.5% を織り込んでいます"
}
```

### 6.3 市場デフォルト取得 API（新規）

**GET** `/api/markets/defaults/`

レスポンス:
```json
[
  {
    "market_type": "JP",
    "name": "日本",
    "default_cost_of_capital": 8.0,
    "avg_roe": {"min": 8.0, "max": 12.0},
    "avg_growth": {"min": 1.0, "max": 4.0},
    "avg_pbr": {"min": 1.0, "max": 2.0}
  },
  {
    "market_type": "US",
    "name": "米国",
    "default_cost_of_capital": 10.0,
    "avg_roe": {"min": 15.0, "max": 25.0},
    "avg_growth": {"min": 3.0, "max": 6.0},
    "avg_pbr": {"min": 3.0, "max": 5.0}
  }
]
```

---

## 7. ドメインモデル設計

### 7.1 FairValueCalculation エンティティ（変更）

現行の簡易モデル `PBR = 1 + growth_rate × 10` を、ゴードン成長モデルに置き換える。

```python
@dataclass
class FairValueCalculation:
    """適正株価の計算エンティティ（ゴードン成長モデル）"""

    roe: Decimal           # ROE（例: 0.15 = 15%）
    growth_rate: Decimal   # 永続成長率（例: 0.05 = 5%）
    cost_of_capital: Decimal  # 資本コスト（例: 0.08 = 8%）
    bps: Decimal           # 1株あたり純資産
    current_price: Decimal # 現在株価

    @property
    def fair_pbr(self) -> Decimal:
        """理論PBR = (ROE - g) / (r - g)"""
        denominator = self.cost_of_capital - self.growth_rate
        if denominator <= 0:
            raise ValueError("成長率が資本コスト以上のため算出不可")
        return ((self.roe - self.growth_rate) / denominator).quantize(Decimal("0.01"))

    @property
    def fair_value(self) -> Decimal:
        """適正株価 = BPS × 理論PBR"""
        return (self.bps * self.fair_pbr).quantize(Decimal("1"))

    @property
    def current_pbr(self) -> Decimal:
        """現在PBR = 現在株価 / BPS"""
        if self.bps == 0:
            return Decimal("0")
        return (self.current_price / self.bps).quantize(Decimal("0.01"))

    @property
    def discount_rate(self) -> Decimal:
        """乖離率 = (現在PBR - 理論PBR) / 理論PBR"""
        if self.fair_pbr == 0:
            return Decimal("0")
        return ((self.current_pbr - self.fair_pbr) / self.fair_pbr).quantize(Decimal("0.0001"))

    @property
    def implied_growth_rate(self) -> Decimal:
        """市場織り込み成長率 = (PBR × r - ROE) / (PBR - 1)"""
        pbr = self.current_pbr
        if pbr == 1:
            raise ValueError("PBR=1では逆算不可")
        return ((pbr * self.cost_of_capital - self.roe) / (pbr - 1)).quantize(Decimal("0.0001"))

    @property
    def base_pbr(self) -> Decimal:
        """成長ゼロ時の基準PBR = ROE / r"""
        if self.cost_of_capital == 0:
            return Decimal("0")
        return (self.roe / self.cost_of_capital).quantize(Decimal("0.01"))

    @property
    def evaluation(self) -> str:
        """評価ゾーン判定"""
        ...  # 3.1 節の評価ロジック

    @property
    def is_undervalued(self) -> bool:
        """割安判定"""
        return self.current_price < self.fair_value
```

### 7.2 USComparison 値オブジェクト（新規）

```python
@dataclass(frozen=True)
class USComparison:
    """米国基準比較"""

    us_cost_of_capital: Decimal = Decimal("0.10")

    def calculate_us_fair_pbr(self, roe: Decimal, growth_rate: Decimal) -> Decimal:
        """米国基準の理論PBR"""
        denominator = self.us_cost_of_capital - growth_rate
        if denominator <= 0:
            raise ValueError("算出不可")
        return (roe - growth_rate) / denominator

    def is_bubble(self, current_pbr: Decimal, us_fair_pbr: Decimal) -> bool:
        """米国基準でバブル判定（理論PBRの2倍超）"""
        return current_pbr > us_fair_pbr * 2
```

### 7.3 EvaluationZone 値オブジェクト（新規）

```python
class EvaluationZone(str, Enum):
    """評価ゾーン"""
    UNDERVALUED = "割安"
    SLIGHTLY_UNDERVALUED = "やや割安"
    FAIR = "適正"
    SLIGHTLY_OVERVALUED = "やや割高"
    OVERVALUED = "割高"
    DANGER = "危険域"

    @classmethod
    def from_discount_rate(cls, discount_rate: Decimal, is_us_bubble: bool) -> "EvaluationZone":
        if is_us_bubble or discount_rate > Decimal("0.50"):
            return cls.DANGER
        if discount_rate > Decimal("0.30"):
            return cls.OVERVALUED
        if discount_rate > Decimal("0.10"):
            return cls.SLIGHTLY_OVERVALUED
        if discount_rate > Decimal("-0.10"):
            return cls.FAIR
        if discount_rate > Decimal("-0.30"):
            return cls.SLIGHTLY_UNDERVALUED
        return cls.UNDERVALUED
```

---

## 8. 画面設計

### 8.1 画面一覧

| 画面ID | 画面名 | URL | 説明 |
|--------|--------|-----|------|
| S-01 | ダッシュボード | `/` | 登録銘柄の評価サマリー一覧 |
| S-02 | 銘柄一覧 | `/stocks` | 登録銘柄の管理 |
| S-03 | 銘柄詳細 | `/stocks/:code` | 銘柄の財務・株価・評価履歴 |
| S-04 | 適正株価算出 | `/valuations/calculate` | メイン算出画面 |
| S-05 | 算出結果詳細 | `/valuations/:id` | 算出結果の詳細表示 |
| S-06 | 算出履歴 | `/valuations` | 過去の算出結果一覧 |

### 8.2 S-04: 適正株価算出画面（メイン画面）

#### レイアウト

```
┌─────────────────────────────────────────────────────────┐
│ Fair Value Calculator                                    │
├─────────────────────────────────────────────────────────┤
│                                                          │
│ ┌─ 入力パネル ────────────────────────────────────────┐ │
│ │ 銘柄: [5892 ▼]  市場: (●JP ○US)                    │ │
│ │                                                      │ │
│ │ ROE:        [38.39] %    BPS:    [305.6] 円         │ │
│ │ 成長率:     [ 5.0 ] %    現在株価: [2000] 円        │ │
│ │ 資本コスト: [ 8.0 ] %    ← 市場選択で自動切替      │ │
│ │                                                      │ │
│ │                          [ 算出する ]                │ │
│ └──────────────────────────────────────────────────────┘ │
│                                                          │
│ ┌─ 算出結果 ──────────────────────────────────────────┐ │
│ │                                                      │ │
│ │  評価: 🟢 割安                                       │ │
│ │                                                      │ │
│ │  ┌──────────┬──────────┬──────────┬──────────┐      │ │
│ │  │ 理論PBR  │ 適正株価  │ 現在PBR  │ 乖離率   │      │ │
│ │  │ 11.13倍  │ 3,401円  │ 6.54倍   │ -41.1%  │      │ │
│ │  └──────────┴──────────┴──────────┴──────────┘      │ │
│ │                                                      │ │
│ │  市場織り込み成長率: 2.5% (普通)                      │ │
│ │  成長ゼロ時PBR: 4.80倍                               │ │
│ │                                                      │ │
│ │  ┌─ 米国基準比較 ─────────────────────────────────┐ │ │
│ │  │ 米国基準PBR: 6.68倍                             │ │ │
│ │  │ バブルライン: 4,083円 (PBR 13.36倍)             │ │ │
│ │  │ 判定: 正常範囲                                   │ │ │
│ │  └────────────────────────────────────────────────┘ │ │
│ │                                                      │ │
│ └──────────────────────────────────────────────────────┘ │
│                                                          │
│ ┌─ 成長率シナリオ ────────────────────────────────────┐ │
│ │                                                      │ │
│ │  成長率 │ 理論PBR │ 適正株価 │ 評価     │ ゲージ   │ │
│ │  ───────┼─────────┼──────────┼──────────┼────────  │ │
│ │    0%   │  4.80   │  1,466円 │ 割高     │ ████░░  │ │
│ │    2%   │  6.07   │  1,854円 │ やや割高 │ ███░░░  │ │
│ │    3%   │  7.08   │  2,163円 │ 適正     │ ██░░░░  │ │
│ │  ▶ 5%   │ 11.13   │  3,401円 │ 割安     │ █░░░░░  │ │
│ │    6%   │ 16.20   │  4,949円 │ 割安     │ ░░░░░░  │ │
│ │                                                      │ │
│ │  ※ ▶ = ユーザー入力値                                │ │
│ └──────────────────────────────────────────────────────┘ │
│                                                          │
│ ┌─ 株価レンジ ────────────────────────────────────────┐ │
│ │                                                      │ │
│ │  割安     やや割安   適正    やや割高  割高   危険域  │ │
│ │  |--------|---------|--------|---------|------|------| │ │
│ │  0    2,163     2,829   3,401   3,973  4,545  4,949  │ │
│ │               ▲ 現在: 2,000円                        │ │
│ │                                                      │ │
│ └──────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### 8.3 S-01: ダッシュボード

登録銘柄の最新評価を一覧表示する。

```
┌─────────────────────────────────────────────────────────┐
│ Dashboard                                                │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  コード │ 銘柄名     │ 現在株価  │ 適正株価 │ 評価     │ │
│  ───────┼───────────┼──────────┼──────────┼──────────│ │
│  5892   │ yutori     │ 2,000円  │ 3,401円 │ 🟢割安   │ │
│  7203   │ トヨタ自動車│ 2,500円  │ 2,400円 │ 🔵適正   │ │
│  9984   │ SBG       │ 9,500円  │ 7,200円 │ 🟡やや割高│ │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## 9. エラーハンドリング

### 9.1 ビジネスルールエラー

| エラーコード | 条件 | メッセージ |
|------------|------|-----------|
| GROWTH_EXCEEDS_COST | g >= r | 成長率が資本コスト以上のため、理論PBRを算出できません。成長率または資本コストを見直してください。 |
| PBR_EQUALS_ONE | 現在PBR = 1.0 | PBR=1.0では市場織り込み成長率を逆算できません。 |
| BPS_ZERO | BPS = 0 | BPS(1株あたり純資産)が0のため、PBRを算出できません。 |
| NEGATIVE_ROE | ROE < 0 | ROEが負の値のため、本モデルでの算出は不適切です。 |

### 9.2 注意喚起メッセージ

| 条件 | メッセージ |
|------|-----------|
| g が r の90%以上 | 成長率が資本コストに近く、PBRが極端に高くなっています。結果の信頼性が低い可能性があります。 |
| 理論PBR > 30 | 理論PBRが30倍を超えています。現実的には5〜15倍程度に収束することが一般的です。 |
| 逆算成長率 > 10% | 市場は非常に高い成長率を織り込んでいます。成長鈍化時のリスクに注意してください。 |

---

## 10. 計算例（検証用）

### 10.1 yutori（5892）の算出例

**入力**:
- ROE: 38.39%, g: 5.0%, r: 8.0%, BPS: 305.6円, 現在株価: 2,000円

**算出過程**:

```
1. 理論PBR = (0.3839 - 0.05) / (0.08 - 0.05)
           = 0.3339 / 0.03
           = 11.13

2. 適正株価 = 305.6 × 11.13
            = 3,401円

3. 現在PBR = 2,000 / 305.6
           = 6.54

4. 乖離率 = (6.54 - 11.13) / 11.13
          = -41.2%

5. 市場織り込み成長率 = (6.54 × 0.08 - 0.3839) / (6.54 - 1)
                     = (0.5232 - 0.3839) / 5.54
                     = 0.0251 = 2.5%

6. 評価ゾーン: 乖離率 -41.2% → 割安

7. 米国基準PBR = (0.3839 - 0.05) / (0.10 - 0.05)
              = 0.3339 / 0.05
              = 6.68

8. バブルライン = 6.68 × 2 = 13.36 → 現在PBR 6.54 < 13.36 → 正常
```

### 10.2 低成長企業の算出例

**入力**:
- ROE: 12%, g: 2%, r: 8%, BPS: 612円, 現在株価: 436円

**算出過程**:

```
1. 理論PBR = (0.12 - 0.02) / (0.08 - 0.02)
           = 0.10 / 0.06
           = 1.67

2. 適正株価 = 612 × 1.67 = 1,022円

3. 現在PBR = 436 / 612 = 0.71

4. 乖離率 = (0.71 - 1.67) / 1.67 = -57.5% → 割安
```

---

## 11. 将来拡張（スコープ外・メモ）

以下は初期スコープには含めないが、将来的に検討する機能。

| 機能 | 説明 |
|------|------|
| 2段階成長モデル | 短期高成長→長期安定成長の段階モデル |
| 外部API連携 | Yahoo Finance等からの自動データ取得 |
| PER基準の算出 | PBRだけでなくPERベースの適正株価算出 |
| ポートフォリオ管理 | 保有銘柄の一括評価・資産配分表示 |
| アラート機能 | 株価が割安ゾーンに入った際の通知 |
| 決算データ自動取得 | EDINETからの財務データ自動取得 |

---

## 12. 非機能要件

| 項目 | 要件 |
|------|------|
| パフォーマンス | 算出APIのレスポンス: 500ms以内 |
| データ保持 | 算出履歴は無期限保持 |
| 同時利用者 | 個人利用のため1ユーザー |
| セキュリティ | 初期段階では認証不要。公開時は要検討 |
| ブラウザ対応 | Chrome最新版 |
