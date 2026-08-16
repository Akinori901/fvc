from django.db import models


class Stock(models.Model):
    """銘柄マスタ"""

    INSTRUMENT_TYPE_CHOICES = [
        ("stock", "普通株式"),
        ("etf", "ETF・ETN"),
        ("reit", "J-REIT"),
        ("other", "その他"),
    ]

    code = models.CharField("証券コード", max_length=10, unique=True)
    name = models.CharField("銘柄名", max_length=255)
    market = models.CharField("市場区分", max_length=50, blank=True, default="")
    market_type = models.CharField(
        "市場タイプ",
        max_length=2,
        default="JP",
        choices=[("JP", "日本"), ("US", "米国")],
    )
    instrument_type = models.CharField("種別", max_length=10, choices=INSTRUMENT_TYPE_CHOICES, default="stock")
    sector = models.CharField("業種", max_length=100, blank=True, default="")
    is_active = models.BooleanField("有効フラグ", default=True)
    is_active_override = models.BooleanField(
        "上場状態手動オーバーライド",
        null=True,
        blank=True,
        help_text="True=強制アクティブ, False=強制非アクティブ, Null=自動判定(sync準拠)",
    )
    consecutive_missing_syncs = models.PositiveSmallIntegerField(
        "連続欠損同期回数", default=0, help_text="J-Quantsレスポンスに連続で含まれなかった回数"
    )
    latest_price = models.DecimalField("最新株価", max_digits=12, decimal_places=2, null=True, blank=True)
    latest_price_date = models.DateField("最新株価日", null=True, blank=True)
    created_at = models.DateTimeField("作成日時", auto_now_add=True)
    updated_at = models.DateTimeField("更新日時", auto_now=True)

    class Meta:
        db_table = "m_stocks"
        ordering = ["code"]
        verbose_name = "銘柄"
        verbose_name_plural = "銘柄"

    def __str__(self) -> str:
        return f"{self.code} {self.name}"


class StockFinancial(models.Model):
    """財務データ"""

    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name="financials", verbose_name="銘柄")
    fiscal_year = models.IntegerField("会計年度")
    period_end_date = models.DateField(
        "決算期末日", null=True, blank=True, help_text="J-Quants CurPerEn: 株式分割調整係数の基準日"
    )
    bps = models.DecimalField("1株あたり純資産(BPS)", max_digits=12, decimal_places=2)
    eps = models.DecimalField("1株あたり利益(EPS)", max_digits=12, decimal_places=2, null=True, blank=True)
    roe = models.DecimalField("ROE", max_digits=8, decimal_places=4, null=True, blank=True)
    net_assets = models.BigIntegerField("純資産(百万円)", null=True, blank=True)
    total_shares = models.BigIntegerField("発行済株式数", null=True, blank=True)
    revenue = models.BigIntegerField("売上高(百万円)", null=True, blank=True)
    operating_income = models.BigIntegerField("営業利益(百万円)", null=True, blank=True)
    eps_forecast = models.DecimalField("予想EPS", max_digits=12, decimal_places=2, null=True, blank=True)
    operating_cash_flow = models.BigIntegerField("営業CF(百万円)", null=True, blank=True)
    free_cash_flow = models.BigIntegerField("FCF(百万円)", null=True, blank=True)
    created_at = models.DateTimeField("作成日時", auto_now_add=True)

    class Meta:
        db_table = "t_stock_financials"
        ordering = ["-fiscal_year"]
        unique_together = [["stock", "fiscal_year"]]
        indexes = [
            models.Index(fields=["stock", "-fiscal_year"], name="idx_financial_stock_fy"),
        ]
        verbose_name = "財務データ"
        verbose_name_plural = "財務データ"

    def __str__(self) -> str:
        return f"{self.stock.code} FY{self.fiscal_year}"


class StockPrice(models.Model):
    """株価履歴"""

    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name="prices", verbose_name="銘柄")
    date = models.DateField("日付")
    close_price = models.DecimalField("終値", max_digits=12, decimal_places=2)
    is_limit_up = models.BooleanField("ストップ高", default=False, help_text="J-Quants UL フラグ")
    is_limit_down = models.BooleanField("ストップ安", default=False, help_text="J-Quants LL フラグ")
    adj_factor = models.DecimalField(
        "調整係数",
        max_digits=20,
        decimal_places=10,
        default=1,
        help_text="株式分割等の権利調整係数（AdjFactor）。現在日は1.0、分割前は<1.0",
    )
    pbr = models.DecimalField("PBR", max_digits=8, decimal_places=4, null=True, blank=True)
    volume = models.BigIntegerField("出来高", null=True, blank=True)
    created_at = models.DateTimeField("作成日時", auto_now_add=True)

    class Meta:
        db_table = "t_stock_prices"
        ordering = ["-date"]
        unique_together = [["stock", "date"]]
        indexes = [
            models.Index(fields=["date", "stock"], name="idx_price_date_stock"),
        ]
        verbose_name = "株価"
        verbose_name_plural = "株価"

    def __str__(self) -> str:
        return f"{self.stock.code} {self.date} ¥{self.close_price}"


