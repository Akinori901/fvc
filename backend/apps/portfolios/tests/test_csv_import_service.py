"""CSV インポートサービスのテスト (SBI ポートフォリオパーサ中心)。"""

from __future__ import annotations

import io
from decimal import Decimal

import pytest

from apps.portfolios.application.services.csv_import_service import (
    CsvParseResult,
    RakutenJuniorNisaCsvParser,
    SbiMarginCsvParser,
    SbiPortfolioCsvParser,
    _detect_sbi_section,
)


class _FakeUploadedFile:
    """Django UploadedFile を模した最小実装。"""

    def __init__(self, content_bytes: bytes) -> None:
        self._buf = io.BytesIO(content_bytes)
        self.name = "sbi_test.csv"

    def read(self) -> bytes:
        return self._buf.read()


# SBI ポートフォリオ CSV のサンプル (Shift-JIS、投信 1 セクション)。
# 元データは「iFreeレバレッジ FANG+ / 数量 229221 / 取得単価 19623 / 現在値 40272 /
# 評価損益 +473318.44 / 評価額 923118.81」。
_SBI_FUND_CSV_TEXT = (
    "ポートフォリオ一覧\r\n"
    "一括表示\r\n"
    "PTS株価非表示\r\n"
    "総件数：1件\r\n"
    "選択範囲：1-1件\r\n"
    "ページ：1\r\n"
    "投資信託（金額/特定預り）\r\n"
    "ファンド名,買付日,数量,取得単価,現在値,前日比,前日比（％）,損益,損益（％）,評価額\r\n"
    "iFreeレバレッジ FANG+,----/--/--,229221,19623,40272,-1,0.00,473318.44,105.23,923118.81\r\n"
    "投資信託(金額/特定預り)合計\r\n"
    "評価額,含み損益,含み損益（％）,前日比,前日比（％）\r\n"
    "923118.81,473318.44,105.23,-22.92,0\r\n"
)


@pytest.fixture
def sbi_fund_csv_bytes() -> bytes:
    return _SBI_FUND_CSV_TEXT.encode("shift_jis")


class TestDetectSbiSection:
    def test_fund_section_with_specific(self) -> None:
        kind, acct = _detect_sbi_section("投資信託（金額/特定預り）")
        assert kind == "fund"
        assert acct == "特定預り"

    def test_fund_section_with_nisa(self) -> None:
        kind, acct = _detect_sbi_section("投資信託（金額/NISA成長投資枠）")
        assert kind == "fund"
        assert acct == "NISA成長投資枠"

    def test_total_row_is_not_a_section(self) -> None:
        kind, acct = _detect_sbi_section("投資信託(金額/特定預り)合計")
        assert kind is None
        assert acct == ""

    def test_empty_returns_none(self) -> None:
        kind, acct = _detect_sbi_section("")
        assert kind is None
        assert acct == ""

    def test_unrelated_returns_none(self) -> None:
        kind, acct = _detect_sbi_section("ポートフォリオ一覧")
        assert kind is None


