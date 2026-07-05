from dataclasses import dataclass
from decimal import Decimal

# 市場別デフォルト資本コスト
MARKET_COST_OF_CAPITAL: dict[str, Decimal] = {
    "JP": Decimal("0.08"),  # 日本株: 8%
    "US": Decimal("0.10"),  # 米国株: 10%
}

# 成長率評価ラベルのしきい値（高い順）
_GROWTH_RATE_LABEL_THRESHOLDS: list[tuple[Decimal, str]] = [
    (Decimal("0.07"), "かなり強気"),
    (Decimal("0.05"), "非常に優秀"),
    (Decimal("0.03"), "優秀"),
    (Decimal("0.02"), "普通"),
    (Decimal("0.00"), "低成長"),
]


def growth_rate_label(rate: Decimal) -> str:
    """市場折込成長率を評価ラベルに変換する。"""
    for threshold, label in _GROWTH_RATE_LABEL_THRESHOLDS:
        if rate >= threshold:
            return label
    return "マイナス成長"


@dataclass
class FairValueCalculation:
    """適正株価の計算エンティティ（ゴードン成長モデル）

    ゴードン成長モデルに基づき、ROE・成長率・資本コストから適正PBRを算出し、
    現在の株価と比較して割安・割高を判断する。

    適正PBR算出ロジック:
      理論PBR = (ROE - g) / (r - g)
      r: 資本コスト（JP=8%, US=10%）, g: 永続成長率

    制約:
      g < r である必要がある（成長率が資本コストを超えるとモデルが成立しない）
      BPS > 0 である必要がある
    """

    growth_rate: Decimal  # g: 永続成長率（例: 0.05 = 5%）
    bps: Decimal  # 1株あたり純資産
    current_price: Decimal  # 現在株価
    roe: Decimal  # 自己資本利益率（例: 0.38 = 38%）
    cost_of_capital: Decimal  # r: 資本コスト（市場別定数）

    @property
    def fair_pbr(self) -> Decimal:
        """適正PBR = (ROE - g) / (r - g)"""
        denominator = self.cost_of_capital - self.growth_rate
        return (self.roe - self.growth_rate) / denominator

    @property
    def fair_value(self) -> Decimal:
        """適正株価 = BPS × 適正PBR"""
        return (self.bps * self.fair_pbr).quantize(Decimal("0.01"))

    @property
    def current_pbr(self) -> Decimal:
        """現在PBR = 現在株価 / BPS"""
        return (self.current_price / self.bps).quantize(Decimal("0.0001"))

    @property
    def discount_rate(self) -> Decimal:
        """割引率 = (適正株価 - 現在株価) / 適正株価

        正の値: 割安（現在株価が適正価格より低い）
        負の値: 割高（現在株価が適正価格より高い）
        """
        if self.fair_value == 0:
            return Decimal("0")
        return ((self.fair_value - self.current_price) / self.fair_value).quantize(Decimal("0.0001"))

    @property
    def is_undervalued(self) -> bool:
        """割安判定: 現在の株価が適正株価より低い"""
        return self.current_price < self.fair_value

    @property
    def implied_growth_rate(self) -> Decimal:
        """市場織り込み成長率 = (PBR × r - ROE) / (PBR - 1)

        現在のPBRから、市場が期待している永続成長率を逆算する。
        PBR ≈ 1 では分母がゼロに近づき計算不能（特異点）。
        """
        pbr = self.current_pbr
        if abs(pbr - Decimal("1")) < Decimal("0.05"):
            raise ZeroDivisionError("implied_growth_rate undefined near PBR=1")
        return ((pbr * self.cost_of_capital - self.roe) / (pbr - Decimal("1"))).quantize(Decimal("0.0001"))


@dataclass
class ValuationResult:
    """算出結果エンティティ"""

    stock_id: int
    user_id: int
    growth_rate: Decimal
    fair_pbr: Decimal
    fair_value: Decimal
    current_price: Decimal
    discount_rate: Decimal
    is_undervalued: bool
    id: int | None = None
    # ゴードン成長モデル追加フィールド（nullable: 旧レコードとの互換性）
    roe: Decimal | None = None
    cost_of_capital: Decimal | None = None
    bps: Decimal | None = None
    current_pbr: Decimal | None = None
    implied_growth_rate: Decimal | None = None