class ApiConfig(models.Model):
    """外部API設定マスタ"""

    provider = models.CharField("プロバイダー", max_length=50, unique=True)
    is_enabled = models.BooleanField("有効フラグ", default=False)
    api_key = models.CharField("APIキー", max_length=500, blank=True, default="")
    plan = models.CharField("契約プラン", max_length=50, blank=True, default="")
    config_json = models.JSONField("追加設定", default=dict, blank=True)
    created_at = models.DateTimeField("作成日時", auto_now_add=True)
    updated_at = models.DateTimeField("更新日時", auto_now=True)

    class Meta:
        db_table = "m_api_configs"
        verbose_name = "API設定"
        verbose_name_plural = "API設定"

    def __str__(self) -> str:
        return f"{self.provider} ({'有効' if self.is_enabled else '無効'})"


class SyncLog(models.Model):
    """同期ログ"""

    class SyncType(models.TextChoices):
        STOCKS = "stocks", "銘柄マスタ"
        FINANCIALS = "financials", "財務データ"
        PRICES = "prices", "株価"
        DIVIDENDS = "dividends", "配当・分配金"

    class SyncStatus(models.TextChoices):
        RUNNING = "running", "実行中"
        SUCCESS = "success", "成功"
        PARTIAL = "partial", "一部失敗"
        FAILED = "failed", "失敗"

    sync_type = models.CharField("同期種別", max_length=20, choices=SyncType.choices)
    provider = models.CharField("データソース", max_length=50)
    market = models.CharField("市場", max_length=10, blank=True, default="")
    status = models.CharField("ステータス", max_length=20, choices=SyncStatus.choices)
    started_at = models.DateTimeField("開始日時")
    finished_at = models.DateTimeField("終了日時", null=True, blank=True)
    total_count = models.IntegerField("対象件数", default=0)
    success_count = models.IntegerField("成功件数", default=0)
    error_count = models.IntegerField("エラー件数", default=0)
    error_details = models.JSONField("エラー詳細", default=list, blank=True)
    created_at = models.DateTimeField("作成日時", auto_now_add=True)

    class Meta:
        db_table = "t_sync_logs"
        ordering = ["-started_at"]
        indexes = [
            # ダッシュボード等で「直近の同期ログ」を ORDER BY -started_at LIMIT N
            # で取得する。インデックスが無いと filesort になり、error_details
            # (JSON) カラム込みで全行をソートして MySQL の sort_buffer_size を
            # 超え 1038 'Out of sort memory' エラーになる (実際本番で発生済み)。
            models.Index(fields=["-started_at"], name="t_sync_logs_started_idx"),
        ]
        verbose_name = "同期ログ"
        verbose_name_plural = "同期ログ"

    def __str__(self) -> str:
        return f"{self.sync_type} {self.market} {self.status} ({self.started_at})"


class Dividend(models.Model):
    """配当・分配金履歴"""

    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name="dividends", verbose_name="銘柄")
    ex_dividend_date = models.DateField("権利落ち日")
    dividends_per_share = models.DecimalField("1口あたり配当/分配金", max_digits=12, decimal_places=4)
    record_date = models.DateField("権利確定日", null=True, blank=True)
    payable_date = models.DateField("支払開始日", null=True, blank=True)
    source = models.CharField("取得元", max_length=20, default="yfinance")
    created_at = models.DateTimeField("作成日時", auto_now_add=True)

    class Meta:
        db_table = "t_dividends"
        unique_together = [["stock", "ex_dividend_date"]]
        ordering = ["-ex_dividend_date"]
        verbose_name = "配当・分配金"
        verbose_name_plural = "配当・分配金"

    def __str__(self) -> str:
        return f"{self.stock.code} {self.ex_dividend_date} ¥{self.dividends_per_share}"