class TestSbiPortfolioCsvParser:
    def test_parses_single_fund_section(self, sbi_fund_csv_bytes: bytes) -> None:
        parser = SbiPortfolioCsvParser()
        result = parser.parse(_FakeUploadedFile(sbi_fund_csv_bytes), "2026-05-27")  # type: ignore[arg-type]

        assert result.provider == "sbi_portfolio"
        assert result.snapshot_date == "2026-05-27"
        assert len(result.account_groups) == 1

        group = result.account_groups[0]
        assert group.asset_type_raw == "投資信託"
        assert group.account_type_raw == "特定預り"
        assert group.asset_class == "fund"
        assert group.total_value_jpy == Decimal("923118.81")

        # cost_jpy = quantity × unit_price / 10000 = 229221 × 19623 / 10000 ≒ 449800
        assert group.total_cost_jpy == (Decimal("229221") * Decimal("19623")) / Decimal(10000)

        assert len(group.holdings) == 1
        h = group.holdings[0]
        assert h.asset_name == "iFreeレバレッジ FANG+"
        assert h.asset_type == "fund"
        assert h.quantity == Decimal("229221")
        assert h.unit_price == Decimal("19623")
        assert h.value_jpy == Decimal("923118.81")
        assert h.currency == "JPY"

    def test_total_row_terminates_section(self, sbi_fund_csv_bytes: bytes) -> None:
        """『投資信託(金額/特定預り)合計』の後の集計行を明細として誤読しないこと。"""
        parser = SbiPortfolioCsvParser()
        result = parser.parse(_FakeUploadedFile(sbi_fund_csv_bytes), "2026-05-27")  # type: ignore[arg-type]
        group = result.account_groups[0]
        # 1 行のみ取り込まれる (合計行直後の `923118.81,473318.44,...` は明細扱いしない)
        assert len(group.holdings) == 1

    def test_handles_cp932_fallback(self) -> None:
        """shift_jis でなく cp932 でしか読めないバイトでも parser が落ちないこと。"""
        # NEC 拡張 (CP932 にしか無い) 文字 ① をファンド名に含む
        text = (
            "ポートフォリオ一覧\r\n"
            "投資信託（金額/特定預り）\r\n"
            "ファンド名,買付日,数量,取得単価,現在値,前日比,前日比（％）,損益,損益（％）,評価額\r\n"
            "テストファンド①,----/--/--,100,10000,12000,0,0.00,200,2.00,120000\r\n"
            "投資信託(金額/特定預り)合計\r\n"
        )
        raw = text.encode("cp932")
        parser = SbiPortfolioCsvParser()
        result = parser.parse(_FakeUploadedFile(raw), "2026-05-27")  # type: ignore[arg-type]
        assert len(result.account_groups) == 1
        assert result.account_groups[0].holdings[0].asset_name == "テストファンド①"


# SBI 信用建玉 CSV (marginbalance(JP)_*.csv) のサンプル (Shift-JIS)。
# 「特定」口座で 5892 ＹＵＴＯＲＩ を 4 建玉保有 (すべて買建・制度)。
_SBI_MARGIN_CSV_TEXT = (
    "■表示形式,個別銘柄\r\n"
    "\r\n"
    '保証金率（新規建）［％］,"125.89",保証金率［％］,"84.58",評価損益[円],"-49,778"\r\n'
    '売建[円],"0",買建[円],"3,735,100",合計[円],"3,735,100"\r\n'
    "\r\n"
    "口座区分,銘柄コード,銘柄名,市場名称,売買,信用区分,弁済期限,建玉数量［株］,執行中［株］,"
    "建単価[円],現在値［円］,現在値（前日比）［円］,保証金率［％］,保証金率（うち現金）［％］,"
    "建日,最終返済日,時価評価額［円］,評価損益額［円］,評価損益率［％］,"
    "建手数料［円］（税抜）,逆日歩［円］,名義書換料［円］（税抜）,金利［円］,貸株料［円］,"
    "事務管理費［円］（税抜）,税金［円］\r\n"
    '"特定","5892","ＹＵＴＯＲＩ","東証","買建","制度","6ヶ月","500","0","2,500",'
    '"2,316","-62","30.00","0.00","2025/12/02","2026/06/01","1,158,000","-110,181","-8.81",'
    '"0","0","0","0","0","0","0"\r\n'
    '"特定","5892","ＹＵＴＯＲＩ","東証","買建","制度","6ヶ月","300","0","1,870",'
    '"2,316","-62","30.00","0.00","2026/05/12","2026/11/11","694,800","132,939","23.69",'
    '"0","0","0","0","0","0","0"\r\n'
)


