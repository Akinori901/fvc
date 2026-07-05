from django.conf import settings
from django.db import models

# ============================================================
# 家族ポートフォリオ管理（新機能）
# ============================================================


class FamilyMember(models.Model):
    """家族メンバーマスタ"""

    class Role(models.TextChoices):
        SELF = "self", "本人"
        SPOUSE = "spouse", "配偶者"
        CHILD = "child", "子"
        PARENT = "parent", "親"
        OTHER = "other", "その他"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="family_members",
    )
    name = models.CharField("名前", max_length=50)
    role = models.CharField("役割", max_length=20, choices=Role.choices, default=Role.SELF)
    color_code = models.CharField("カラーコード", max_length=7, default="#1976d2")
    display_order = models.IntegerField("表示順", default=0)
    include_in_family_total = models.BooleanField("家族合算に含める", default=True)

    class Meta:
        db_table = "m_family_members"
        ordering = ["display_order", "id"]
        verbose_name = "家族メンバー"
        verbose_name_plural = "家族メンバー"

    def __str__(self) -> str:
        return f"{self.user} - {self.name}"


class PortfolioAccount(models.Model):
    """口座マスタ"""

    class InstitutionType(models.TextChoices):
        SECURITIES_JP = "securities_jp", "国内証券"
        SECURITIES_US = "securities_us", "米国証券"
        BANK = "bank", "銀行"
        IDECO = "ideco", "iDeCo"
        MUTUAL_AID = "mutual_aid", "小規模企業共済"
        COMPANY_LOAN = "company_loan", "会社貸付"
        INSURANCE = "insurance", "保険"
        PENSION = "pension", "年金"
        OTHER = "other", "その他"

    class TradingType(models.TextChoices):
        SPOT = "spot", "現物"
        MARGIN = "margin", "信用"

    class MarginCreditType(models.TextChoices):
        SYSTEM_6M = "system_6m", "制度信用 (6ヶ月)"
        GENERAL_6M = "general_6m", "一般信用 (6ヶ月)"
        GENERAL_UNLIMITED = "general_unlimited", "一般信用 (無期限)"

    class AssetClass(models.TextChoices):
        CASH = "cash", "現金・預金"
        JP_STOCK = "jp_stock", "国内株式"
        US_STOCK = "us_stock", "米国株式"
        JP_BOND = "jp_bond", "国内債券"
        US_BOND = "us_bond", "米国債"
        ETF = "etf", "ETF"
        FUND = "fund", "投資信託"
        INSURANCE = "insurance", "保険"
        MUTUAL_AID = "mutual_aid", "共済"
        LOAN = "loan", "貸付"
        REAL_ESTATE = "real_estate", "不動産・土地"
        OTHER = "other", "その他"

    family_member = models.ForeignKey(
        FamilyMember,
        on_delete=models.CASCADE,
        related_name="accounts",
    )
    institution = models.CharField("機関名", max_length=100)
    institution_type = models.CharField("機関種別", max_length=30, choices=InstitutionType.choices)
    asset_class = models.CharField("資産クラス", max_length=30, choices=AssetClass.choices)
    trading_type = models.CharField("取引方式", max_length=20, choices=TradingType.choices, default=TradingType.SPOT)
    nickname = models.CharField("表示名", max_length=100, blank=True)
    currency = models.CharField("通貨", max_length=3, default="JPY")
    notes = models.TextField("メモ", blank=True)
    is_active = models.BooleanField("有効", default=True)
    expected_return_rate = models.DecimalField(
        "期待リターン率(%)", max_digits=5, decimal_places=2, null=True, blank=True
    )
    margin_credit_type = models.CharField(
        "信用枠区分",
        max_length=30,
        choices=MarginCreditType.choices,
        null=True,
        blank=True,
        help_text="trading_type=margin のときに設定。期限・現引き計算に使用",
    )
    margin_interest_rate = models.DecimalField(
        "信用金利 (年率)",
        max_digits=5,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="例: 0.0285 = 年率 2.85%",
    )

    class Meta:
        db_table = "m_portfolio_accounts"
        ordering = ["family_member__display_order", "institution"]
        verbose_name = "口座"
        verbose_name_plural = "口座"

    def __str__(self) -> str:
        return f"{self.family_member.name} - {self.institution}"


class AccountSnapshot(models.Model):
    """月次スナップショット"""

    account = models.ForeignKey(
        PortfolioAccount,
        on_delete=models.CASCADE,
        related_name="snapshots",
    )
    snapshot_date = models.DateField("記録日")
    total_value_jpy = models.DecimalField("評価額(円)", max_digits=16, decimal_places=0)
    total_cost_jpy = models.DecimalField("取得原価(円)", max_digits=16, decimal_places=0, null=True, blank=True)
    exchange_rate = models.DecimalField("為替レート", max_digits=10, decimal_places=4, null=True, blank=True)
    notes = models.TextField("メモ", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "t_account_snapshots"
        unique_together = [["account", "snapshot_date"]]
        ordering = ["-snapshot_date"]
        verbose_name = "月次スナップショット"
        verbose_name_plural = "月次スナップショット"

    def __str__(self) -> str:
        return f"{self.account} {self.snapshot_date} ¥{self.total_value_jpy:,}"


class AccountHolding(models.Model):
    """個別保有明細"""

    class AssetType(models.TextChoices):
        STOCK = "stock", "株式"
        ETF = "etf", "ETF"
        FUND = "fund", "投資信託"
        BOND = "bond", "債券"
        CASH = "cash", "現金"
        OTHER = "other", "その他"

    snapshot = models.ForeignKey(
        AccountSnapshot,
        on_delete=models.CASCADE,
        related_name="holdings",
    )
    stock = models.ForeignKey(
        "stocks.Stock",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="account_holdings",
        verbose_name="銘柄",
    )
    proxy_stock = models.ForeignKey(
        "stocks.Stock",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="proxy_holdings",
        verbose_name="プロキシETF",
    )
    ticker_code = models.CharField("ティッカー", max_length=20, blank=True)
    asset_name = models.CharField("銘柄・商品名", max_length=255)
    asset_type = models.CharField("資産種別", max_length=20, choices=AssetType.choices)
    quantity = models.DecimalField("数量", max_digits=16, decimal_places=4, null=True, blank=True)
    unit_price = models.DecimalField("単価", max_digits=16, decimal_places=4, null=True, blank=True)
    value_jpy = models.DecimalField("評価額(円)", max_digits=16, decimal_places=0)
    cost_jpy = models.DecimalField("取得原価(円)", max_digits=16, decimal_places=0, null=True, blank=True)
    built_date = models.DateField(
        "建玉日",
        null=True,
        blank=True,
        help_text="信用建玉の建玉日。未設定時は snapshot_date を fallback として扱う",
    )

    class Meta:
        db_table = "t_account_holdings"
        verbose_name = "個別保有明細"
        verbose_name_plural = "個別保有明細"

    def __str__(self) -> str:
        return f"{self.snapshot} - {self.asset_name}"


class WatchlistItem(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="watchlist_items",
    )
    stock = models.ForeignKey(
        "stocks.Stock",
        on_delete=models.CASCADE,
        related_name="watchlist_items",
    )
    memo = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "r_watchlist"
        unique_together = ("user", "stock")
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.user} - {self.stock}"