class MarginBalance(models.Model):
    """信用取引残高（日々公表）"""

    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name="margin_balances", verbose_name="銘柄")
    date = models.DateField("公表日")

    long_balance = models.BigIntegerField("信用買残(株数)", null=True, blank=True)
    long_balance_change = models.BigIntegerField("信用買残変化(株数)", null=True, blank=True)
    short_balance = models.BigIntegerField("信用売残(株数)", null=True, blank=True)
    short_balance_change = models.BigIntegerField("信用売残変化(株数)", null=True, blank=True)
    sl_ratio = models.DecimalField(
        "信売比率", max_digits=8, decimal_places=4, null=True, blank=True, help_text="信用売残÷信用買残"
    )
    created_at = models.DateTimeField("作成日時", auto_now_add=True)

    class Meta:
        db_table = "t_margin_balances"
        unique_together = [["stock", "date"]]
        ordering = ["-date"]
        verbose_name = "信用残高"
        verbose_name_plural = "信用残高"

    def __str__(self) -> str:
        return f"{self.stock.code} {self.date} 買残={self.long_balance}"


class DailyMovers(models.Model):
    """日次の急騰急落集計（compute_movers バッチで日次に書き換え）"""

    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name="daily_movers", verbose_name="銘柄")
    date = models.DateField("集計日")
    close_price = models.DecimalField("終値", max_digits=12, decimal_places=2)
    prev_close = models.DecimalField("前営業日終値", max_digits=12, decimal_places=2, null=True, blank=True)
    change_pct = models.DecimalField(
        "前日比(%)", max_digits=8, decimal_places=4, null=True, blank=True, help_text="例: 21.2800"
    )
    volume = models.BigIntegerField("出来高", null=True, blank=True)
    volume_ratio_20d = models.DecimalField(
        "出来高 20 日平均比", max_digits=8, decimal_places=2, null=True, blank=True, help_text="例: 3.80"
    )
    is_limit_up = models.BooleanField("ストップ高", default=False)
    is_limit_down = models.BooleanField("ストップ安", default=False)
    created_at = models.DateTimeField("作成日時", auto_now_add=True)

    class Meta:
        db_table = "t_daily_movers"
        unique_together = [["stock", "date"]]
        ordering = ["-date", "-change_pct"]
        indexes = [
            models.Index(fields=["date", "change_pct"], name="idx_movers_date_change"),
            models.Index(fields=["date", "volume_ratio_20d"], name="idx_movers_date_volratio"),
        ]
        verbose_name = "日次急騰急落"
        verbose_name_plural = "日次急騰急落"

    def __str__(self) -> str:
        return f"{self.stock.code} {self.date} change_pct={self.change_pct}"


class OwnerShareholder(models.Model):
    """代表者-大株主紐付け結果"""

    MATCH_TYPE_CHOICES = [
        ("exact", "代表者本人"),
        ("family", "親族（同姓）"),
        ("company", "資産管理会社候補"),
    ]

    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name="owner_shareholders", verbose_name="銘柄")
    representative_name = models.CharField("代表者氏名", max_length=100)
    shareholder_name = models.CharField("大株主名", max_length=200)
    shareholder_rank = models.IntegerField("大株主順位")
    ownership_ratio = models.DecimalField("持ち株比率(%)", max_digits=6, decimal_places=2)
    match_type = models.CharField("判定タイプ", max_length=20, choices=MATCH_TYPE_CHOICES)
    fiscal_year = models.IntegerField("事業年度")
    doc_id = models.CharField("EDINET書類ID", max_length=20)
    created_at = models.DateTimeField("作成日時", auto_now_add=True)
    updated_at = models.DateTimeField("更新日時", auto_now=True)

    class Meta:
        db_table = "t_owner_shareholders"
        unique_together = [["stock", "fiscal_year", "shareholder_rank"]]
        ordering = ["-fiscal_year", "shareholder_rank"]
        verbose_name = "オーナー大株主"
        verbose_name_plural = "オーナー大株主"

    def __str__(self) -> str:
        return f"{self.stock.code} FY{self.fiscal_year} #{self.shareholder_rank} {self.shareholder_name}"


