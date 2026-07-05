from abc import ABC, abstractmethod

from .entities import (
    AccountSnapshotEntity,
    FamilyMemberEntity,
    PortfolioAccountEntity,
    WatchlistItemEntity,
)

# ============================================================
# 家族ポートフォリオ
# ============================================================


class FamilyMemberRepository(ABC):
    @abstractmethod
    def find_by_user(self, user_id: int) -> list[FamilyMemberEntity]: ...

    @abstractmethod
    def find_by_id(self, member_id: int, user_id: int) -> FamilyMemberEntity | None: ...

    @abstractmethod
    def save(self, entity: FamilyMemberEntity) -> FamilyMemberEntity: ...

    @abstractmethod
    def delete(self, member_id: int, user_id: int) -> None: ...


class PortfolioAccountRepository(ABC):
    @abstractmethod
    def find_by_user(self, user_id: int) -> list[PortfolioAccountEntity]: ...

    @abstractmethod
    def find_by_id(self, account_id: int, user_id: int) -> PortfolioAccountEntity | None: ...

    @abstractmethod
    def save(self, entity: PortfolioAccountEntity) -> PortfolioAccountEntity: ...

    @abstractmethod
    def delete(self, account_id: int, user_id: int) -> None: ...


class AccountSnapshotRepository(ABC):
    @abstractmethod
    def find_by_account(self, account_id: int, user_id: int) -> list[AccountSnapshotEntity]: ...

    @abstractmethod
    def find_by_account_and_date(
        self, account_id: int, snapshot_date: str, user_id: int
    ) -> AccountSnapshotEntity | None: ...

    @abstractmethod
    def save(self, entity: AccountSnapshotEntity, user_id: int) -> AccountSnapshotEntity: ...

    @abstractmethod
    def delete(self, account_id: int, snapshot_date: str, user_id: int) -> None: ...

    @abstractmethod
    def find_latest_by_user(self, user_id: int) -> list[AccountSnapshotEntity]: ...

    @abstractmethod
    def find_each_account_latest_before(
        self, user_id: int, as_of_date: str, with_holdings: bool = False
    ) -> list[AccountSnapshotEntity]:
        """各口座について、as_of_date 以前で最新のスナップショットを 1 件ずつ返す。

        月初来損益 (MTD) の baseline 計算に使用。
        as_of_date 以前にスナップショットが無い口座は結果に含まれない。

        Args:
            user_id: 対象ユーザー
            as_of_date: 基準日 (YYYY-MM-DD)。この日以前で最新のスナップショットを取得
            with_holdings: True なら holdings も読み込む (DynamicValuationService 用)。
                           False (デフォルト) なら holdings は空リスト (静的合計用、軽量)
        """
        ...

    @abstractmethod
    def find_latest_single(self, account_id: int, user_id: int) -> AccountSnapshotEntity | None: ...

    @abstractmethod
    def find_all_by_user(self, user_id: int) -> list[AccountSnapshotEntity]: ...

    @abstractmethod
    def find_earliest_date_by_user(self, user_id: int) -> str | None:
        """ユーザーの全スナップショットの最古日付を返す（YYYY-MM-DD）。データなし→None"""
        ...


class WatchlistRepository(ABC):
    @abstractmethod
    def find_by_user(self, user_id: int) -> list[WatchlistItemEntity]: ...

    @abstractmethod
    def find_by_user_and_stock(self, user_id: int, stock_code: str) -> WatchlistItemEntity | None: ...

    @abstractmethod
    def add(self, entity: WatchlistItemEntity) -> WatchlistItemEntity: ...

    @abstractmethod
    def remove(self, user_id: int, stock_code: str) -> None: ...
