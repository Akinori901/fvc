"""証券会社CSVファイルのパース・インポートサービス。

対応プロバイダ:
- rakuten: 楽天証券「資産残高・保有商品」CSV
- rakuten_margin: 楽天証券「信用取引 建玉一覧」CSV
- rakuten_ideco: 楽天証券 iDeCo CSV
- rakuten_fund: 楽天証券「保有商品（投資信託）」CSV
- sbi_portfolio: SBI証券「My資産 → ポートフォリオ」CSV (投信MVP)
- sbi_margin: SBI証券「信用建玉一覧」CSV (marginbalance(JP)_*.csv)
"""

from __future__ import annotations

import csv
import io
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.core.files.uploadedfile import UploadedFile


# ============================================================
# データクラス
# ============================================================


@dataclass
class ParsedHolding:
    """CSV から抽出した個別保有銘柄。"""

    ticker_code: str
    asset_name: str
    asset_type: str  # stock / etf / fund / bond / cash / other
    quantity: Decimal
    unit_price: Decimal | None
    currency: str  # JPY / USD
    value_jpy: Decimal
    cost_jpy: Decimal | None


@dataclass
class AccountGroup:
    """CSVの口座グループ（種別×口座の組み合わせ）。"""

    asset_type_raw: str  # 元CSV種別（"米国株式", "投資信託" 等）
    account_type_raw: str  # 元CSV口座（"旧NISA", "特定" 等）
    asset_class: str  # マッピング後の asset_class
    total_value_jpy: Decimal = Decimal(0)
    total_cost_jpy: Decimal = Decimal(0)
    currency: str = "JPY"
    holdings: list[ParsedHolding] = field(default_factory=list)


@dataclass
class CsvParseResult:
    """CSVパース結果。"""

    provider: str
    snapshot_date: str
    exchange_rates: dict[str, Decimal]
    account_groups: list[AccountGroup]


# ============================================================
# 共通ユーティリティ
# ============================================================


def _parse_number(s: str) -> Decimal | None:
    """カンマ・符号付き数値文字列を Decimal に変換。"""
    s = s.strip().replace(",", "")
    if not s or s == "-":
        return None
    try:
        return Decimal(s.lstrip("+"))
    except InvalidOperation:
        return None


# ============================================================
# パーサー基底クラス
# ============================================================


class CsvParser(ABC):
    """プロバイダ固有の CSV パーサー基底クラス。"""

    @abstractmethod
    def parse(self, file: UploadedFile, snapshot_date: str) -> CsvParseResult:
        """CSVファイルをパースし、構造化データを返す。"""


# ============================================================
# 楽天証券パーサー
# ============================================================

# 前方一致で検索するため (prefix, mapped_value) のタプルリスト（長い順）
_RAKUTEN_ASSET_CLASS_PREFIXES: list[tuple[str, str]] = [
    ("外貨預り金", "cash"),
    ("外貨建てMMF", "other"),
    ("外国債券", "us_bond"),
    ("金・プラチナ", "other"),
    ("アセアン株式", "other"),
    ("国内株式", "jp_stock"),  # "国内株式（信用）" も含む
    ("米国株式", "us_stock"),
    ("中国株式", "other"),
    ("投資信託", "fund"),
    ("債券", "jp_bond"),
]

_RAKUTEN_ASSET_TYPE_PREFIXES: list[tuple[str, str]] = [
    ("外貨預り金", "cash"),
    ("外貨建てMMF", "fund"),
    ("外国債券", "bond"),
    ("金・プラチナ", "other"),
    ("アセアン株式", "stock"),
    ("国内株式", "stock"),
    ("米国株式", "stock"),
    ("中国株式", "stock"),
    ("投資信託", "fund"),
    ("債券", "bond"),
]


def _lookup_prefix(prefixes: list[tuple[str, str]], key: str, default: str = "other") -> str:
    """前方一致でマッピング値を検索。"""
    for prefix, value in prefixes:
        if key.startswith(prefix):
            return value
    return default


