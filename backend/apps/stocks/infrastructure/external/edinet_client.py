"""EDINET APIクライアント。有報の書類一覧取得・XBRL取得を行う。"""

from __future__ import annotations

import io
import logging
import time
import zipfile
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.edinet-fsa.go.jp/api/v2"
_REQUEST_INTERVAL = 4.0  # 秒（EDINET推奨: 3-5秒）


@dataclass
class EdinetDocument:
    """EDINET書類メタデータ"""

    doc_id: str
    sec_code: str | None  # 5桁の証券コード（末尾チェックディジット付き）
    filer_name: str
    doc_description: str
    period_end: str | None  # "2025-03-31" 等


@dataclass
class EdinetXbrlContent:
    """有報から抽出したXBRLコンテンツ"""

    major_shareholders_html: str | None  # 大株主テーブルHTML
    representative_html: str | None  # 代表者情報HTML


class EdinetClientService:
    """EDINET API通信サービス。"""

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._last_request_time: float = 0

    def fetch_documents(self, date_str: str) -> list[EdinetDocument]:
        """指定日の有価証券報告書一覧を取得。

        Args:
            date_str: "YYYY-MM-DD" 形式
        """
        self._rate_limit()
        url = f"{_BASE_URL}/documents.json"
        params = {
            "date": date_str,
            "type": "2",  # 有報
            "Subscription-Key": self._api_key,
        }

        try:
            with httpx.Client(timeout=30) as client:
                resp = client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError as e:
            logger.warning("EDINET 書類一覧取得失敗 (date=%s, status=%s)", date_str, e.response.status_code)
            return []
        except httpx.HTTPError:
            logger.warning("EDINET 書類一覧取得 ネットワークエラー (date=%s)", date_str, exc_info=True)
            return []

        results: list[EdinetDocument] = []
        for doc in data.get("results", []):
            # 有報（ordinanceCode=010, formCode=030040）のみ
            if doc.get("ordinanceCode") != "010" or doc.get("formCode") != "030040":
                continue
            sec_code = doc.get("secCode")
            if not sec_code:
                continue

            results.append(
                EdinetDocument(
                    doc_id=doc["docID"],
                    sec_code=sec_code,
                    filer_name=doc.get("filerName", ""),
                    doc_description=doc.get("docDescription", ""),
                    period_end=doc.get("periodEnd"),
                )
            )

        return results

    def fetch_xbrl_content(self, doc_id: str) -> EdinetXbrlContent | None:
        """有報のXBRLコンテンツ（大株主・代表者情報）を取得。

        ZIPをダウンロードし、XBRLファイルからテキストブロックを抽出。
        """
        self._rate_limit()
        url = f"{_BASE_URL}/documents/{doc_id}"
        params = {
            "type": "5",  # XBRL + CSV
            "Subscription-Key": self._api_key,
        }

        try:
            with httpx.Client(timeout=60) as client:
                resp = client.get(url, params=params)
                resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.warning("EDINET XBRL取得失敗 (doc=%s, status=%s)", doc_id, e.response.status_code)
            return None
        except httpx.HTTPError:
            logger.warning("EDINET XBRL取得 ネットワークエラー (doc=%s)", doc_id, exc_info=True)
            return None

        return self._extract_from_zip(resp.content, doc_id)

    def _extract_from_zip(self, zip_bytes: bytes, doc_id: str) -> EdinetXbrlContent | None:
        """ZIPから大株主・代表者情報のHTMLブロックを抽出。"""
        try:
            zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
        except zipfile.BadZipFile:
            logger.warning("EDINET ZIPファイル破損 (doc=%s)", doc_id)
            return None

        shareholders_html: str | None = None
        representative_html: str | None = None

        for name in zf.namelist():
            if not name.endswith(".htm") and not name.endswith(".html"):
                continue

            try:
                content = zf.read(name).decode("utf-8", errors="replace")
            except Exception:
                continue

            # 大株主テキストブロック
            if shareholders_html is None:
                block = self._extract_text_block(content, "MajorShareholdersTextBlock")
                if block:
                    shareholders_html = block

            # 代表者情報テキストブロック
            if representative_html is None:
                for tag_name in [
                    "CompanyRepresentativeInformationTextBlock",
                    "BusinessManagerNameInformationTextBlock",
                ]:
                    block = self._extract_text_block(content, tag_name)
                    if block:
                        representative_html = block
                        break

            if shareholders_html and representative_html:
                break

        if not shareholders_html:
            return None

        return EdinetXbrlContent(
            major_shareholders_html=shareholders_html,
            representative_html=representative_html,
        )

    def _extract_text_block(self, xbrl_content: str, tag_suffix: str) -> str | None:
        """XBRLコンテンツからテキストブロックを抽出。contextRef付きタグを検索。"""
        import re

        # jpcrp_cor:MajorShareholdersTextBlock 等のタグを検索
        pattern = rf"<[^>]*{re.escape(tag_suffix)}[^>]*>(.*?)</[^>]*{re.escape(tag_suffix)}>"
        m = re.search(pattern, xbrl_content, re.DOTALL)
        if m:
            return m.group(1)
        return None

    def _rate_limit(self) -> None:
        """EDINET推奨のリクエスト間隔を確保。"""
        elapsed = time.time() - self._last_request_time
        if elapsed < _REQUEST_INTERVAL:
            time.sleep(_REQUEST_INTERVAL - elapsed)
        self._last_request_time = time.time()

    @staticmethod
    def sec_code_to_stock_code(sec_code: str) -> str:
        """EDINETの5桁secCodeから4桁証券コードを導出。末尾チェックディジットを除去。"""
        return sec_code[:4] if len(sec_code) >= 5 else sec_code  # noqa: PLR2004
