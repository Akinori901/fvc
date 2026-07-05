"""ポートフォリオ口座の統合 (旧 → 新へ snapshot を付け替えて旧を削除)。

用途:
- CSV インポートで nickname が変わり新規口座が作られた場合に、既存口座と統合する
- 例: 「SBI特定投資信託」(旧) → 「特定預り」(新、CSV 取込で自動作成)

操作:
- 旧口座の AccountSnapshot を全て新口座 ID に付け替え (account_id update)
- 同日 snapshot がある (unique_together 違反) 場合はエラーで停止
- snapshot 付け替え後、旧口座を削除

実行例:
    aws lambda invoke --function-name fvc-worker \\
      --payload '{"command": "merge_portfolio_accounts", \\
                   "args": ["--from-id", "12", "--to-id", "47", "--dry-run"]}' ...
"""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand, CommandParser
from django.db import transaction

from apps.portfolios.models import AccountSnapshot, PortfolioAccount


class Command(BaseCommand):
    help = "ポートフォリオ口座 (PortfolioAccount) を統合し、snapshot を付け替えて旧口座を削除"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--from-id", type=int, required=True, help="統合元 (削除される) の口座 ID")
        parser.add_argument("--to-id", type=int, required=True, help="統合先 (残る) の口座 ID")
        parser.add_argument("--dry-run", action="store_true", help="実際の更新/削除を行わない")

    def handle(self, *args: Any, **options: Any) -> None:
        from_id: int = options["from_id"]
        to_id: int = options["to_id"]
        dry_run: bool = options["dry_run"]

        if from_id == to_id:
            self.stderr.write(self.style.ERROR("--from-id と --to-id が同じです"))
            return

        try:
            src = PortfolioAccount.objects.get(pk=from_id)
        except PortfolioAccount.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"--from-id={from_id} の口座が見つかりません"))
            return
        try:
            dst = PortfolioAccount.objects.get(pk=to_id)
        except PortfolioAccount.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"--to-id={to_id} の口座が見つかりません"))
            return

        # 同一家族メンバー所属チェック (誤マージ防止)
        if src.family_member_id != dst.family_member_id:
            self.stderr.write(
                self.style.ERROR(
                    f"family_member_id が異なります: src={src.family_member_id}, dst={dst.family_member_id}. "
                    "誤った口座同士の統合を防ぐため中止します。"
                )
            )
            return

        # snapshot 一覧と日付衝突チェック
        src_snapshots = AccountSnapshot.objects.filter(account_id=from_id).order_by("snapshot_date")
        src_dates = list(src_snapshots.values_list("snapshot_date", flat=True))
        dst_dates = set(AccountSnapshot.objects.filter(account_id=to_id).values_list("snapshot_date", flat=True))
        conflicts = [d for d in src_dates if d in dst_dates]

        self.stdout.write("=" * 60)
        self.stdout.write(f"統合元 (src): #{src.id}  {src.institution} / {src.nickname} ({src.asset_class})")
        self.stdout.write(f"統合先 (dst): #{dst.id}  {dst.institution} / {dst.nickname} ({dst.asset_class})")
        self.stdout.write(f"family_member_id (両者): {src.family_member_id}")
        self.stdout.write(f"src snapshot 件数: {len(src_dates)}")
        self.stdout.write(f"dst snapshot 件数: {len(dst_dates)}")
        self.stdout.write(f"日付衝突: {len(conflicts)} 件")
        if conflicts:
            self.stdout.write(self.style.WARNING(f"衝突日付: {[str(d) for d in conflicts]}"))
            self.stdout.write(
                self.style.ERROR(
                    "同じ日付の snapshot が src/dst 両方にあるため、unique_together 違反になります。"
                    "中止します。先に dst 側の重複日付 snapshot を手動削除してから再実行してください。"
                )
            )
            return

        if not src_dates:
            self.stdout.write(self.style.WARNING("src に snapshot がありません。src 口座のみ削除します。"))

        action = "DRY RUN" if dry_run else "EXEC"
        self.stdout.write(f"\n[{action}] {len(src_dates)} 件の snapshot を {from_id} → {to_id} に付け替え")
        for d in src_dates[:10]:
            self.stdout.write(f"  - {d}")
        if len(src_dates) > 10:
            self.stdout.write(f"  ... 他 {len(src_dates) - 10} 件")
        self.stdout.write(f"[{action}] 旧口座 #{from_id} を削除")

        if dry_run:
            self.stdout.write(self.style.SUCCESS("\n[DRY RUN] 完了 (実際には何も変更していません)"))
            return

        with transaction.atomic():
            updated = AccountSnapshot.objects.filter(account_id=from_id).update(account_id=to_id)
            src.delete()

        self.stdout.write(self.style.SUCCESS(f"\n完了: {updated} 件 snapshot 付け替え、旧口座 #{from_id} 削除"))