class ShareholderRaw(models.Model):
    """大株主生データ"""

    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name="shareholders_raw", verbose_name="銘柄")
    shareholder_name = models.CharField("大株主名", max_length=200)
    shareholder_rank = models.IntegerField("順位")
    ownership_ratio = models.DecimalField("持ち株比率(%)", max_digits=6, decimal_places=2)
    shares_held = models.BigIntegerField("保有株数", null=True, blank=True)
    fiscal_year = models.IntegerField("事業年度")
    doc_id = models.CharField("EDINET書類ID", max_length=20)
    created_at = models.DateTimeField("作成日時", auto_now_add=True)

    class Meta:
        db_table = "t_shareholder_raw"
        unique_together = [["stock", "fiscal_year", "shareholder_rank"]]
        ordering = ["-fiscal_year", "shareholder_rank"]
        verbose_name = "大株主生データ"
        verbose_name_plural = "大株主生データ"

    def __str__(self) -> str:
        return f"{self.stock.code} FY{self.fiscal_year} #{self.shareholder_rank} {self.shareholder_name}"


class ScreeningPreset(models.Model):
    """ユーザー保存のスクリーニングフィルタープリセット"""

    user = models.ForeignKey(
        "auth.User",
        on_delete=models.CASCADE,
        related_name="screening_presets",
        verbose_name="ユーザー",
    )
    name = models.CharField("プリセット名", max_length=100)
    priority = models.IntegerField("優先度", default=0, help_text="小さいほど優先")
    filters = models.JSONField("フィルター設定", default=dict)
    created_at = models.DateTimeField("作成日時", auto_now_add=True)
    updated_at = models.DateTimeField("更新日時", auto_now=True)

    class Meta:
        db_table = "m_user_screening_presets"
        ordering = ["priority", "created_at"]
        unique_together = [["user", "name"]]
        verbose_name = "スクリーニングプリセット"
        verbose_name_plural = "スクリーニングプリセット"

    def __str__(self) -> str:
        return f"{self.user.username} / {self.name} (priority={self.priority})"


class FinancialManualInput(models.Model):
    """手動入力財務データ（J-Quantsにないデータの一時補完用）

    J-Quants 同期で同年度データが取得できた場合は t_stock_financials が優先される。
    このテーブルのレコードは自動削除されず、補完用フォールバックとして残る。
    """

    SOURCE_CHOICES = [
        ("shikiho", "四季報"),
        ("minkabu", "ミンカブ"),
        ("irpage", "IR/会社HP"),
        ("other", "その他"),
    ]

    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name="manual_financials", verbose_name="銘柄")
    fiscal_year = models.IntegerField("会計年度")
    bps = models.DecimalField("BPS", max_digits=12, decimal_places=2, null=True, blank=True)
    eps = models.DecimalField("EPS", max_digits=12, decimal_places=2, null=True, blank=True)
    roe = models.DecimalField("ROE", max_digits=8, decimal_places=4, null=True, blank=True)
    eps_forecast = models.DecimalField("予想EPS", max_digits=12, decimal_places=2, null=True, blank=True)
    revenue = models.BigIntegerField("売上高(百万円)", null=True, blank=True)
    operating_income = models.BigIntegerField("営業利益(百万円)", null=True, blank=True)
    source = models.CharField("情報ソース", max_length=20, choices=SOURCE_CHOICES, default="other")
    note = models.TextField("メモ", blank=True, default="")
    created_at = models.DateTimeField("作成日時", auto_now_add=True)
    updated_at = models.DateTimeField("更新日時", auto_now=True)

    class Meta:
        db_table = "t_financial_manual_inputs"
        unique_together = [["stock", "fiscal_year"]]
        ordering = ["-fiscal_year"]
        verbose_name = "手動入力財務データ"
        verbose_name_plural = "手動入力財務データ"

    def __str__(self) -> str:
        return f"{self.stock.code} FY{self.fiscal_year} [{self.get_source_display()}]"


class RecommendationSnapshot(models.Model):
    """おすすめ銘柄スナップショット（ダッシュボード用）。

    Worker Lambda が定期的に RecommendationUseCase を実行し、その結果を
    DBに保存する。API は本テーブルを SELECT するだけで即座に応答する。
    """

    class Category(models.TextChoices):
        LONG_TERM = "long_term", "長期保有"
        DAY_TRADE = "day_trade", "デイトレ"
        RANGE_BOUND = "range_bound", "1〜2年レンジ"

    category = models.CharField("カテゴリ", max_length=20, choices=Category.choices)
    rank = models.PositiveSmallIntegerField("順位")
    stock = models.ForeignKey(
        Stock,
        on_delete=models.CASCADE,
        related_name="recommendation_snapshots",
        verbose_name="銘柄",
    )
    latest_price = models.DecimalField("最新株価", max_digits=12, decimal_places=2, null=True, blank=True)
    metrics = models.JSONField("指標", default=dict)
    score = models.DecimalField("スコア", max_digits=14, decimal_places=4)
    generated_at = models.DateTimeField("生成日時", auto_now_add=True)

    class Meta:
        db_table = "t_recommendation_snapshots"
        unique_together = [["category", "rank"]]
        ordering = ["category", "rank"]
        indexes = [models.Index(fields=["category", "rank"])]
        verbose_name = "おすすめ銘柄スナップショット"
        verbose_name_plural = "おすすめ銘柄スナップショット"

    def __str__(self) -> str:
        return f"[{self.get_category_display()}] {self.rank}位 {self.stock.code}"


