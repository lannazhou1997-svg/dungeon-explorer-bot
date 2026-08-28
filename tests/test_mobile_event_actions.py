import pytest

import bot as dungeon_one
from game.models import Player as DungeonOnePlayer
from school_dungeon import runtime as dungeon_two
from school_dungeon.game.models import Player as DungeonTwoPlayer


EVENTS = (
    ("merchant", "查看商品"),
    ("fairy", "帮助精灵"),
    ("trapped_beast", "解救妖兽"),
)


@pytest.mark.parametrize("event, expected_label", EVENTS)
def test_dungeon_one_mobile_event_actions_use_separate_rows(
    event: str,
    expected_label: str,
) -> None:
    player = DungeonOnePlayer(1, "手机测试", pending_event=event)

    primary_row = dungeon_one.DungeonActions(player)
    decline_row = dungeon_one.DungeonDeclineActions(player)

    assert [button.label for button in primary_row.children] == [expected_label]
    assert [button.label for button in decline_row.children] == ["婉拒／离开"]
    assert primary_row.children[0].custom_id != decline_row.children[0].custom_id


@pytest.mark.parametrize(
    "event, expected_label",
    (
        ("merchant", "查看商品"),
        ("fairy", "帮助新生"),
        ("trapped_beast", "解救吉祥物"),
    ),
)
def test_dungeon_two_mobile_event_actions_use_separate_rows(
    event: str,
    expected_label: str,
) -> None:
    player = DungeonTwoPlayer(1, "手机测试", pending_event=event)

    primary_row = dungeon_two.DungeonActions(player)
    decline_row = dungeon_two.DungeonDeclineActions(player)

    assert [button.label for button in primary_row.children] == [expected_label]
    assert [button.label for button in decline_row.children] == ["婉拒／离开"]
    assert primary_row.children[0].custom_id != decline_row.children[0].custom_id