class RakutenCsvParser(CsvParser):
    """楽天証券「資産残高・保有商品（すべて）」CSVパーサー。"""

    def parse(self, file: UploadedFile, snapshot_date: str) -> CsvParseResult:
        raw = file.read()
        # Shift-JIS → UTF-8
        try:
            text = raw.decode("shift_jis")
        except UnicodeDecodeError:
            text = raw.decode("cp932")

        lines = list(csv.reader(io.StringIO(text)))
        holdings_rows = self._extract_holdings_section(lines)
        exchange_rates = self._extract_exchange_rates(lines)

        # グルーピング: (asset_type_raw, account_type_raw) → AccountGroup
        groups: dict[tuple[str, str], AccountGroup] = {}

        for row in holdings_rows:
            parsed = self._parse_holding_row(row, exchange_rates)
            if parsed is None:
                continue
            asset_type_raw, account_type_raw, holding = parsed
            key = (asset_type_raw, account_type_raw)
            if key not in groups:
                groups[key] = AccountGroup(
                    asset_type_raw=asset_type_raw,
                    account_type_raw=account_type_raw,
                    asset_class=_lookup_prefix(_RAKUTEN_ASSET_CLASS_PREFIXES, asset_type_raw),
                    currency=holding.currency,
                )
            g = groups[key]
            g.holdings.append(holding)
            g.total_value_jpy += holding.value_jpy
            if holding.cost_jpy is not None:
                g.total_cost_jpy += holding.cost_jpy

        return CsvParseResult(
            provider="rakuten",
            snapshot_date=snapshot_date,
            exchange_rates=exchange_rates,
            account_groups=list(groups.values()),
        )

    def _extract_holdings_section(self, lines: list[list[str]]) -> list[list[str]]:
        """保有商品詳細セクションのデータ行を抽出。"""
        start = None
        for i, row in enumerate(lines):
            if row and "保有商品" in row[0] and "詳細" in row[0]:
                start = i
                break
        if start is None:
            return []

        # ヘッダー行をスキップ（空行→ヘッダー→データ）
        data_start = start + 1
        while data_start < len(lines) and (not lines[data_start] or not lines[data_start][0].strip()):
            data_start += 1
        # ヘッダー行をスキップ
        data_start += 1

        rows = []
        for i in range(data_start, len(lines)):
            row = lines[i]
            if not row or not row[0].strip():
                # 空行で終了（次のセクション境界）
                # ただし連続空行は1行だけ許容
                if i + 1 < len(lines) and (not lines[i + 1] or not lines[i + 1][0].strip()):
                    break
                continue
            # 次のセクションヘッダー（■で始まる）なら終了
            if row[0].startswith("■"):
                break
            rows.append(row)
        return rows

    def _parse_holding_row(
        self,
        row: list[str],
        exchange_rates: dict[str, Decimal],
    ) -> tuple[str, str, ParsedHolding] | None:
        """1行のデータを ParsedHolding に変換。"""
        if len(row) < 15:
            return None

        asset_type_raw = row[0].strip()
        ticker = row[1].strip()
        name = row[2].strip()
        account_type_raw = row[3].strip()

        if not asset_type_raw:
            return None

        # 口座が "-" の場合（外貨預り金など）
        if account_type_raw == "-":
            account_type_raw = "その他"

        quantity = _parse_number(row[4])
        if quantity is None:
            return None

        unit_price = _parse_number(row[6])
        price_currency = row[7].strip() if len(row) > 7 else "円"
        currency = "USD" if "USD" in price_currency else "JPY"

        value_jpy = _parse_number(row[14])
        if value_jpy is None:
            return None

        # 評価損益[円] (column 16)
        unrealized_gain = _parse_number(row[16]) if len(row) > 16 else None
        cost_jpy: Decimal | None = None
        if unrealized_gain is not None:
            cost_jpy = value_jpy - unrealized_gain

        holding_asset_type = _lookup_prefix(_RAKUTEN_ASSET_TYPE_PREFIXES, asset_type_raw)

        return (
            asset_type_raw,
            account_type_raw,
            ParsedHolding(
                ticker_code=ticker,
                asset_name=name,
                asset_type=holding_asset_type,
                quantity=quantity,
                unit_price=unit_price,
                currency=currency,
                value_jpy=value_jpy,
                cost_jpy=cost_jpy,
            ),
        )

    def _extract_exchange_rates(self, lines: list[list[str]]) -> dict[str, Decimal]:
        """参考為替レートセクションを抽出。"""
        rates: dict[str, Decimal] = {}
        start = None
        for i, row in enumerate(lines):
            if row and "参考為替レート" in row[0]:
                start = i + 1
                break
        if start is None:
            return rates

        currency_map = {
            "米ドル": "USD",
            "ユーロ": "EUR",
            "英ポンド": "GBP",
            "豪ドル": "AUD",
            "カナダドル": "CAD",
        }

        for i in range(start, len(lines)):
            row = lines[i]
            if not row or not row[0].strip():
                continue
            name = row[0].strip()
            rate = _parse_number(row[1]) if len(row) > 1 else None
            if rate is not None:
                code = currency_map.get(name, name)
                rates[code] = rate
        return rates


