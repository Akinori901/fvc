"""sync_shareholders の分割実行（limit / skip_processed）のテスト。"""

from __future__ import annotations

from typing import Any

from apps.stocks.application.usecases.sync_shareholders_usecase import SyncShareholdersUseCase


class _Doc:
    def __init__(self, doc_id: str, sec_code: str) -> None:
        self.doc_id = doc_id
        self.sec_code = sec_code
        self.period_end = "2026-03-31"


class _FakeEdinet:
    def __init__(self, docs: list[_Doc]) -> None:
        self._docs = docs
        self.fetched_doc_ids: list[str] = []

    def fetch_documents(self, date_str: str) -> list[_Doc]:  # noqa: ARG002
        return self._docs

    def sec_code_to_stock_code(self, sec_code: str) -> str:
        return sec_code[:4]


class _FakeStockRepo:
    def find_by_market_type(self, market_type: str) -> list[Any]:  # noqa: ARG002
        class _S:
            def __init__(self, code: str, sid: int) -> None:
                self.code = code
                self.id = sid

        return [_S("1301", 1), _S("1302", 2), _S("1303", 3)]


class _FakeRawRepo:
    def __init__(self, processed: set[str] | None = None) -> None:
        self._processed = processed or set()

    def find_processed_doc_ids(self) -> set[str]:
        return self._processed

    def save_batch(self, *_args: Any, **_kwargs: Any) -> None:
        return None


def _make_usecase(docs: list[_Doc], processed: set[str] | None = None) -> tuple[SyncShareholdersUseCase, list[str]]:
    """_process_document を呼び出し記録に差し替えたユースケースを返す。"""
    calls: list[str] = []
    uc = SyncShareholdersUseCase(
        edinet_client=_FakeEdinet(docs),  # type: ignore[arg-type]
        parse_service=None,  # type: ignore[arg-type]
        match_service=None,  # type: ignore[arg-type]
        stock_repo=_FakeStockRepo(),  # type: ignore[arg-type]
        owner_repo=None,  # type: ignore[arg-type]
        raw_repo=_FakeRawRepo(processed),  # type: ignore[arg-type]
    )

    def _fake_process(doc: Any, stock_code: str, stock_id: int, dry_run: bool, stats: dict[str, int]) -> None:  # noqa: ARG001, FBT001
        calls.append(doc.doc_id)
        stats["processed"] += 1

    uc._process_document = _fake_process  # type: ignore[method-assign]  # noqa: SLF001
    return uc, calls


_DOCS = [_Doc("D1", "13010"), _Doc("D2", "13020"), _Doc("D3", "13030")]


class TestSyncShareholdersLimit:
    def test_limit_stops_processing_and_reports_remaining(self) -> None:
        uc, calls = _make_usecase(_DOCS)

        stats = uc.execute(from_date="2026-06-26", to_date="2026-06-26", limit=2)

        assert calls == ["D1", "D2"]
        assert stats["processed"] == 2  # noqa: PLR2004
        assert stats["remaining"] == 1

    def test_no_limit_processes_all(self) -> None:
        uc, calls = _make_usecase(_DOCS)

        stats = uc.execute(from_date="2026-06-26", to_date="2026-06-26")

        assert calls == ["D1", "D2", "D3"]
        assert stats["remaining"] == 0

    def test_already_processed_documents_are_skipped(self) -> None:
        # 再実行時に取得済みを飛ばして続きから進める
        uc, calls = _make_usecase(_DOCS, processed={"D1", "D2"})

        stats = uc.execute(from_date="2026-06-26", to_date="2026-06-26")

        assert calls == ["D3"]
        assert stats["processed"] == 1

    def test_skip_processed_can_be_disabled(self) -> None:
        uc, calls = _make_usecase(_DOCS, processed={"D1"})

        uc.execute(from_date="2026-06-26", to_date="2026-06-26", skip_processed=False)

        assert calls == ["D1", "D2", "D3"]

    def test_dry_run_does_not_consult_processed_ids(self) -> None:
        # dry-run は書き込まないため、取得済み判定で件数が変わらないこと
        uc, calls = _make_usecase(_DOCS, processed={"D1", "D2", "D3"})

        uc.execute(from_date="2026-06-26", to_date="2026-06-26", dry_run=True)

        assert calls == ["D1", "D2", "D3"]