class ScreeningSnapshot(models.Model):
    """スクリーニング（銘柄一覧）の事前計算スナップショット。

    バッチ(generate_screening_snapshot)が全銘柄の growth_rate 非依存な計算結果
    （テクニカル・配当・FCF・信用・オーナー・生財務・買い時シグナル）を保存する。
    一覧APIは本テーブルを SELECT し、リクエスト時の growth_rate から適正株価・
    評価ゾーン・総合評価スコアだけを軽量に再計算してページングする。
    最新1世代のみ（バッチで全削除→再生成）。

    - WHERE/検索に使う主要フィールドは個別カラム（インデックス対象）。
    - 表示・リクエスト時の軽計算に使う残りの指標は metrics(JSONField) にまとめる。
    """

    stock = models.OneToOneField(
        Stock,
        on_delete=models.CASCADE,
        related_name="screening_snapshot",
        verbose_name="銘柄",
    )
    code = models.CharField("証券コード", max_length=16)
    name = models.CharField("銘柄名", max_length=255)
    sector = models.CharField("業種", max_length=100, blank=True)
    market_type = models.CharField("市場区分", max_length=8, default="JP")
    is_active = models.BooleanField("上場中", default=True)

    # --- WHERE / ORDER BY に使う growth_rate 非依存の指標（個別カラム） ---
    roe = models.DecimalField("ROE", max_digits=12, decimal_places=6, null=True, blank=True)
    sl_ratio = models.DecimalField("信売比率", max_digits=12, decimal_places=4, null=True, blank=True)
    roe_trend = models.CharField("ROEトレンド", max_length=16, null=True, blank=True)
    dividend_yield = models.DecimalField("配当利回り", max_digits=8, decimal_places=4, null=True, blank=True)
    fcf_yield = models.DecimalField("FCF利回り", max_digits=8, decimal_places=4, null=True, blank=True)
    momentum_signal = models.CharField("モメンタム", max_length=16, null=True, blank=True)
    liquidity_level = models.CharField("流動性", max_length=16, null=True, blank=True)
    is_owner_managed = models.BooleanField("オーナー経営", default=False)

    # --- 買い時テクニカルシグナル（絞り込み用 bool） ---
    ma_golden_cross = models.BooleanField(default=False)
    price_cross_ma25 = models.BooleanField(default=False)
    price_cross_ma75 = models.BooleanField(default=False)
    macd_golden_cross = models.BooleanField(default=False)
    rsi_rebound = models.BooleanField(default=False)
    pullback_buy = models.BooleanField(default=False)

    # --- 表示 / リクエスト時の軽計算に使う残りの指標一式 ---
    # latest_price, bps, eps, current_pbr, implied_growth_rate,
    # eps_growth_yoy, eps_cagr_3y, revenue_growth_yoy, op_income_growth_yoy,
    # company_forecast_growth_rate, long_balance, short_balance,
    # long_balance_change_pct, long_balance_trend, price_position_52w,
    # distance_from_52w_high, volume_ratio_20d, ma_25_deviation,
    # avg_turnover_20d, payout_ratio, consecutive_dividend_years,
    # progressive_dividend_years, dividend_score, fcf, prev_fcf, fcf_margin,
    # fcf_score, owner_ratio, owner_match_type, not_calculable_reason,
    # is_manual_financial（すべて growth_rate 非依存）
    metrics = models.JSONField("その他指標", default=dict)

    generated_at = models.DateTimeField("生成日時", auto_now_add=True)

    class Meta:
        db_table = "t_screening_snapshots"
        indexes = [
            models.Index(fields=["market_type", "is_active"]),
            models.Index(fields=["market_type", "is_active", "roe"]),
            models.Index(fields=["market_type", "is_active", "dividend_yield"]),
            models.Index(fields=["code"]),
        ]
        verbose_name = "スクリーニングスナップショット"
        verbose_name_plural = "スクリーニングスナップショット"

    def __str__(self) -> str:
        return f"{self.code} {self.name}"