# ============================================================
# 楽天証券 信用取引パーサー
# ============================================================


class RakutenMarginCsvParser(CsvParser):
    """楽天証券「信用取引 建玉一覧」CSVパーサー。

    CSVカラム（Shift-JIS / CP932）:
    0: 口座区分, 1: 銘柄コード, 2: 銘柄名, 3: 市場名称, 4: 売買,
    5: 信用区分, 6: 弁済期限, 7: 建玉数量[株], 8: 執行中[株], 9: 建単価[円],
    10: 現在値[円], 11: 現在値(前日比)[円], 12: 保証金率[％],
    13: 保証金率(うち現金)[％], 14: 建日, 15: 最終返済日,
    16: 時価評価額[円], 17: 評価損益額[円], 18: 評価損益率[％], ...
    """

    def parse(self, file: UploadedFile, snapshot_date: str) -> CsvParseResult:
        raw = file.read()
        try:
            text = raw.decode("shift_jis")
        except UnicodeDecodeError:
            text = raw.decode("cp932")

        lines = list(csv.reader(io.StringIO(text)))

        # データ行を探す（ヘッダー行の次から）
        data_start = None
        for i, row in enumerate(lines):
            if len(row) > 1 and "銘柄コード" in row[1]:
                data_start = i + 1
                break

        if data_start is None:
            # ヘッダーが見つからない場合、データ行を直接探す
            for i, row in enumerate(lines):
                if len(row) > 5 and row[4].strip() in ("買建", "売建"):
                    data_start = i
                    break

        if data_start is None:
            return CsvParseResult(
                provider="rakuten_margin",
                snapshot_date=snapshot_date,
                exchange_rates={},
                account_groups=[],
            )

        # グルーピング: 口座別
        groups: dict[str, AccountGroup] = {}

        for i in range(data_start, len(lines)):
            row = lines[i]
            if len(row) < 18:
                continue

            account_type = row[0].strip() or "特定"  # 口座区分
            ticker = row[1].strip()
            name = row[2].strip()
            trade_type = row[4].strip()  # 売買（買建 / 売建）

            if trade_type not in ("買建", "売建"):
                continue

            quantity = _parse_number(row[7])
            cost_price = _parse_number(row[9])
            value_jpy = _parse_number(row[16])
            unrealized_gain = _parse_number(row[17])

            if quantity is None or value_jpy is None:
                continue

            cost_jpy: Decimal | None = None
            if unrealized_gain is not None:
                cost_jpy = value_jpy - unrealized_gain

            # 売建は負のポジション
            if trade_type == "売建":
                value_jpy = -value_jpy
                if cost_jpy is not None:
                    cost_jpy = -cost_jpy

            holding = ParsedHolding(
                ticker_code=ticker,
                asset_name=f"{name}（{trade_type}）",
                asset_type="stock",
                quantity=quantity,
                unit_price=cost_price,
                currency="JPY",
                value_jpy=value_jpy,
                cost_jpy=cost_jpy,
            )

            # nickname に「信用」サフィックスを付与し、同じ口座区分の現物口座と衝突しないようにする
            # 例: "特定" → "特定信用", "一般" → "一般信用"
            nickname = f"{account_type}信用"
            key = nickname
            if key not in groups:
                groups[key] = AccountGroup(
                    asset_type_raw="国内株式（信用）",
                    account_type_raw=nickname,
                    asset_class="jp_stock",
                )
            g = groups[key]
            g.holdings.append(holding)
            g.total_value_jpy += holding.value_jpy
            if holding.cost_jpy is not None:
                g.total_cost_jpy += holding.cost_jpy

        return CsvParseResult(
            provider="rakuten_margin",
            snapshot_date=snapshot_date,
            exchange_rates={},
            account_groups=list(groups.values()),
        )