class TestSbiMarginCsvParser:
    def test_parses_buy_margin_positions(self) -> None:
        parser = SbiMarginCsvParser()
        raw = _SBI_MARGIN_CSV_TEXT.encode("shift_jis")
        result = parser.parse(_FakeUploadedFile(raw), "2026-05-28")  # type: ignore[arg-type]

        assert result.provider == "sbi_margin"
        assert result.snapshot_date == "2026-05-28"
        assert len(result.account_groups) == 1

        group = result.account_groups[0]
        assert group.asset_type_raw == "国内株式（信用）"
        # nickname は CSV の口座区分「特定」+ 「信用」サフィックスで「特定信用」
        # → 同じ証券会社の現物口座 (nickname="特定") と衝突しない
        assert group.account_type_raw == "特定信用"
        assert group.asset_class == "jp_stock"
        # 評価額合計 = 1,158,000 + 694,800
        assert group.total_value_jpy == Decimal("1852800")
        # cost = value - gain. 110,181 損失なので cost = 1,158,000 - (-110,181) = 1,268,181
        # cost = 694,800 - 132,939 = 561,861. 合計 1,830,042
        assert group.total_cost_jpy == Decimal("1830042")

        assert len(group.holdings) == 2
        h0 = group.holdings[0]
        assert h0.ticker_code == "5892"
        assert h0.asset_type == "stock"
        assert h0.quantity == Decimal("500")
        assert h0.unit_price == Decimal("2500")
        assert h0.value_jpy == Decimal("1158000")  # 買建は positive
        assert h0.cost_jpy == Decimal("1268181")
        # asset_name に売買・信用区分・建日が付与される
        assert "買建" in h0.asset_name
        assert "制度" in h0.asset_name
        assert "2025/12/02" in h0.asset_name

    def test_sell_margin_becomes_negative_position(self) -> None:
        """売建は value_jpy / cost_jpy が負の値で保存されること。"""
        text = (
            "口座区分,銘柄コード,銘柄名,市場名称,売買,信用区分,弁済期限,建玉数量［株］,執行中［株］,"
            "建単価[円],現在値［円］,現在値（前日比）［円］,保証金率［％］,保証金率（うち現金）［％］,"
            "建日,最終返済日,時価評価額［円］,評価損益額［円］,評価損益率［％］\r\n"
            '"特定","9999","ダミー","東証","売建","制度","6ヶ月","100","0","1,000",'
            '"900","0","30.00","0.00","2026/05/01","2026/11/01","90,000","10,000","11.11"\r\n'
        )
        raw = text.encode("shift_jis")
        parser = SbiMarginCsvParser()
        result = parser.parse(_FakeUploadedFile(raw), "2026-05-28")  # type: ignore[arg-type]

        assert len(result.account_groups) == 1
        group = result.account_groups[0]
        assert len(group.holdings) == 1
        h = group.holdings[0]
        # 売建: value = -90,000, cost = -(90,000 - 10,000) = -80,000
        assert h.value_jpy == Decimal("-90000")
        assert h.cost_jpy == Decimal("-80000")
        assert "売建" in h.asset_name
        # 合計も負になる
        assert group.total_value_jpy == Decimal("-90000")

    def test_empty_csv_returns_no_groups(self) -> None:
        """ヘッダー行が見つからない場合、空の結果を返すこと (例外を投げない)。"""
        text = "ダミー行\r\n別のダミー行\r\n"
        raw = text.encode("shift_jis")
        parser = SbiMarginCsvParser()
        result = parser.parse(_FakeUploadedFile(raw), "2026-05-28")  # type: ignore[arg-type]
        assert result.provider == "sbi_margin"
        assert result.account_groups == []


