"""スクリーニングプリセットのユーザー分離テスト。

他人の preset id を指定したとき、**更新されないだけでなく内容も見えない**
ことを守る。以前は update() が user_id で守られていた一方、直後の
get(pk=...) に user_id が無く、他人の name / filters がレスポンスとして
返っていた。
"""

from __future__ import annotations

from typing import Any

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.stocks.models import ScreeningPreset

User = get_user_model()


@pytest.fixture
def owner() -> Any:
    return User.objects.create_user(username="owner", email="owner@example.com", password="x")


@pytest.fixture
def intruder() -> Any:
    return User.objects.create_user(username="intruder", email="intruder@example.com", password="x")


@pytest.fixture
def owner_preset(owner: Any) -> ScreeningPreset:
    return ScreeningPreset.objects.create(
        user=owner,
        name="オーナーの秘密プリセット",
        priority=1,
        filters={"per_max": 15},
    )


@pytest.mark.django_db
class TestScreeningPresetIsolation:
    def test_other_user_cannot_read_via_put(self, intruder: Any, owner_preset: ScreeningPreset) -> None:
        """他人の preset を PUT しても内容が漏れない。

        これが元の不具合。200 で相手の name / filters が返っていた。
        """
        client = APIClient()
        client.force_authenticate(user=intruder)

        res = client.put(
            f"/api/stocks/screening/presets/{owner_preset.id}/",
            {"name": "乗っ取り", "priority": 9, "filters": {}},
            format="json",
        )

        assert res.status_code == 404
        # 相手の情報がレスポンスに含まれないこと
        assert "オーナーの秘密プリセット" not in res.content.decode()

    def test_other_user_cannot_modify(self, intruder: Any, owner_preset: ScreeningPreset) -> None:
        """PUT しても中身が書き換わらない。"""
        client = APIClient()
        client.force_authenticate(user=intruder)
        client.put(
            f"/api/stocks/screening/presets/{owner_preset.id}/",
            {"name": "乗っ取り", "priority": 9, "filters": {}},
            format="json",
        )

        owner_preset.refresh_from_db()
        assert owner_preset.name == "オーナーの秘密プリセット"
        assert owner_preset.filters == {"per_max": 15}

    def test_owner_can_update(self, owner: Any, owner_preset: ScreeningPreset) -> None:
        """本人の更新は通る（修正で塞ぎすぎていないこと）。"""
        client = APIClient()
        client.force_authenticate(user=owner)

        res = client.put(
            f"/api/stocks/screening/presets/{owner_preset.id}/",
            {"name": "更新後", "priority": 2, "filters": {"pbr_max": 1.0}},
            format="json",
        )

        assert res.status_code == 200
        owner_preset.refresh_from_db()
        assert owner_preset.name == "更新後"

    def test_list_shows_only_own(self, owner: Any, intruder: Any, owner_preset: ScreeningPreset) -> None:
        """一覧に他人のものが混ざらない。"""
        ScreeningPreset.objects.create(user=intruder, name="侵入者の", priority=1, filters={})

        client = APIClient()
        client.force_authenticate(user=intruder)
        res = client.get("/api/stocks/screening/presets/")

        assert res.status_code == 200
        body = res.content.decode()
        assert "オーナーの秘密プリセット" not in body
        assert "侵入者の" in body