# ============================================================
# 楽天証券 iDeCo パーサー
# ============================================================

_IDECO_ASSET_CLASS_MAP: dict[str, str] = {
    "外国株式": "us_stock",
    "国内外株式": "fund",
    "国内株式": "jp_stock",
    "海外REIT": "other",
    "コモディティ": "other",
    "外国債券": "us_bond",
    "国内債券": "jp_bond",
    "バランス": "fund",
}


def _parse_jpy_value(s: str) -> Decimal | None:
    """「1,234,567 円」「+1,234 円」形式を Decimal に変換。"""
    s = s.strip().replace(",", "").replace("円", "").replace(" ", "")
    if not s or s == "-":
        return None
    try:
        return Decimal(s.lstrip("+"))
    except InvalidOperation:
        return None


def _parse_quantity_with_unit(s: str) -> Decimal | None:
    """「255,078 口」「625 口」形式を Decimal に変換。"""
    s = s.strip().replace(",", "").replace("口", "").replace(" ", "")
    if not s or s == "-":
        return None
    try:
        return Decimal(s)
    except InvalidOperation:
        return None


class RakutenIdecoCsvParser(CsvParser):
    """楽天証券 iDeCo 資産CSVパーサー。

    CSVカラム（UTF-8）:
    0: 資産タイプ, 1: 商品名, 2: 構成比, 3: 保有数量, 4: 取得金額,
    5: 基準価額, 6: 評価額, 7: 評価損益
    """

    def parse(self, file: UploadedFile, snapshot_date: str) -> CsvParseResult:
        raw = file.read()
        # UTF-8 or Shift-JIS
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = raw.decode("shift_jis")
            except UnicodeDecodeError:
                text = raw.decode("cp932")

        lines = list(csv.reader(io.StringIO(text)))
        group = AccountGroup(
            asset_type_raw="iDeCo",
            account_type_raw="iDeCo",
            asset_class="fund",
        )

        for row in lines:
            if len(row) < 7:
                continue

            asset_type_cell = row[0].strip()
            # データ行は "● " で始まる
            if not asset_type_cell.startswith("●"):
                continue

            name = row[1].strip()
            quantity = _parse_quantity_with_unit(row[3])
            cost_jpy = _parse_jpy_value(row[4])
            unit_price = _parse_jpy_value(row[5])
            value_jpy = _parse_jpy_value(row[6])

            if value_jpy is None or quantity is None:
                continue

            holding = ParsedHolding(
                ticker_code="",
                asset_name=name,
                asset_type="fund",
                quantity=quantity,
                unit_price=unit_price,
                currency="JPY",
                value_jpy=value_jpy,
                cost_jpy=cost_jpy,
            )
            group.holdings.append(holding)
            group.total_value_jpy += value_jpy
            if cost_jpy is not None:
                group.total_cost_jpy += cost_jpy

        return CsvParseResult(
            provider="rakuten_ideco",
            snapshot_date=snapshot_date,
            exchange_rates={},
            account_groups=[group] if group.holdings else [],
        )


# ============================================================
# 楽天証券 投資信託パーサー
# ============================================================