# 楽天証券 ジュニアNISA CSV (assetbalance(INVST)、Shift-JIS、21列)。
# 実データ: 娘のジュニアNISA単独DL。口座区分列は "NISA" だが取込では
# nickname を "ジュニアNISA" に固定して既存口座に集約する。
# 列: 0保有区分,1口座区分,2ファンド,3分配金コース,4保有数量,5内訳通常,6内訳積立,
#     7平均取得価額,8取得総額,9基準価額,10前日比,11前月比,12時価評価額,13評価損益,
#     14評価損益%,15トータルリターン,16-20(外貨関連,当口座は"-")
_JUNIOR_NISA_CSV_TEXT = (
    "保有区分,口座区分,ファンド,分配金コース,保有数量[口],(内訳)通常[口],(内訳)積立[口],"
    "平均取得価額[円],取得総額[円],基準価額[円],基準価額(前日比)[円],基準価額(前月比)[円],"
    "時価評価額[円],評価損益[円],評価損益[％],トータルリターン[円],評価金額通貨単位,買付余力,参考為替,評価額(外貨),評価額[円]\r\n"
    '"娘","NISA","楽天・S&P500インデックス・ファンド（楽天・VTI）","再投資","52,354","9,399","42,955",'
    '"23,255.15","121,750","45,493","-144","457","238,174","116,424","95.62","116,424","-","-","-","-","-"\r\n'
    '"娘","NISA","eMAXIS Slim 国内株式（日経平均）","再投資","63,883","0","63,883",'
    '"15,105.74","96,499","31,747","-1,333","-2,932","202,809","106,309","110.16","106,309","-","-","-","-","-"\r\n'
    '"娘","NISA","eMAXIS Slim 米国株式（S&P500）","再投資","53,470","9,606","43,864",'
    '"22,769.78","121,750","45,008","-150","609","240,658","118,908","97.66","118,908","-","-","-","-","-"\r\n'
    '"娘","NISA","eMAXIS Slim 全世界株式（オール・カントリー）","再投資","46,504","11,061","35,443",'
    '"19,729.49","91,750","38,338","-188","321","178,287","86,537","94.31","86,537","-","-","-","-","-"\r\n'
    '"娘","NISA","iFreeNEXT インド株インデックス","再投資","91,056","55,208","35,848",'
    '"12,107.93","110,249","14,206","15","-158","129,354","19,104","17.32","19,104","-","-","-","-","-"\r\n'
)


class TestRakutenJuniorNisaCsvParser:
    def _parse(self) -> CsvParseResult:
        raw = _JUNIOR_NISA_CSV_TEXT.encode("shift_jis")
        parser = RakutenJuniorNisaCsvParser()
        return parser.parse(_FakeUploadedFile(raw), "2026-07-21")  # type: ignore[arg-type]

    def test_provider_is_junior_nisa(self) -> None:
        result = self._parse()
        assert result.provider == "rakuten_junior_nisa"

    def test_all_holdings_in_single_junior_nisa_group(self) -> None:
        """口座区分 "NISA" でも 1 グループにまとまり、nickname は "ジュニアNISA" に固定される。"""
        result = self._parse()
        assert len(result.account_groups) == 1
        group = result.account_groups[0]
        # 既存の「ジュニアNISA」口座に集約するためのキー
        assert group.account_type_raw == "ジュニアNISA"
        assert group.asset_class == "fund"
        assert len(group.holdings) == 5

    def test_totals_match_source_csv(self) -> None:
        """8列目「取得総額」を取得原価に使う。評価額・原価が実データと一致すること。"""
        result = self._parse()
        group = result.account_groups[0]
        # 時価評価額(12列目)の合計
        assert group.total_value_jpy == Decimal("989282")
        # 取得総額(8列目)の合計 = 正しい取得原価
        assert group.total_cost_jpy == Decimal("541998")

    def test_holding_fields_use_correct_columns(self) -> None:
        result = self._parse()
        vti = next(h for h in result.account_groups[0].holdings if "楽天・VTI" in h.asset_name)
        assert vti.asset_type == "fund"
        assert vti.quantity == Decimal("52354")  # 4列目 保有数量
        assert vti.unit_price == Decimal("45493")  # 9列目 基準価額
        assert vti.value_jpy == Decimal("238174")  # 12列目 時価評価額
        assert vti.cost_jpy == Decimal("121750")  # 8列目 取得総額
