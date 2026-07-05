"""XBRL HTMLテーブルから大株主・代表者名を解析するサービス。"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from html.parser import HTMLParser

logger = logging.getLogger(__name__)


@dataclass
class ParsedShareholder:
    """パースされた大株主データ"""

    name: str
    rank: int
    ownership_ratio: float
    shares_held: int | None = None


class ShareholderParseService:
    """有報XBRL内の大株主テーブルHTMLをパースする。"""

    def parse_shareholders(self, html: str) -> list[ParsedShareholder]:
        """大株主テーブルHTMLから大株主リストを抽出。"""
        parser = _TableParser()
        try:
            parser.feed(html)
        except Exception:
            logger.warning("大株主テーブルのHTMLパースに失敗", exc_info=True)
            return []

        rows = parser.rows
        if len(rows) < 2:  # noqa: PLR2004
            return []

        results: list[ParsedShareholder] = []
        for rank, row in enumerate(rows[1:], start=1):  # ヘッダ行をスキップ
            if rank > 10:  # noqa: PLR2004
                break
            if len(row) < 3:  # noqa: PLR2004
                continue

            name = row[0].strip()
            if not name:
                continue

            # 持ち株比率の抽出（"12.50" or "12.50%"）
            ratio = self._parse_ratio(row[-1])
            if ratio is None:
                # 2列目も試す
                ratio = self._parse_ratio(row[1]) if len(row) > 2 else None  # noqa: PLR2004
            if ratio is None:
                continue

            # 保有株数の抽出（カンマ区切り数値）
            shares = self._parse_shares(row[1]) if len(row) > 2 else None  # noqa: PLR2004

            results.append(ParsedShareholder(name=name, rank=rank, ownership_ratio=ratio, shares_held=shares))

        return results

    def parse_representative(self, html: str) -> str | None:
        """代表者情報テキストブロックから代表者名を抽出。"""
        # 「代表取締役社長」「代表取締役」の後に続く名前を抽出
        patterns = [
            r"代表取締役(?:社長|会長)?[　\s]*([^\s<　]{1,4}[　\s]+[^\s<　]{1,4})",
            r"代表取締役(?:社長|会長)?[　\s]*([^\s<　]{2,8})",
        ]
        # HTMLタグを除去
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text)

        for pattern in patterns:
            m = re.search(pattern, text)
            if m:
                return m.group(1).strip()
        return None

    def _parse_ratio(self, text: str) -> float | None:
        """テキストから持ち株比率を抽出。"""
        text = text.strip().replace("%", "").replace("％", "")
        m = re.search(r"(\d+\.?\d*)", text)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                return None
        return None

    def _parse_shares(self, text: str) -> int | None:
        """テキストから保有株数を抽出（カンマ区切り対応）。"""
        text = text.strip().replace(",", "").replace("，", "")
        m = re.search(r"(\d+)", text)
        if m:
            try:
                return int(m.group(1))
            except ValueError:
                return None
        return None


class _TableParser(HTMLParser):
    """HTMLテーブルから行×セルの2次元配列を抽出する簡易パーサー。"""

    def __init__(self) -> None:
        super().__init__()
        self.rows: list[list[str]] = []
        self._current_row: list[str] = []
        self._current_cell: list[str] = []
        self._in_cell = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr":
            self._current_row = []
        elif tag in ("td", "th"):
            self._in_cell = True
            self._current_cell = []

    def handle_endtag(self, tag: str) -> None:
        if tag in ("td", "th"):
            self._in_cell = False
            self._current_row.append("".join(self._current_cell))
        elif tag == "tr":
            if self._current_row:
                self.rows.append(self._current_row)

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._current_cell.append(data)