# 投資信託種別 → asset_class マッピング
_FUND_ASSET_CLASS_MAP: dict[str, str] = {
    "投資信託": "fund",
    "外貨建てMMF": "fund",
}


class RakutenFundCsvParser(CsvParser):
    """楽天証券「保有商品（投資信託）」CSVパーサー。

    assetbalance(INVST) / ジュニアNISA等の投資信託専用CSV。
    1行目がヘッダー、2行目以降がデータ。

    CSVカラム（Shift-JIS / CP932）:
    0: 投資信託種別, 1: 口座区分, 2: ファンド, 3: 分配金コース,
    4: 保有数量[口], 5: (内訳 通常数量[口]), 6: (内訳 積立数量[口]),
    7: 平均取得価額[円], 8: 取得総額[円], 9: 基準価額[円],
    10: 基準価額(前日比)[円], 11: 基準価額(前月比)[円],
    12: 時価評価額[円], 13: 評価損益[円], 14: 評価損益[％], ...
    """

    def parse(self, file: UploadedFile, snapshot_date: str) -> CsvParseResult:
        raw = file.read()
        try:
            text = raw.decode("shift_jis")
        except UnicodeDecodeError:
            text = raw.decode("cp932")

        lines = list(csv.reader(io.StringIO(text)))

        # 1行目がヘッダーかどうか確認
        data_start = 0
        if lines and len(lines[0]) > 2 and "ファンド" in lines[0][2]:
            data_start = 1

        # グルーピング: (投資信託種別, 口座区分) → AccountGroup
        groups: dict[tuple[str, str], AccountGroup] = {}

        for i in range(data_start, len(lines)):
            row = lines[i]
            if len(row) < 14:
                continue

            fund_type = row[0].strip()  # 投資信託種別
            account_type = row[1].strip()  # 口座区分（NISA, 特定 等）
            name = row[2].strip()

            if not fund_type or not name:
                continue

            quantity = _parse_number(row[4])
            unit_price = _parse_number(row[9])  # 基準価額
            value_jpy = _parse_number(row[12])  # 時価評価額
            cost_jpy = _parse_number(row[8])  # 取得総額

            if quantity is None or value_jpy is None:
                continue

            holding = ParsedHolding(
                ticker_code="",
                asset_name=name,
                asset_type="fund",
                quantity=quantity,
                unit_price=unit_price,
                currency="JPY",
                value_jpy=value_jpy,
                cost_jpy=cost_jpy,
            )

            key = (fund_type, account_type)
            if key not in groups:
                groups[key] = AccountGroup(
                    asset_type_raw=fund_type,
                    account_type_raw=account_type,
                    asset_class=_FUND_ASSET_CLASS_MAP.get(fund_type, "fund"),
                )
            g = groups[key]
            g.holdings.append(holding)
            g.total_value_jpy += value_jpy
            if cost_jpy is not None:
                g.total_cost_jpy += cost_jpy

        return CsvParseResult(
            provider="rakuten_fund",
            snapshot_date=snapshot_date,
            exchange_rates={},
            account_groups=list(groups.values()),
        )


# ============================================================
# SBI証券 ポートフォリオパーサー
# ============================================================

# SBI セクション見出し (部分一致) → (asset_class, section_kind)
# section_kind は内部用ラベル ("fund" / "us_stock" / "jp_stock" / "cash" / "other")
_SBI_SECTION_PATTERNS: list[tuple[str, str, str]] = [
    # (見出しに含まれる部分文字列, asset_class, section_kind)
    ("投資信託", "fund", "fund"),
    # 将来追加: 米株/国内株/預り金などを観測したらここに追加 (現状は MVP として未対応)
]


