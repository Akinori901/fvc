"""EDINET大株主データ同期ユースケース。"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import TYPE_CHECKING

from django.db import transaction

if TYPE_CHECKING:
    from apps.stocks.application.services.owner_match_service import MatchResult, OwnerMatchService
    from apps.stocks.application.services.shareholder_parse_service import ParsedShareholder, ShareholderParseService
    from apps.stocks.domain.repositories import (
        OwnerShareholderRepository,
        ShareholderRawRepository,
        StockRepository,
    )
    from apps.stocks.infrastructure.external.edinet_client import EdinetClientService

logger = logging.getLogger(__name__)


class SyncShareholdersUseCase:
    """EDINET有報から大株主データを取得し、オーナー経営判定を行う。"""

    def __init__(
        self,
        edinet_client: EdinetClientService,
        parse_service: ShareholderParseService,
        match_service: OwnerMatchService,
        stock_repo: StockRepository,
        owner_repo: OwnerShareholderRepository,
        raw_repo: ShareholderRawRepository,
    ) -> None:
        self._edinet = edinet_client
        self._parser = parse_service
        self._matcher = match_service
        self._stock_repo = stock_repo
        self._owner_repo = owner_repo
        self._raw_repo = raw_repo

    def execute(
        self,
        from_date: str,
        to_date: str,
        codes: list[str] | None = None,
        dry_run: bool = False,
        limit: int | None = None,
        skip_processed: bool = True,
    ) -> dict[str, int]:
        """大株主データを同期。

        Args:
            from_date: 開始日（"YYYY-MM-DD"）
            to_date: 終了日（"YYYY-MM-DD"）
            codes: 対象証券コード（None=全銘柄）
            dry_run: True の場合はDB書き込みを行わない
            limit: この件数を処理したら打ち切る（Lambda の実行時間上限対策）
            skip_processed: 取得済み doc_id を再取得しない（再実行で続きから進める）

        Returns:
            {"processed": N, "matched": N, "skipped": N, "errors": N, "remaining": N}

        有報1件ごとにXBRLのZIP取得とレート制限待ちが入るため、
        件数が多い日は1回の実行で終わらない。limit で区切って複数回実行し、
        skip_processed により前回の続きから進める運用を想定している。
        """
        from datetime import date, timedelta

        start = date.fromisoformat(from_date)
        end = date.fromisoformat(to_date)

        # 証券コード→stock_id のマップを構築
        stock_map = self._build_stock_map(codes)

        processed_doc_ids: set[str] = set()
        if skip_processed and not dry_run:
            try:
                processed_doc_ids = self._raw_repo.find_processed_doc_ids()
                logger.info("取得済み書類: %d 件（スキップ対象）", len(processed_doc_ids))
            except NotImplementedError:
                logger.warning("取得済み判定に非対応のため全件処理します")

        stats = {"processed": 0, "matched": 0, "skipped": 0, "errors": 0, "remaining": 0}

        current = start
        while current <= end:
            date_str = current.isoformat()
            logger.info("EDINET 書類一覧取得: %s", date_str)

            try:
                documents = self._edinet.fetch_documents(date_str)
            except Exception:
                logger.warning("EDINET 書類一覧取得エラー: %s", date_str, exc_info=True)
                stats["errors"] += 1
                current += timedelta(days=1)
                continue

            for doc in documents:
                if doc.sec_code is None:
                    continue

                stock_code = self._edinet.sec_code_to_stock_code(doc.sec_code)

                # 対象銘柄フィルター
                if codes and stock_code not in codes:
                    continue
                if stock_code not in stock_map:
                    stats["skipped"] += 1
                    continue

                # 取得済みは再取得しない（再実行で続きから進めるため）
                if doc.doc_id in processed_doc_ids:
                    continue

                # 実行時間上限に達したら残件を報告して打ち切る
                if limit is not None and stats["processed"] >= limit:
                    stats["remaining"] += 1
                    continue

                try:
                    self._process_document(doc, stock_code, stock_map[stock_code], dry_run, stats)
                except Exception:
                    logger.warning(
                        "EDINET 書類処理エラー: doc=%s, code=%s",
                        doc.doc_id,
                        stock_code,
                        exc_info=True,
                    )
                    stats["errors"] += 1

            current += timedelta(days=1)

        logger.info(
            "大株主同期完了: processed=%d, matched=%d, skipped=%d, errors=%d, remaining=%d",
            stats["processed"],
            stats["matched"],
            stats["skipped"],
            stats["errors"],
            stats["remaining"],
        )
        return stats

    def _process_document(
        self,
        doc: object,
        stock_code: str,
        stock_id: int,
        dry_run: bool,
        stats: dict[str, int],
    ) -> None:
        """1書類を処理。"""
        from apps.stocks.infrastructure.external.edinet_client import EdinetDocument

        assert isinstance(doc, EdinetDocument)

        xbrl = self._edinet.fetch_xbrl_content(doc.doc_id)
        if xbrl is None or xbrl.major_shareholders_html is None:
            stats["skipped"] += 1
            return

        # 大株主テーブルをパース
        shareholders = self._parser.parse_shareholders(xbrl.major_shareholders_html)
        if not shareholders:
            stats["skipped"] += 1
            return

        # 代表者名を抽出
        rep_name: str | None = None
        if xbrl.representative_html:
            rep_name = self._parser.parse_representative(xbrl.representative_html)

        if not rep_name:
            logger.info("代表者名が取得できません: doc=%s, code=%s", doc.doc_id, stock_code)
            stats["skipped"] += 1
            return

        # 決算年度の推定
        fiscal_year = int(doc.period_end[:4]) if doc.period_end else 0

        # 名寄せ
        sh_dicts = [{"name": s.name, "rank": s.rank, "ratio": s.ownership_ratio} for s in shareholders]
        matches = self._matcher.match(rep_name, sh_dicts)

        stats["processed"] += 1
        if matches:
            stats["matched"] += len(matches)

        if dry_run:
            logger.info(
                "[DRY RUN] %s (%s): 代表=%s, 大株主=%d名, マッチ=%d件",
                stock_code,
                doc.doc_id,
                rep_name,
                len(shareholders),
                len(matches),
            )
            return

        # DB保存（トランザクション）
        self._save_results(
            stock_id=stock_id,
            fiscal_year=fiscal_year,
            doc_id=doc.doc_id,
            rep_name=rep_name,
            shareholders=shareholders,
            matches=matches,
        )

    @transaction.atomic
    def _save_results(
        self,
        stock_id: int,
        fiscal_year: int,
        doc_id: str,
        rep_name: str,
        shareholders: list[ParsedShareholder],
        matches: list[MatchResult],
    ) -> None:
        """名寄せ結果と生データをDB保存。"""
        from apps.stocks.application.services.owner_match_service import MatchResult
        from apps.stocks.application.services.shareholder_parse_service import ParsedShareholder
        from apps.stocks.domain.entities import OwnerShareholderEntity, ShareholderRawEntity

        # 生データ保存
        raw_entities = [
            ShareholderRawEntity(
                stock_id=stock_id,
                shareholder_name=sh.name,
                shareholder_rank=sh.rank,
                ownership_ratio=Decimal(str(sh.ownership_ratio)),
                shares_held=sh.shares_held if isinstance(sh, ParsedShareholder) else None,
                fiscal_year=fiscal_year,
                doc_id=doc_id,
            )
            for sh in shareholders
            if isinstance(sh, ParsedShareholder)
        ]
        self._raw_repo.save_batch(stock_id, fiscal_year, raw_entities)

        # マッチ結果保存
        owner_entities = [
            OwnerShareholderEntity(
                stock_id=stock_id,
                representative_name=rep_name,
                shareholder_name=m.shareholder_name,
                shareholder_rank=m.rank,
                ownership_ratio=Decimal(str(m.ownership_ratio)),
                match_type=m.match_type,
                fiscal_year=fiscal_year,
                doc_id=doc_id,
            )
            for m in matches
            if isinstance(m, MatchResult)
        ]
        self._owner_repo.save_batch(stock_id, fiscal_year, owner_entities)

    def _build_stock_map(self, codes: list[str] | None) -> dict[str, int]:
        """証券コード→stock_id のマップを構築。"""
        stocks = self._stock_repo.find_by_market_type("JP")
        result: dict[str, int] = {}
        for s in stocks:
            if s.id is not None and (codes is None or s.code in codes):
                result[s.code] = s.id
        return result
