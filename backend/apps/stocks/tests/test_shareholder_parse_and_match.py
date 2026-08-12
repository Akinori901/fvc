"""有報の代表者名パースとオーナー名寄せのテスト。

有報の実データは氏名が1文字ずつ全角スペースで区切られる場合があり
（例: "横　田　義　之"）、この形式でも正しく判定できることを確認する。
"""

from __future__ import annotations

from apps.stocks.application.services.owner_match_service import OwnerMatchService
from apps.stocks.application.services.shareholder_parse_service import ShareholderParseService


class TestParseRepresentative:
    def test_parses_name_split_by_ideographic_spaces(self) -> None:
        # 有報の表紙は1文字ずつ全角スペースで区切られることが多い
        result = ShareholderParseService().parse_representative("代表取締役社長　　横　田　義　之")
        assert result == "横田義之"

    def test_resolves_html_entities(self) -> None:
        # &#160;(NBSP) が実体参照のまま残っていても氏名を取り出せる
        result = ShareholderParseService().parse_representative("代表取締役社長 &#160;&#160;清藤 勉")
        assert result == "清藤勉"

    def test_strips_html_tags(self) -> None:
        result = ShareholderParseService().parse_representative("<p>代表取締役　山田　太郎</p>")
        assert result == "山田太郎"

    def test_returns_none_when_no_representative(self) -> None:
        assert ShareholderParseService().parse_representative("<p>該当事項はありません</p>") is None


class TestOwnerMatch:
    def _shareholders(self, *names: str) -> list[dict[str, object]]:
        return [{"name": n, "rank": i + 1, "ratio": 5.0} for i, n in enumerate(names)]

    def test_exact_match_ignores_spacing_differences(self) -> None:
        # 代表者 "清藤勉" と大株主 "清藤　勉" は空白の入り方だけが違う
        results = OwnerMatchService().match("清藤勉", self._shareholders("清藤　勉"))

        assert len(results) == 1
        assert results[0].match_type == "exact"

    def test_exact_match_with_character_split_shareholder(self) -> None:
        # 大株主側が1文字区切りのケース
        results = OwnerMatchService().match("井藤秀雄", self._shareholders("井 藤　秀 雄"))

        assert len(results) == 1
        assert results[0].match_type == "exact"

    def test_family_match_by_surname(self) -> None:
        results = OwnerMatchService().match("藤井宗徳", self._shareholders("藤井　将徳", "藤井　智徳"))

        assert len(results) == 2  # noqa: PLR2004
        assert all(r.match_type == "family" for r in results)

    def test_family_match_when_shareholder_is_character_split(self) -> None:
        # "横　田　征　子" は姓を切り出せないため先頭2文字で判定する
        results = OwnerMatchService().match("横田義之", self._shareholders("横　田　征　子"))

        assert len(results) == 1
        assert results[0].match_type == "family"

    def test_excludes_institutional_shareholders(self) -> None:
        # 信託銀行等は代表者と姓が一致しても除外する
        results = OwnerMatchService().match("日本太郎", self._shareholders("日本マスタートラスト信託銀行株式会社"))

        assert results == []

    def test_returns_empty_when_no_relation(self) -> None:
        results = OwnerMatchService().match("鳥居良彦", self._shareholders("株式会社サンプル", "山田　花子"))

        assert results == []