class SbiPortfolioCsvParser(CsvParser):
    """SBI証券「My資産 → ポートフォリオ」CSV (一括表示) のパーサー。

    SBI CSV 構造 (Shift-JIS):
        ポートフォリオ一覧
        一括表示
        PTS株価非表示
        総件数：N件
        選択範囲：1-N件
        ページ：1
        投資信託（金額/特定預り）              ← セクション見出し
        ファンド名, 買付日, 数量, 取得単価, 現在値, 前日比, 前日比（％）, 損益, 損益（％）, 評価額
        iFreeレバレッジ FANG+, ----/--/--, 229221, 19623, 40272, -1, 0.00, 473318.44, 105.23, 923118.81
        投資信託(金額/特定預り)合計             ← 合計行
        評価額, 含み損益, 含み損益（％）, 前日比, 前日比（％）
        923118.81, 473318.44, 105.23, -22.92, 0
        (次セクションがあれば繰り返し)

    現状 MVP は **投信セクションのみ処理**。米株・預り金等の他セクションは
    将来追加する想定 (CSV サンプルが揃い次第)。
    """

    # 投信セクションのカラム位置 (ヘッダー検出後の明細行で使用)
    _FUND_COL_NAME = 0
    _FUND_COL_QUANTITY = 2
    _FUND_COL_UNIT_PRICE = 3
    _FUND_COL_VALUE = 9

    def parse(self, file: UploadedFile, snapshot_date: str) -> CsvParseResult:
        raw = file.read()
        try:
            text = raw.decode("shift_jis")
        except UnicodeDecodeError:
            text = raw.decode("cp932", errors="replace")

        lines = list(csv.reader(io.StringIO(text)))

        groups: dict[tuple[str, str], AccountGroup] = {}

        # 状態: None | "fund_header_pending" | "fund_data"
        section_state: str | None = None
        section_account_type = ""  # "特定預り" / "NISA" 等を見出しから抽出

        for row in lines:
            if not row or all((c or "").strip() == "" for c in row):
                continue
            cell0 = (row[0] or "").strip()

            # セクション見出しを検出: 「投資信託（金額/特定預り）」 等
            section_kind, account_type_from_section = _detect_sbi_section(cell0)
            if section_kind == "fund":
                section_state = "fund_header_pending"
                section_account_type = account_type_from_section
                continue

            # 合計行 (例: 「投資信託(金額/特定預り)合計」) → セクション終了
            if section_state in ("fund_header_pending", "fund_data") and "合計" in cell0:
                section_state = None
                continue

            # ヘッダー行検出 (「ファンド名」を含む)
            if section_state == "fund_header_pending" and "ファンド" in cell0:
                section_state = "fund_data"
                continue

            # 明細行 (投信セクション)
            if section_state == "fund_data" and len(row) > self._FUND_COL_VALUE:
                name = cell0
                if not name:
                    continue
                quantity = _parse_number(row[self._FUND_COL_QUANTITY])
                unit_price = _parse_number(row[self._FUND_COL_UNIT_PRICE])
                value_jpy = _parse_number(row[self._FUND_COL_VALUE])
                if quantity is None or value_jpy is None:
                    continue

                # cost_jpy は SBI CSV に直接含まれないため、(数量 × 取得単価) で算出
                # 数量は「口数」、取得単価は「1万口あたりの単価」のため /10000 で換算
                cost_jpy: Decimal | None = None
                if unit_price is not None:
                    cost_jpy = (quantity * unit_price) / Decimal(10000)

                holding = ParsedHolding(
                    ticker_code="",
                    asset_name=name,
                    asset_type="fund",
                    quantity=quantity,
                    unit_price=unit_price,
                    currency="JPY",
                    value_jpy=value_jpy,
                    cost_jpy=cost_jpy,
                )

                key = ("投資信託", section_account_type)
                if key not in groups:
                    groups[key] = AccountGroup(
                        asset_type_raw="投資信託",
                        account_type_raw=section_account_type,
                        asset_class="fund",
                    )
                g = groups[key]
                g.holdings.append(holding)
                g.total_value_jpy += value_jpy
                if cost_jpy is not None:
                    g.total_cost_jpy += cost_jpy

        return CsvParseResult(
            provider="sbi_portfolio",
            snapshot_date=snapshot_date,
            exchange_rates={},
            account_groups=list(groups.values()),
        )


