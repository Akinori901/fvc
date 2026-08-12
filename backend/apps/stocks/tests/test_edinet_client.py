"""EDINET APIクライアントのユニットテスト。"""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from apps.stocks.infrastructure.external.edinet_client import EdinetClientService


class _MockResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self._payload


class _MockClient:
    """httpx.Client の代替。呼び出し時の params / headers を記録する。"""

    captured: dict[str, Any] = {}

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        pass

    def __enter__(self) -> _MockClient:
        return self

    def __exit__(self, *_args: Any) -> None:
        return None

    def get(self, url: str, params: dict[str, Any], headers: dict[str, str]) -> _MockResponse:
        _MockClient.captured = {"url": url, "params": params, "headers": headers}
        return _MockResponse(
            {
                "results": [
                    # 有報（採用されるべき）
                    {
                        "docID": "S100AAAA",
                        "secCode": "13010",
                        "ordinanceCode": "010",
                        "formCode": "030000",
                        "filerName": "テスト株式会社",
                        "docDescription": "有価証券報告書－第1期",
                        "periodEnd": "2026-03-31",
                    },
                    # 半期報告書（除外されるべき）
                    {
                        "docID": "S100BBBB",
                        "secCode": "13020",
                        "ordinanceCode": "010",
                        "formCode": "043000",
                        "filerName": "除外株式会社",
                        "docDescription": "半期報告書",
                        "periodEnd": "2026-03-31",
                    },
                    # secCode 無し（除外されるべき）
                    {
                        "docID": "S100CCCC",
                        "secCode": None,
                        "ordinanceCode": "010",
                        "formCode": "030000",
                        "filerName": "非上場株式会社",
                        "docDescription": "有価証券報告書",
                        "periodEnd": "2026-03-31",
                    },
                ]
            }
        )


@pytest.fixture
def _mock_httpx(monkeypatch: pytest.MonkeyPatch) -> None:
    _MockClient.captured = {}
    monkeypatch.setattr(httpx, "Client", _MockClient)


@pytest.mark.usefixtures("_mock_httpx")
class TestFetchDocuments:
    def test_api_key_is_sent_as_header_not_query(self) -> None:
        # クエリに載せると httpx のログにフルURLごと記録されてしまうため
        EdinetClientService(api_key="secret-key").fetch_documents("2026-06-26")

        captured = _MockClient.captured
        assert captured["headers"]["Ocp-Apim-Subscription-Key"] == "secret-key"
        assert "Subscription-Key" not in captured["params"]
        assert "secret-key" not in str(captured["params"])

    def test_extracts_only_annual_reports(self) -> None:
        # 有価証券報告書の formCode は 030000（030040 ではない）
        docs = EdinetClientService(api_key="k").fetch_documents("2026-06-26")

        assert len(docs) == 1
        assert docs[0].doc_id == "S100AAAA"
        assert docs[0].sec_code == "13010"

    def test_skips_documents_without_sec_code(self) -> None:
        docs = EdinetClientService(api_key="k").fetch_documents("2026-06-26")

        assert all(d.sec_code for d in docs)
        assert "S100CCCC" not in [d.doc_id for d in docs]
