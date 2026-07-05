"""名寄せロジック（ルールベース判定）。代表者名と大株主名を突合する。"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

# 機関投資家を除外するキーワード
_INSTITUTIONAL_KEYWORDS = frozenset(
    {
        "信託銀行",
        "マスタートラスト",
        "カストディ",
        "CUSTODY",
        "証券",
        "SECURITIES",
        "保険",
        "INSURANCE",
        "投資顧問",
        "日本銀行",
        "年金",
        "PENSION",
        "ファンド",
        "FUND",
        "アセットマネジメント",
        "ASSET",
    }
)


@dataclass
class MatchResult:
    """名寄せ判定結果"""

    shareholder_name: str
    rank: int
    ownership_ratio: float
    match_type: str  # "exact" / "family" / "company" / "none"


class OwnerMatchService:
    """代表者名と大株主リストを突合し、オーナー経営判定を行う。"""

    def match(
        self,
        representative_name: str,
        shareholders: list[dict[str, object]],
    ) -> list[MatchResult]:
        """名寄せ判定を実行。マッチした結果のみ返す（match_type="none" は除外）。

        Args:
            representative_name: 代表者氏名（例: "田中 一郎"）
            shareholders: 大株主リスト。各要素は {"name": str, "rank": int, "ratio": float}
        """
        norm_rep = self._normalize(representative_name)
        family_name = self._extract_family_name(norm_rep)

        results: list[MatchResult] = []
        for sh in shareholders:
            name = str(sh["name"])
            norm_name = self._normalize(name)
            rank = int(str(sh["rank"]))
            ratio = float(str(sh["ratio"]))

            # 機関投資家の除外
            if self._is_institutional(norm_name):
                continue

            # 完全一致
            if norm_rep == norm_name:
                results.append(MatchResult(name, rank, ratio, "exact"))
                continue

            # 個人名判定（スペース含む or 漢字2-4文字）
            if self._is_personal_name(norm_name):
                sh_family = self._extract_family_name(norm_name)
                if family_name and sh_family and family_name == sh_family:
                    results.append(MatchResult(name, rank, ratio, "family"))
                    continue

            # 法人名に姓が含まれるか
            if family_name and family_name in norm_name:
                results.append(MatchResult(name, rank, ratio, "company"))
                continue

        return results

    def _normalize(self, text: str) -> str:
        """全角→半角スペース正規化、前後空白除去、NFKC正規化。"""
        text = unicodedata.normalize("NFKC", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _extract_family_name(self, name: str) -> str:
        """姓を抽出（スペース区切りの先頭）。"""
        parts = name.split(" ")
        return parts[0] if parts else ""

    def _is_personal_name(self, name: str) -> bool:
        """個人名かどうかを推定。スペース含む or 漢字2-4文字。"""
        if " " in name:
            parts = name.split(" ")
            if len(parts) == 2 and all(len(p) <= 4 for p in parts):  # noqa: PLR2004
                return True
        # 漢字のみ2-4文字
        return bool(re.match(r"^[\u4e00-\u9fff]{2,4}$", name))

    def _is_institutional(self, name: str) -> bool:
        """機関投資家キーワードに該当するか。"""
        upper = name.upper()
        return any(kw in name or kw in upper for kw in _INSTITUTIONAL_KEYWORDS)