def _detect_sbi_section(cell: str) -> tuple[str | None, str]:
    """セクション見出しを判定。

    例: 「投資信託（金額/特定預り）」 → ("fund", "特定預り")
        「投資信託（金額/NISA成長投資枠）」 → ("fund", "NISA成長投資枠")

    Returns:
        (section_kind, account_type) または (None, "")
    """
    if not cell:
        return None, ""
    # 合計行は除外
    if "合計" in cell:
        return None, ""
    for pattern, _asset_class, kind in _SBI_SECTION_PATTERNS:
        if pattern in cell and "(" in cell or pattern in cell and "（" in cell:
            # 括弧内から口座区分を抽出: 「投資信託（金額/特定預り）」 → "特定預り"
            account_type = ""
            for left, right in [("（", "）"), ("(", ")")]:
                if left in cell and right in cell:
                    inner = cell[cell.index(left) + 1 : cell.rindex(right)]
                    # 「金額/特定預り」 → "特定預り"
                    parts = inner.split("/")
                    account_type = parts[-1].strip() if parts else inner.strip()
                    break
            return kind, account_type
    return None, ""


# ============================================================
# SBI証券 信用建玉パーサー
# ============================================================


class SbiMarginCsvParser(CsvParser):
    """SBI証券「口座管理 → 信用建玉一覧」CSVパーサー (marginbalance(JP)_*.csv)。

    CSV 構造 (Shift-JIS):
        ■表示形式,個別銘柄
        (空行)
        保証金率（新規建）［％］,..., 評価損益[円],"-49,778"
        売建[円],"0", 買建[円],"3,735,100", 合計[円],"3,735,100"
        (空行)
        口座区分, 銘柄コード, 銘柄名, 市場名称, 売買, 信用区分, 弁済期限,
        建玉数量［株］, 執行中［株］, 建単価[円], 現在値［円］, 現在値（前日比）［円］,
        保証金率［％］, 保証金率（うち現金）［％］, 建日, 最終返済日,
        時価評価額［円］, 評価損益額［円］, 評価損益率［％］, 建手数料 ...
        "特定","5892","ＹＵＴＯＲＩ","東証","買建","制度","6ヶ月","500","0","2,500", ...

    売建は negative position として保存 (楽天 RakutenMarginCsvParser に準拠)。
    銘柄名は機種依存文字で化けやすいため CSV 値はフォールバック扱いとし、
    呼び出し側で銘柄コード経由で m_stocks から正式名を引き直す想定。
    """

    # データ行のカラム位置
    _COL_ACCOUNT_TYPE = 0
    _COL_TICKER = 1
    _COL_NAME = 2
    _COL_MARKET = 3
    _COL_TRADE_TYPE = 4  # "買建" / "売建"
    _COL_CREDIT_TYPE = 5  # "制度" / "一般"
    _COL_QUANTITY = 7
    _COL_UNIT_PRICE = 9  # 建単価
    _COL_BUILT_DATE = 14
    _COL_VALUE = 16  # 時価評価額
    _COL_GAIN = 17  # 評価損益額

    def parse(self, file: UploadedFile, snapshot_date: str) -> CsvParseResult:
        raw = file.read()
        try:
            text = raw.decode("shift_jis")
        except UnicodeDecodeError:
            text = raw.decode("cp932", errors="replace")

        lines = list(csv.reader(io.StringIO(text)))

        # ヘッダー行 (「口座区分」「銘柄コード」を含む) を検出
        data_start: int | None = None
        for i, row in enumerate(lines):
            if len(row) > self._COL_TICKER and row[self._COL_ACCOUNT_TYPE].strip() == "口座区分":
                data_start = i + 1
                break

        if data_start is None:
            return CsvParseResult(
                provider="sbi_margin",
                snapshot_date=snapshot_date,
                exchange_rates={},
                account_groups=[],
            )

        # 口座区分ごとにグルーピング (例: "特定" / "一般")
        groups: dict[str, AccountGroup] = {}

        for i in range(data_start, len(lines)):
            row = lines[i]
            if len(row) <= self._COL_GAIN:
                continue

            account_type = row[self._COL_ACCOUNT_TYPE].strip()
            ticker = row[self._COL_TICKER].strip()
            trade_type = row[self._COL_TRADE_TYPE].strip()

            if trade_type not in ("買建", "売建"):
                continue
            if not ticker:
                continue

            name = row[self._COL_NAME].strip()
            credit_type = row[self._COL_CREDIT_TYPE].strip()
            quantity = _parse_number(row[self._COL_QUANTITY])
            unit_price = _parse_number(row[self._COL_UNIT_PRICE])
            value_jpy = _parse_number(row[self._COL_VALUE])
            gain = _parse_number(row[self._COL_GAIN])

            if quantity is None or value_jpy is None:
                continue

            cost_jpy: Decimal | None = None
            if gain is not None:
                cost_jpy = value_jpy - gain

            # 売建は負のポジション (楽天 RakutenMarginCsvParser に準拠)
            if trade_type == "売建":
                value_jpy = -value_jpy
                if cost_jpy is not None:
                    cost_jpy = -cost_jpy

            # 同一銘柄の複数建玉を区別するため asset_name に建日・売買・信用区分を付与する
            # (ParsedHolding に built_date フィールドが無いため、明細上の識別は asset_name で行う)
            built_date_raw = row[self._COL_BUILT_DATE].strip() if len(row) > self._COL_BUILT_DATE else ""
            suffix_parts = [trade_type]
            if credit_type:
                suffix_parts.append(credit_type)
            if built_date_raw:
                suffix_parts.append(built_date_raw)
            suffix = "・".join(suffix_parts)
            display_name = f"{name}（{suffix}）" if name else f"{ticker}（{suffix}）"

            holding = ParsedHolding(
                ticker_code=ticker,
                asset_name=display_name,
                asset_type="stock",
                quantity=quantity,
                unit_price=unit_price,
                currency="JPY",
                value_jpy=value_jpy,
                cost_jpy=cost_jpy,
            )

            # nickname に「信用」サフィックスを付与し、同じ口座区分の現物口座と衝突しないようにする
            # 例: "特定" → "特定信用", "一般" → "一般信用"
            raw_account = account_type or "特定"
            nickname = f"{raw_account}信用"
            key = nickname
            if key not in groups:
                groups[key] = AccountGroup(
                    asset_type_raw="国内株式（信用）",
                    account_type_raw=nickname,
                    asset_class="jp_stock",
                    currency="JPY",
                )
            g = groups[key]
            g.holdings.append(holding)
            g.total_value_jpy += value_jpy
            if cost_jpy is not None:
                g.total_cost_jpy += cost_jpy

        return CsvParseResult(
            provider="sbi_margin",
            snapshot_date=snapshot_date,
            exchange_rates={},
            account_groups=list(groups.values()),
        )


# ============================================================
# パーサーファクトリ
# ============================================================

_PARSERS: dict[str, type[CsvParser]] = {
    "rakuten": RakutenCsvParser,
    "rakuten_margin": RakutenMarginCsvParser,
    "rakuten_ideco": RakutenIdecoCsvParser,
    "rakuten_fund": RakutenFundCsvParser,
    "sbi_portfolio": SbiPortfolioCsvParser,
    "sbi_margin": SbiMarginCsvParser,
}


def get_csv_parser(provider: str) -> CsvParser:
    """プロバイダ名からパーサーインスタンスを返す。"""
    parser_cls = _PARSERS.get(provider)
    if parser_cls is None:
        msg = f"未対応のプロバイダ: {provider}"
        raise ValueError(msg)
    return parser_cls()


def extract_date_from_filename(filename: str) -> str | None:
    """ファイル名から日付を抽出。例: assetbalance(all)_20260308_151501.csv → 2026-03-08"""
    match = re.search(r"(\d{4})(\d{2})(\d{2})", filename)
    if match:
        return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
    return None
