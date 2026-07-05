"""CSV インポートサービスのテスト (SBI ポートフォリオパーサ中心)。"""

from __future__ import annotations

import io
from decimal import Decimal

import pytest

from apps.portfolios.application.services.csv_import_service import (
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
